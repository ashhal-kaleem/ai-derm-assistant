import json, numpy as np, torch, torch.nn as nn, timm
from PIL import Image
import os
# Folder with the Kaggle training outputs (*.pt weights, meta_schema.json, *_logits.npz)
K=os.environ.get('V3_OUT_DIR','out3')
SCHEMA=json.load(open(f'{K}/meta_schema.json')); LOCS=SCHEMA['localizations']; MDIM=SCHEMA['meta_dim']
MODELS=[('convnextv2_tiny','convnextv2_tiny.fcmae_ft_in22k_in1k_384',384),
        ('effnetv2_s','tf_efficientnetv2_s.in21k_ft_in1k',384),
        ('eva02_small','eva02_small_patch14_336.mim_in22k_ft_in1k',336)]
PRE=448
MEAN=np.array([0.485,0.456,0.406],np.float32); STD=np.array([0.229,0.224,0.225],np.float32)
def shades_of_gray(a,p=6):
    a=a.astype(np.float32); ill=np.power(np.mean(np.power(a,p),axis=(0,1)),1.0/p)
    ill=ill/(np.sqrt((ill**2).sum())+1e-6)
    return np.clip(a/(ill*np.sqrt(3.0)+1e-6),0,255).astype(np.uint8)
def pre448(img): return shades_of_gray(np.asarray(img.convert('RGB').resize((PRE,PRE),Image.BICUBIC),np.uint8))
def to_tensor(a448,size):
    a=np.asarray(Image.fromarray(a448).resize((size,size),Image.BILINEAR),np.float32)/255.0
    return ((a-MEAN)/STD).transpose(2,0,1)[None].astype(np.float32)
def meta_vec(age,sex,loc):
    age=-1 if age is None or (isinstance(age,float) and np.isnan(age)) else float(age)
    v=[0.0 if age<0 else age/90.0, 1.0 if age<0 else 0.0]
    v+=[float(sex==s) for s in ['male','female']]
    loc=loc if isinstance(loc,str) else 'unknown'
    v+=[float(loc==l) for l in LOCS]
    return np.array([v],np.float32)
class Net(nn.Module):
    def __init__(s,name):
        super().__init__()
        s.b=timm.create_model(name,pretrained=False,num_classes=0)
        s.m=nn.Sequential(nn.Linear(MDIM,64),nn.GELU(),nn.Dropout(0.1),nn.Linear(64,64),nn.GELU())
        s.h=nn.Sequential(nn.Dropout(0.3),nn.Linear(s.b.num_features+64,7))
    def forward(s,x,m): return s.h(torch.cat([s.b(x),s.m(m)],1))
def load(key,name):
    n=Net(name); sd=torch.load(f'{K}/{key}.pt',map_location='cpu'); n.load_state_dict(sd); return n.eval()
def tta4(x): return [x,x[...,::-1],x[...,::-1,:],x.transpose(0,1,3,2)]
