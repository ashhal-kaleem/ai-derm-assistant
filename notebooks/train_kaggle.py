"""HAM10000 Production Model Training Pipeline for Kaggle GPU.

This script executes the complete deep learning training pipeline:
1. Auto-discovers HAM10000 dataset in Kaggle input directories.
2. Partitions dataset with ZERO patient leakage via StratifiedGroupKFold on lesion_id.
3. Implements class-weighted Cross-Entropy loss to solve the 67% melanocytic nevus imbalance.
4. Trains an EfficientNet-B4 backbone with mixed-precision (FP16) acceleration.
5. Optimizes temperature scaling (T*) for calibrated clinical confidence.
6. Exports a dual-output ONNX model (logits + feature maps) compatible with DermAssist AI.
"""

import os
import sys
import glob
import json
import time
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from PIL import Image
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import classification_report, f1_score, balanced_accuracy_score
from scipy.optimize import minimize_scalar

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms

# -------------------------------------------------------------------------
# 1. Class Taxonomy & Global Constants
# -------------------------------------------------------------------------
CLASS_NAMES = ["akiec", "bcc", "bkl", "df", "mel", "nv", "vasc"]
CLASS_TO_IDX = {name: idx for idx, name in enumerate(CLASS_NAMES)}
IDX_TO_CLASS = {idx: name for idx, name in enumerate(CLASS_NAMES)}

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
IMAGE_SIZE = (380, 380)  # Native resolution for EfficientNet-B4

# -------------------------------------------------------------------------
# 2. Path Auto-Detection (Kaggle vs Local Fallback)
# -------------------------------------------------------------------------
def locate_dataset_paths() -> Tuple[str, List[str]]:
    """Locate the metadata CSV and image directories across Kaggle or local environments."""
    kaggle_base = "/kaggle/input/skin-cancer-mnist-ham10000"
    local_base = "data/ham10000"

    if os.path.exists(kaggle_base):
        csv_path = os.path.join(kaggle_base, "HAM10000_metadata.csv")
        image_dirs = [
            os.path.join(kaggle_base, "HAM10000_images_part_1"),
            os.path.join(kaggle_base, "HAM10000_images_part_2"),
        ]
        return csv_path, image_dirs
    elif os.path.exists(local_base):
        csv_path = os.path.join(local_base, "HAM10000_metadata.csv")
        image_dirs = [
            os.path.join(local_base, "HAM10000_images_part_1"),
            os.path.join(local_base, "HAM10000_images_part_2"),
        ]
        return csv_path, image_dirs
    else:
        # Fallback search in working tree
        csv_candidates = glob.glob("**/HAM10000_metadata.csv", recursive=True)
        if csv_candidates:
            csv_path = csv_candidates[0]
            base_dir = os.path.dirname(csv_path)
            image_dirs = [
                os.path.join(base_dir, "HAM10000_images_part_1"),
                os.path.join(base_dir, "HAM10000_images_part_2"),
            ]
            return csv_path, image_dirs
        raise FileNotFoundError(
            "HAM10000 dataset not found. When running on Kaggle, ensure 'skin-cancer-mnist-ham10000' "
            "is added to the Notebook inputs at /kaggle/input/skin-cancer-mnist-ham10000/."
        )

# -------------------------------------------------------------------------
# 3. Patient-Aware Zero-Leakage Dataset Partitioning
# -------------------------------------------------------------------------
def prepare_metadata(csv_path: str, image_dirs: List[str]) -> pd.DataFrame:
    """Read metadata, index image file paths, map diagnostic labels, and verify data integrity."""
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} metadata records from {csv_path}")

    # Build image ID to absolute path dictionary
    image_path_map: Dict[str, str] = {}
    for img_dir in image_dirs:
        for ext in ("*.jpg", "*.jpeg", "*.png"):
            for file_path in glob.glob(os.path.join(img_dir, ext)):
                image_id = os.path.splitext(os.path.basename(file_path))[0]
                image_path_map[image_id] = file_path

    print(f"Discovered {len(image_path_map)} image files across {len(image_dirs)} directories")
    df["file_path"] = df["image_id"].map(image_path_map)
    df = df.dropna(subset=["file_path"]).copy()

    # Map string diagnoses to integer targets
    df["label"] = df["dx"].map(CLASS_TO_IDX)
    df = df.dropna(subset=["label"]).copy()
    df["label"] = df["label"].astype(int)

    return df

