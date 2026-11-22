# DermAssist v3 model (training and export)

Final production model: ensemble of ConvNeXt-V2-T@384, EfficientNetV2-S@384 and EVA02-S@336, each using the image plus 19 metadata features (age, sex, anatomical site). Trained on HAM10000 with a lesion-disjoint split (train / val / cal / test, seed 2026).

| File | What it does |
|---|---|
| `train_v3_ensemble.py` | Kaggle training script (GPU). Writes weights, logits, `meta_schema.json`, `results.json`. |
| `common.py` | Shared preprocessing (shades-of-gray, resize, TTA) and model definitions. `V3_OUT_DIR` = training output folder. |
| `export_onnx.py` | Exports each member to ONNX (fp32, opset 17, inputs `image` + `meta`, output `logits`). |
| `quantize_onnx.py` | Dynamic INT8 for EVA02-S only (`eva02_small_int8.onnx`, used by the backend). |
| `parity_onnx.py` | Checks ONNX output against the training logits. `PARITY_DIR` = folder with `pick.txt`, metadata CSV and images. |

Inference settings (in `backend/checkpoints/v3/model_v3.json`): 4-view TTA, temperature 0.5973, melanoma threshold 0.34 (chosen on the cal split).

Test split (1,975 images). With the 0.34 melanoma threshold (what the backend serves): accuracy 83.6%, balanced accuracy 74.9%, macro F1 0.758, melanoma recall 85.3%, malignant AUC 0.950. Without the threshold (plain argmax): accuracy 85.6%, balanced accuracy 75.8%, macro F1 0.772.
