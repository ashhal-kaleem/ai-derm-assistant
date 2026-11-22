import torch, sys, os
from common import *
for key,name,size in MODELS:
    if len(sys.argv)>1 and key not in sys.argv[1:]: continue
    net=load(key,name)
    x=torch.randn(2,3,size,size); m=torch.zeros(2,MDIM)
    torch.onnx.export(net,(x,m),f'onnx/{key}.onnx',input_names=['image','meta'],output_names=['logits'],
        dynamic_axes={'image':{0:'b'},'meta':{0:'b'},'logits':{0:'b'}},opset_version=17,dynamo=False,do_constant_folding=True)
    print(key,'exported',os.path.getsize(f'onnx/{key}.onnx')//1e6,'MB',flush=True)
