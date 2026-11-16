import json
from pathlib import Path

src = Path('/tmp/kaggle_notebook_rendered.json')
out = Path('/home/ubuntu/ai-derm-assistant/training/skin_lesion_training_production_safe.ipynb')
nb = json.loads(src.read_text())

safe_guard = r'''# 0. Production-safe retraining guard
# This cell runs before the original notebook cells and prevents CPU quota waste.
import os, json, base64, zipfile
import torch
import numpy as np
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import balanced_accuracy_score, f1_score, classification_report, confusion_matrix

assert torch.cuda.is_available(), 'GPU is not enabled; enable a T4/P100 accelerator before running.'
print(f'Preflight GPU: {torch.cuda.get_device_name(0)} | CUDA {torch.version.cuda}')

def _production_guard(_result):
    g = globals()
    # The original val_df is a lesion-grouped holdout. Split it into model-selection,
    # calibration, and untouched final-test partitions.
    if 'train_df' in g and 'val_df' in g and not g.get('_safe_split_done'):
        hold = g['val_df'].copy()
        outer = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=123)
        sel_i, rem_i = next(outer.split(hold, hold['label'], groups=hold['lesion_id']))
        selection = hold.iloc[sel_i].reset_index(drop=True)
        remaining = hold.iloc[rem_i].reset_index(drop=True)
        inner = StratifiedGroupKFold(n_splits=2, shuffle=True, random_state=456)
        cal_i, test_i = next(inner.split(remaining, remaining['label'], groups=remaining['lesion_id']))
        g['val_df'] = selection
        g['calibration_df'] = remaining.iloc[cal_i].reset_index(drop=True)
        g['test_df'] = remaining.iloc[test_i].reset_index(drop=True)
        parts = [g['train_df'], g['val_df'], g['calibration_df'], g['test_df']]
        groups = [set(p['lesion_id']) for p in parts]
        assert all(not (groups[i] & groups[j]) for i in range(4) for j in range(i + 1, 4)), 'CRITICAL: lesion overlap'
        g['_safe_split_done'] = True
        print(f"Lesion-safe split: train={len(parts[0])}, selection={len(parts[1])}, calibration={len(parts[2])}, test={len(parts[3])}")

    # Create independent loaders, but leave the original selection loader active.
    if g.get('_safe_split_done') and 'HAM10000Dataset' in g and 'val_transform' in g and not g.get('_safe_loaders_done'):
        D, C = g['DataLoader'], g['HAM10000Dataset']
        args = dict(batch_size=g['BATCH_SIZE'], shuffle=False, num_workers=4, pin_memory=True)
        g['calibration_loader'] = D(C(g['calibration_df'], g['val_transform']), **args)
        g['test_loader'] = D(C(g['test_df'], g['val_transform']), **args)
        g['_safe_loaders_done'] = True
        print('Independent calibration/test loaders created; selection loader remains active.')

    # Only after cell 8 has selected best_epoch may calibration replace val_loader.
    if g.get('_safe_loaders_done') and g.get('best_epoch', 0) > 0 and not g.get('_calibration_armed'):
        g['val_loader'] = g['calibration_loader']
        g['_calibration_armed'] = True
        print('Calibration armed after selection-split model selection.')

    # After cell 9, evaluate the untouched test split with the calibrated model.
    if g.get('_calibration_armed') and 'optimal_t' in g and not g.get('_test_done'):
        model, device = g['model'], g['device']
        model.eval(); logits, labels = [], []
        with torch.no_grad():
            for images, y in g['test_loader']:
                z, _ = model(images.to(device, non_blocking=True))
                logits.append(z.float().cpu().numpy()); labels.extend(y.numpy())
        z, y = np.concatenate(logits), np.asarray(labels)
        temperature = max(0.05, float(g['optimal_t']))
        scaled = z / temperature
        probs = np.exp(scaled - scaled.max(1, keepdims=True)); probs /= probs.sum(1, keepdims=True)
        pred = probs.argmax(1)
        report = classification_report(y, pred, target_names=g['CLASS_NAMES'], output_dict=True, zero_division=0)
        metrics = {
            'split': 'lesion-disjoint-final-test',
            'temperature': temperature,
            'balanced_accuracy': float(balanced_accuracy_score(y, pred)),
            'macro_f1': float(f1_score(y, pred, average='macro', zero_division=0)),
            'weighted_f1': float(f1_score(y, pred, average='weighted', zero_division=0)),
            'classification_report': report,
            'confusion_matrix': confusion_matrix(y, pred).tolist(),
            'malignant_recall': {c: report.get(c, {}).get('recall') for c in ('bcc', 'mel')},
        }
        with open('/kaggle/working/final_test_metrics.json', 'w') as f: json.dump(metrics, f, indent=2)
        print(f"FINAL TEST | BalAcc={metrics['balanced_accuracy']:.4f} Macro-F1={metrics['macro_f1']:.4f} BCC recall={metrics['malignant_recall']['bcc']:.4f} MEL recall={metrics['malignant_recall']['mel']:.4f}")
        g['_test_done'] = True

    # Export the exact head from the same model as ONNX, with runtime-compatible temperature.
    if 'model' in g and 'optimal_t' in g:
        head = g['model'].backbone.classifier[1]
        weights = head.weight.detach().cpu().numpy().astype('<f4')
        payload = {
            'classes': g['CLASS_NAMES'], 'shape': list(weights.shape),
            'weight_f32_b64': base64.b64encode(weights.tobytes()).decode('ascii'),
            'bias': head.bias.detach().cpu().numpy().astype('float32').tolist(),
            'temperature': round(float(g['optimal_t']), 6),
            'note': 'Matching trained head; temperature fit on independent calibration split.'
        }
        with open('/kaggle/working/head_v2.json', 'w') as f: json.dump(payload, f, indent=2)

    bundle = '/kaggle/working/model_files.zip'
    if os.path.exists(bundle) and os.path.exists('/kaggle/working/head_v2.json'):
        with zipfile.ZipFile(bundle, 'a', compression=zipfile.ZIP_DEFLATED) as z:
            if 'head_v2.json' not in z.namelist(): z.write('/kaggle/working/head_v2.json', 'head_v2.json')

get_ipython().events.register('post_run_cell', _production_guard)
'''

