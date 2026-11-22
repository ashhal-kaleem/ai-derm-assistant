"""Dynamic INT8 quantization of the EVA02-S member (weights QInt8).

Only EVA02-S is quantized: on the full 1,975-image test split the INT8 EVA02
ensemble scored the same as fp32 (macro F1 0.762 vs 0.758, melanoma recall
85.3% both), while INT8 ConvNeXt/EffNet changed predictions in a 21-image
parity check, so those stay fp32.

Usage: python quantize_onnx.py <fp32 eva02_small.onnx> <out eva02_small_int8.onnx>
Needs: onnx, onnxruntime (numpy>=2 env is fine; the backend runtime is not affected).
"""
import sys

from onnxruntime.quantization import QuantType, quantize_dynamic

if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    quantize_dynamic(src, dst, weight_type=QuantType.QInt8)
    print("wrote", dst)
