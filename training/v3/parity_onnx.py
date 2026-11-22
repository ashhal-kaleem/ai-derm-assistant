import numpy as np, pandas as pd, glob, os, onnxruntime as ort, time
from PIL import Image
from common import *
md=pd.read_csv(os.environ.get('PARITY_DIR','parity')+'/HAM10000_metadata.csv').set_index('image_id')
picks=[l.split() for l in open(os.environ.get('PARITY_DIR','parity')+'/pick.txt')]
paths={os.path.basename(p)[:-4]:p for p in glob.glob(os.environ.get('PARITY_DIR','parity')+'/img/*/*.jpg')}
for key,name,size in MODELS:
    s=ort.InferenceSession(f'onnx/{key}.onnx',providers=['CPUExecutionProvider'])
    Z=np.load(f'{K}/{key}_logits.npz')['test']; d=[];ag=0;ts=[]
    for i,iid,dx in picks:
        r=md.loc[iid]; x=to_tensor(pre448(Image.open(paths[iid])),size); m=meta_vec(r.age,r.sex,r.localization)
        xb=np.ascontiguousarray(np.concatenate(tta4(x),0)); mb=np.repeat(m,4,0)
        t=time.time(); z=s.run(None,{'image':xb,'meta':mb})[0].mean(0); ts.append(time.time()-t)
        ref=Z[int(i)]; d.append(np.abs(z-ref).max()); ag+=int(z.argmax()==ref.argmax())
    print(key,'onnx max|diff| %.4f agree %d/21 | 4-view batch %.0f ms median (2 cores)'%(max(d),ag,1000*np.median(ts)),flush=True)