def split_dataset_zero_leakage(df: pd.DataFrame, n_splits: int = 5, seed: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Perform StratifiedGroupKFold splitting on lesion_id to guarantee zero patient leakage."""
    sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    
    # Use first split for train and validation
    for train_idx, val_idx in sgkf.split(df, df["label"], groups=df["lesion_id"]):
        train_df = df.iloc[train_idx].copy().reset_index(drop=True)
        val_df = df.iloc[val_idx].copy().reset_index(drop=True)
        break

    # Strictly assert zero patient leakage
    train_lesions = set(train_df["lesion_id"].unique())
    val_lesions = set(val_df["lesion_id"].unique())
    overlap = train_lesions.intersection(val_lesions)
    if len(overlap) > 0:
        raise AssertionError(f"PATIENT DATA LEAKAGE DETECTED: {len(overlap)} lesions overlap between splits!")

    print(f"Zero-Leakage Split Verified: Train={len(train_df)} images ({len(train_lesions)} lesions), "
          f"Val={len(val_df)} images ({len(val_lesions)} lesions). Overlap = 0.")
    return train_df, val_df

# -------------------------------------------------------------------------
# 4. PyTorch Dataset & Clinical Augmentations
# -------------------------------------------------------------------------
class HAM10000Dataset(Dataset):
    """PyTorch Dataset for dermatoscopic images with PIL loading and transformations."""

    def __init__(self, df: pd.DataFrame, transform=None):
        self.df = df
        self.transform = transform
        self.file_paths = df["file_path"].values
        self.labels = df["label"].values

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        path = self.file_paths[idx]
        image = Image.open(path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        label = int(self.labels[idx])
        return image, label

def get_transforms() -> Tuple[transforms.Compose, transforms.Compose]:
    """Return clinical image augmentation pipelines preserving dermoscopic features."""
    train_transform = transforms.Compose([
        transforms.Resize(IMAGE_SIZE),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.5),
        transforms.RandomRotation(degrees=25),
        transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
    ])

    val_transform = transforms.Compose([
        transforms.Resize(IMAGE_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
    ])

    return train_transform, val_transform

# -------------------------------------------------------------------------
# 5. Dual-Output EfficientNet-B4 Neural Architecture
# -------------------------------------------------------------------------
class DualOutputEfficientNetB4(nn.Module):
    """EfficientNet-B4 with dual outputs: classification logits and pre-pooling feature maps.
    
    This matches the exact contract required by DermAssist AI for real-time Grad-CAM explainability.
    """

    def __init__(self, num_classes: int = 7, pretrained: bool = True):
        super().__init__()
        weights = models.EfficientNet_B4_Weights.DEFAULT if pretrained else None
        self.backbone = models.efficientnet_b4(weights=weights)

        # Replace classification head
        in_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(p=0.4, inplace=True),
            nn.Linear(in_features=in_features, out_features=num_classes)
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # Extract convolutional feature maps: shape (B, 1792, H, W)
        features = self.backbone.features(x)
        # Global Average Pooling and classification
        pooled = self.backbone.avgpool(features)
        flattened = torch.flatten(pooled, 1)
        logits = self.backbone.classifier(flattened)
        return logits, features

# -------------------------------------------------------------------------
# 6. Temperature Scaling & Calibration Optimization
# -------------------------------------------------------------------------
def softmax_np(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=-1, keepdims=True)
    exp_vals = np.exp(shifted)
    return exp_vals / np.sum(exp_vals, axis=-1, keepdims=True)

def compute_ece_metric(probabilities: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
    """Compute Expected Calibration Error (ECE) across confidence bins."""
    confidences = np.max(probabilities, axis=1)
    predictions = np.argmax(probabilities, axis=1)
    accuracies = predictions == labels

    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n_samples = len(labels)

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
        bin_size = np.sum(in_bin)

        if bin_size > 0:
            bin_acc = np.mean(accuracies[in_bin])
            bin_conf = np.mean(confidences[in_bin])
            ece += (bin_size / n_samples) * np.abs(bin_acc - bin_conf)

    return float(ece)

def optimize_temperature_scaling(logits: np.ndarray, labels: np.ndarray) -> Tuple[float, float, float]:
    """Find optimal temperature scalar T* that minimizes validation Negative Log-Likelihood."""
    def nll_objective(T: float) -> float:
        scaled = logits / max(0.05, float(T))
        probs = softmax_np(scaled)
        eps = 1e-12
        probs = np.clip(probs, eps, 1.0 - eps)
        n = logits.shape[0]
        return float(-np.sum(np.log(probs[np.arange(n), labels])) / n)

    raw_probs = softmax_np(logits)
    raw_ece = compute_ece_metric(raw_probs, labels)

    res = minimize_scalar(nll_objective, bounds=(0.1, 10.0), method="bounded")
    optimal_t = float(res.x)

    calibrated_probs = softmax_np(logits / optimal_t)
    calibrated_ece = compute_ece_metric(calibrated_probs, labels)

    print(f"Temperature Optimization: Raw ECE={raw_ece*100:.2f}% -> Calibrated ECE={calibrated_ece*100:.2f}% (T* = {optimal_t:.4f})")
    return optimal_t, raw_ece, calibrated_ece

# -------------------------------------------------------------------------
# 7. Dual-Output ONNX Export
# -------------------------------------------------------------------------
def export_onnx_model(model: nn.Module, output_path: str = "efficientnet_b4_ham10000.onnx") -> None:
    """Export the trained PyTorch model to an optimized dual-output ONNX binary."""
    model.eval()
    dummy_input = torch.randn(1, 3, IMAGE_SIZE[0], IMAGE_SIZE[1], dtype=torch.float32)

    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["logits", "features"],
        dynamic_axes={
            "input": {0: "batch_size"},
            "logits": {0: "batch_size"},
            "features": {0: "batch_size"}
        }
    )
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"ONNX Model exported successfully to {output_path} ({file_size_mb:.2f} MB)")

# -------------------------------------------------------------------------
# 8. Main Training Execution Loop
# -------------------------------------------------------------------------
def train_pipeline(epochs: int = 10, batch_size: int = 32, lr: float = 3e-4) -> None:
    """Execute end-to-end training, validation, calibration, and ONNX deployment."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Target Execution Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    csv_path, image_dirs = locate_dataset_paths()
    df = prepare_metadata(csv_path, image_dirs)
    train_df, val_df = split_dataset_zero_leakage(df)

    # Compute smoothed inverse frequency class weights to combat 67% nv dominance
    class_counts = train_df["label"].value_counts().sort_index().values
    total_samples = len(train_df)
    class_weights = total_samples / (len(CLASS_NAMES) * class_counts.astype(np.float32))
    # Apply square root damping to prevent extreme gradients on rare classes (df, vasc)
    damped_weights = np.sqrt(class_weights)
    damped_weights = damped_weights / damped_weights.sum() * len(CLASS_NAMES)
    weight_tensor = torch.tensor(damped_weights, dtype=torch.float32).to(device)

    print("Computed Class Weights (Balanced Cross-Entropy):")
    for cls_name, weight in zip(CLASS_NAMES, damped_weights):
        print(f"  {cls_name:8s}: weight = {weight:.3f}")

    train_transform, val_transform = get_transforms()
    train_dataset = HAM10000Dataset(train_df, transform=train_transform)
    val_dataset = HAM10000Dataset(val_df, transform=val_transform)

    num_workers = min(4, os.cpu_count() or 1)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=True)

    model = DualOutputEfficientNetB4(num_classes=len(CLASS_NAMES), pretrained=True).to(device)
    criterion = nn.CrossEntropyLoss(weight=weight_tensor)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
    scaler = torch.cuda.amp.GradScaler(enabled=torch.cuda.is_available())

    best_macro_f1 = 0.0
    best_weights_path = "best_model.pt"

    for epoch in range(1, epochs + 1):
        start_time = time.time()
        model.train()
        running_loss = 0.0
        train_correct = 0
        total_train = 0

        for images, labels in train_loader:
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)

            optimizer.zero_grad(set_to_none=True)
            with torch.cuda.amp.autocast(enabled=torch.cuda.is_available()):
                logits, _ = model(images)
                loss = criterion(logits, labels)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            running_loss += loss.item() * images.size(0)
            preds = torch.argmax(logits, dim=1)
            train_correct += (preds == labels).sum().item()
            total_train += labels.size(0)

        scheduler.step()
        train_loss = running_loss / total_train
        train_acc = train_correct / total_train

        # Validation phase
        model.eval()
        val_loss = 0.0
        all_val_logits: List[np.ndarray] = []
        all_val_labels: List[int] = []

        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device, non_blocking=True)
                labels = labels.to(device, non_blocking=True)

                with torch.cuda.amp.autocast(enabled=torch.cuda.is_available()):
                    logits, _ = model(images)
                    loss = criterion(logits, labels)

                val_loss += loss.item() * images.size(0)
                all_val_logits.append(logits.cpu().numpy())
                all_val_labels.extend(labels.cpu().numpy())

        val_loss = val_loss / len(val_dataset)
        val_logits_np = np.concatenate(all_val_logits, axis=0)
        val_labels_np = np.array(all_val_labels)
        val_preds_np = np.argmax(val_logits_np, axis=1)

        val_acc = np.mean(val_preds_np == val_labels_np)
        val_balanced_acc = balanced_accuracy_score(val_labels_np, val_preds_np)
        val_macro_f1 = f1_score(val_labels_np, val_preds_np, average="macro", zero_division=0)
        elapsed = time.time() - start_time

        print(f"Epoch [{epoch:02d}/{epochs:02d}] ({elapsed:.1f}s) | "
              f"Train Loss: {train_loss:.4f} Acc: {train_acc*100:.1f}% | "
              f"Val Loss: {val_loss:.4f} Acc: {val_acc*100:.1f}% BalAcc: {val_balanced_acc*100:.1f}% Macro-F1: {val_macro_f1:.4f}")

        if val_macro_f1 > best_macro_f1:
            best_macro_f1 = val_macro_f1
            torch.save(model.state_dict(), best_weights_path)
            print(f"  --> Saved new best checkpoint (Macro-F1: {best_macro_f1:.4f})")

    # Load best checkpoint for post-hoc calibration and export
    print(f"\nLoading best checkpoint from {best_weights_path} for final evaluation and calibration...")
    model.load_state_dict(torch.load(best_weights_path, map_location=device))
    model.eval()

    # Collect final validation logits for temperature calibration
    final_val_logits: List[np.ndarray] = []
    final_val_labels: List[int] = []
    with torch.no_grad():
        for images, labels in val_loader:
            images = images.to(device)
            logits, _ = model(images)
            final_val_logits.append(logits.cpu().numpy())
            final_val_labels.extend(labels.numpy())

    val_logits_np = np.concatenate(final_val_logits, axis=0)
    val_labels_np = np.array(final_val_labels)

    # Perform temperature scaling optimization
    optimal_t, raw_ece, calibrated_ece = optimize_temperature_scaling(val_logits_np, val_labels_np)

    # Classification report
    val_preds_np = np.argmax(val_logits_np, axis=1)
    report = classification_report(val_labels_np, val_preds_np, target_names=CLASS_NAMES, zero_division=0)
    print("\nFinal Validation Clinical Classification Report:")
    print(report)

    # Export ONNX model to working directory
    export_onnx_model(model.cpu(), output_path="efficientnet_b4_ham10000.onnx")

    # Save calibration metadata parameters
    calibration_metadata = {
        "model_architecture": "EfficientNet-B4",
        "num_classes": 7,
        "class_names": CLASS_NAMES,
        "optimal_temperature": round(optimal_t, 4),
        "raw_ece": round(raw_ece, 4),
        "calibrated_ece": round(calibrated_ece, 4),
        "val_macro_f1": round(best_macro_f1, 4),
        "input_resolution": [IMAGE_SIZE[0], IMAGE_SIZE[1]],
        "export_format": "ONNX Opset 14 (Dual Output: Logits + Features)"
    }
    with open("calibration_params.json", "w") as f:
        json.dump(calibration_metadata, f, indent=2)
    print("Saved calibration metadata to calibration_params.json")
    print("\n✅ Training and ONNX generation completed successfully.")

if __name__ == "__main__":
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    train_pipeline(epochs=epochs)
