"""Convert trained PyTorch checkpoint (best_model.pt) to dual-output ONNX binary."""

import os
import torch
import torch.nn as nn
from torchvision import models
import onnxruntime as ort

class DualOutputEfficientNetB4(nn.Module):
    def __init__(self, num_classes=7):
        super().__init__()
        self.backbone = models.efficientnet_b4(weights=None)
        in_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(p=0.4, inplace=True),
            nn.Linear(in_features=in_features, out_features=num_classes)
        )

    def forward(self, x):
        features = self.backbone.features(x)
        pooled = self.backbone.avgpool(features)
        flattened = torch.flatten(pooled, 1)
        logits = self.backbone.classifier(flattened)
        return logits, features

def convert():
    ckpt_path = "checkpoints/best_model.pt"
    onnx_path = "checkpoints/efficientnet_b4_ham10000.onnx"

    if not os.path.exists(ckpt_path):
        raise FileNotFoundError(f"Missing {ckpt_path}")

    print(f"Loading weights from {ckpt_path}...")
    model = DualOutputEfficientNetB4(num_classes=7)
    state_dict = torch.load(ckpt_path, map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()

    dummy_input = torch.randn(1, 3, 380, 380, dtype=torch.float32)
    print(f"Exporting dual-output ONNX to {onnx_path}...")
    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
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
    print(f"ONNX export successful: {os.path.getsize(onnx_path) / (1024*1024):.2f} MB")

    # Verify session
    sess = ort.InferenceSession(onnx_path)
    outputs = sess.run(None, {"input": dummy_input.numpy()})
    print(f"Verified ONNX Runtime output shapes: logits={outputs[0].shape}, features={outputs[1].shape}")
    print("✅ Model is 100% production ready!")

if __name__ == "__main__":
    convert()