cell = {'cell_type': 'code', 'execution_count': None, 'metadata': {}, 'outputs': [], 'source': safe_guard.splitlines(True)}
# Insert immediately after the title markdown, before the original imports.
nb['cells'].insert(1, cell)

# Harden the original packaging cell as well: it runs after the guard and would
# otherwise overwrite the bundle without ONNX external data or the matching head.
for candidate in nb['cells']:
    if candidate.get('cell_type') != 'code':
        continue
    source = ''.join(candidate.get('source', []))
    if '# 12. Artifact Validation & Packaging' not in source:
        continue
    source = source.replace(
        "assert os.path.exists(weights_path), f'Checkpoint weights missing at {weights_path}'",
        "assert os.path.exists(weights_path), f'Checkpoint weights missing at {weights_path}'\n"
        "onnx_data_path = onnx_path + '.data'\n"
        "head_path = '/kaggle/working/head_v2.json'\n"
        "assert os.path.exists(onnx_data_path), f'ONNX external data missing at {onnx_data_path}'\n"
        "assert os.path.exists(head_path), f'Runtime classifier head missing at {head_path}'",
    )
    source = source.replace(
        "artifacts = [weights_path, onnx_path, calib_path]",
        "artifacts = [weights_path, onnx_path, onnx_data_path, calib_path, head_path]",
    )
    source = source.replace(
        "print(f'✅ Successfully generated {zip_path} ({os.path.getsize(zip_path)/1024**2:.2f} MB)')",
        "with zipfile.ZipFile(zip_path) as z:\n"
        "    required = {os.path.basename(p) for p in artifacts}\n"
        "    assert required.issubset(set(z.namelist())), 'Bundle is missing a required artifact.'\n"
        "print(f'✅ Successfully generated {zip_path} ({os.path.getsize(zip_path)/1024**2:.2f} MB)')",
    )
    candidate['source'] = source.splitlines(True)
    break

out.write_text(json.dumps(nb, indent=1) + '\n')
print(out)
