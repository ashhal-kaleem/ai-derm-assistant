# DermAssist AI - Phase 1 v3: Teacher ensemble on HAM10000
# v3 fixes: shades-of-gray color constancy, EMA weights, CutMix, EVA02-S@336 instead of Swin-T@224,
# model selection on EMA (less noisy), same lesion-disjoint split as v2 (SEED 2026) for a fair comparison.
# Lesion-disjoint split: train / val (model selection) / cal (temperature + thresholds) / test (untouched)
# Teachers: ConvNeXt-V2-T @384, EfficientNetV2-S @384, Swin-T @224, all with metadata fusion.
import os, glob, json, time, math, random, subprocess, sys
import numpy as np, pandas as pd
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

T0 = time.time()
SMOKE = False
BUDGET_S = 10.5 * 3600
try:
    import timm
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "timm"], check=True); import timm
import torch, torch.nn as nn, torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import balanced_accuracy_score, f1_score, recall_score, confusion_matrix, roc_auc_score
from scipy.optimize import minimize_scalar

OUT = "/kaggle/working"
SEED = 2026
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
dev = torch.device("cuda")
NGPU = torch.cuda.device_count()
print("GPU:", torch.cuda.get_device_name(0), "x", NGPU, "| timm", timm.__version__, flush=True)
C = ["akiec", "bcc", "bkl", "df", "mel", "nv", "vasc"]

# ---------------- data ----------------
csv = glob.glob("/kaggle/input/**/HAM10000_metadata.csv", recursive=True)[0]
df = pd.read_csv(csv)
paths = {}
for p in glob.glob("/kaggle/input/**/*.jpg", recursive=True):
    paths.setdefault(os.path.splitext(os.path.basename(p))[0], p)
df["path"] = df.image_id.map(paths)
df = df.dropna(subset=["path"]).reset_index(drop=True)
df["y"] = df.dx.map({c: i for i, c in enumerate(C)})
print("images", len(df), "lesions", df.lesion_id.nunique(), flush=True)

# lesion-disjoint split
sg = StratifiedGroupKFold(5, shuffle=True, random_state=SEED)
rest_i, test_i = next(sg.split(df, df.y, df.lesion_id))
df["split"] = "train"; df.loc[test_i, "split"] = "test"
rest = df.iloc[rest_i]
sg8 = StratifiedGroupKFold(8, shuffle=True, random_state=SEED)
folds = list(sg8.split(rest, rest.y, rest.lesion_id))
df.loc[rest.index[folds[0][1]], "split"] = "val"
df.loc[rest.index[folds[1][1]], "split"] = "cal"
for a in ["train", "val", "cal", "test"]:
    for b in ["train", "val", "cal", "test"]:
        if a < b:
            assert not set(df[df.split == a].lesion_id) & set(df[df.split == b].lesion_id), (a, b)
print(df.groupby(["split", "dx"]).size().unstack(fill_value=0), flush=True)
df[["image_id", "lesion_id", "dx", "split"]].to_csv(f"{OUT}/split.csv", index=False)
if SMOKE:
    df = df.groupby("split", group_keys=False).apply(lambda g: g.sample(min(len(g), 300), random_state=SEED)).reset_index(drop=True)
    print("SMOKE subset", df.split.value_counts().to_dict(), flush=True)

# metadata features
LOCS = sorted(df.localization.fillna("unknown").unique())
def meta_vec(r):
    age = r.age if not pd.isna(r.age) else -1
    v = [0.0 if age < 0 else age / 90.0, 1.0 if age < 0 else 0.0]
    v += [float(r.sex == s) for s in ["male", "female"]]
    v += [float((r.localization if isinstance(r.localization, str) else "unknown") == l) for l in LOCS]
    return v
M = np.array([meta_vec(r) for r in df.itertuples()], np.float32)
MDIM = M.shape[1]
json.dump({"localizations": LOCS, "meta_dim": MDIM, "age_scale": 90.0, "sex": ["male", "female"]}, open(f"{OUT}/meta_schema.json", "w"))

# preload images at 448x448 (uint8) - HAM images are 600x450
PRE = 448
def shades_of_gray(a, p=6):
    a = a.astype(np.float32)
    ill = np.power(np.mean(np.power(a, p), axis=(0, 1)), 1.0 / p)
    ill = ill / (np.sqrt((ill ** 2).sum()) + 1e-6)
    return np.clip(a / (ill * np.sqrt(3.0) + 1e-6), 0, 255).astype(np.uint8)
def load(p):
    return shades_of_gray(np.asarray(Image.open(p).convert("RGB").resize((PRE, PRE), Image.BICUBIC), np.uint8))
t = time.time()
with ThreadPoolExecutor(8) as ex:
    IMGS = np.stack(list(ex.map(load, df.path)))
print("preloaded", IMGS.shape, f"{time.time()-t:.0f}s", flush=True)
Y = df.y.values

MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1).to(dev)
STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1).to(dev)

class DS(Dataset):
    def __init__(s, idx, size, train):
        s.idx, s.size, s.train = idx, size, train
    def __len__(s): return len(s.idx)
    def __getitem__(s, i):
        j = s.idx[i]
        im = Image.fromarray(IMGS[j])
        if s.train:
            sc = random.uniform(0.6, 1.0); ar = math.exp(random.uniform(math.log(3/4), math.log(4/3)))
            w = int(PRE * math.sqrt(sc * ar)); h = int(PRE * math.sqrt(sc / ar)); w, h = min(w, PRE), min(h, PRE)
            x0, y0 = random.randint(0, PRE - w), random.randint(0, PRE - h)
            im = im.crop((x0, y0, x0 + w, y0 + h)).rotate(random.uniform(-180, 180), resample=Image.BILINEAR)
            im = im.resize((s.size, s.size), Image.BILINEAR)
            if random.random() < .5: im = im.transpose(Image.FLIP_LEFT_RIGHT)
            if random.random() < .5: im = im.transpose(Image.FLIP_TOP_BOTTOM)
            a = np.asarray(im, np.float32)
            a = a * random.uniform(0.85, 1.15) + random.uniform(-20, 20)            # brightness/contrast
            a = a * np.random.uniform(0.92, 1.08, (1, 1, 3))                       # color cast
            a = np.clip(a, 0, 255).astype(np.uint8)
        else:
            a = np.asarray(im.resize((s.size, s.size), Image.BILINEAR), np.uint8)
        return torch.from_numpy(a).permute(2, 0, 1), torch.from_numpy(M[j]), int(Y[j])

def norm(x): return (x.to(dev, non_blocking=True).float() / 255.0 - MEAN) / STD

class Net(nn.Module):
    def __init__(s, name):
        super().__init__()
        s.b = timm.create_model(name, pretrained=True, num_classes=0)
        s.m = nn.Sequential(nn.Linear(MDIM, 64), nn.GELU(), nn.Dropout(0.1), nn.Linear(64, 64), nn.GELU())
        s.h = nn.Sequential(nn.Dropout(0.3), nn.Linear(s.b.num_features + 64, 7))
    def forward(s, x, m):
        return s.h(torch.cat([s.b(x), s.m(m)], 1))

# cost-sensitive class weights: sqrt inverse frequency x clinical cost
tr_idx = np.where(df.split == "train")[0]
cnt = np.bincount(Y[tr_idx], minlength=7)
cw = np.sqrt(cnt.sum() / (7 * cnt))
cost = np.array([1.2, 1.5, 1.0, 1.0, 2.0, 1.0, 1.0])
cw = cw * cost; cw = cw / cw.mean()
print("class weights", dict(zip(C, cw.round(3))), flush=True)
CW = torch.tensor(cw, dtype=torch.float32, device=dev)

def predict(model, idx, size, bs):
    dl = DataLoader(DS(idx, size, False), batch_size=bs, shuffle=False, num_workers=4, pin_memory=True)
    model.eval(); out = []
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
        for x, m, _ in dl:
            x = norm(x); m = m.to(dev)
            z = (model(x, m) + model(x.flip(3), m) + model(x.flip(2), m) + model(x.transpose(2, 3), m)) / 4
            out.append(z.float().cpu().numpy())
    return np.concatenate(out)

def metrics(z, y, T=1.0):
    p = softmax(z / T); pred = p.argmax(1)
    rec = recall_score(y, pred, average=None, labels=range(7), zero_division=0)
    conf = p.max(1); acc = pred == y; ece = 0.0
    for lo in np.linspace(0, 1, 16)[:-1]:
        k = (conf > lo) & (conf <= lo + 1 / 15)
        if k.any(): ece += k.mean() * abs(acc[k].mean() - conf[k].mean())
    mal = np.isin(y, [0, 1, 4]).astype(int); pmal = p[:, [0, 1, 4]].sum(1)
    return {"acc": float(acc.mean()), "bal_acc": float(balanced_accuracy_score(y, pred)),
            "macro_f1": float(f1_score(y, pred, average="macro")), "ece": float(ece),
            "mel_recall": float(rec[4]), "bcc_recall": float(rec[1]),
            "malignant_auc": float(roc_auc_score(mal, pmal)),
            "recall": {c: round(float(r), 4) for c, r in zip(C, rec)}}

def softmax(z):
    z = z - z.max(1, keepdims=True); e = np.exp(z); return e / e.sum(1, keepdims=True)

EPOCHS = 1 if SMOKE else 25
TEACHERS = [
    ("convnextv2_tiny", ["convnextv2_tiny.fcmae_ft_in22k_in1k_384"], 384, 32, EPOCHS),
    ("effnetv2_s", ["tf_efficientnetv2_s.in21k_ft_in1k"], 384, 32, EPOCHS),
    ("eva02_small", ["eva02_small_patch14_336.mim_in22k_ft_in1k"], 336, 32, EPOCHS),
]
from timm.utils import ModelEmaV3
SPL = {s: np.where(df.split == s)[0] for s in ["val", "cal", "test"]}
results = {}

for key, names, size, bs, EP in TEACHERS:
    remaining = BUDGET_S - (time.time() - T0)
    if remaining < 1800:
        print("SKIP", key, "budget", flush=True); continue
    model = None
    for n in names:
        try: model = Net(n).to(dev); used = n; break
        except Exception as e: print("model fail", n, e, flush=True)
    if model is None: continue
    print(f"\n===== {key} ({used}) size {size} =====", flush=True)
    net = nn.DataParallel(model) if NGPU > 1 else model
    dl = DataLoader(DS(tr_idx, size, True), batch_size=bs, shuffle=True, num_workers=4, pin_memory=True, drop_last=True, persistent_workers=True)
    opt = torch.optim.AdamW([{"params": model.b.parameters(), "lr": 1e-4},
                             {"params": list(model.m.parameters()) + list(model.h.parameters()), "lr": 1e-3}], weight_decay=0.05)
    steps = EP * len(dl); warm = len(dl)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1, (s + 1) / warm) * 0.5 * (1 + math.cos(math.pi * min(1, s / steps))))
    scaler = torch.cuda.amp.GradScaler()
    ema = ModelEmaV3(model, decay=0.998)
    best, best_ep, t_model = -1, 0, time.time()
    for ep in range(1, EP + 1):
        net.train(); tl = 0; te = time.time()
        for x, m, y in dl:
            x = norm(x); m = m.to(dev); y = y.to(dev)
            use_cm = random.random() < 0.5
            if use_cm:   # CutMix: paste a box from a shuffled batch, mix the loss by area
                perm = torch.randperm(x.size(0), device=dev); lam = np.random.beta(1.0, 1.0)
                H = x.size(2); r = math.sqrt(1 - lam); bh = int(H * r); cy, cx = random.randint(0, H - 1), random.randint(0, H - 1)
                y0, y1, x0, x1 = max(cy - bh // 2, 0), min(cy + bh // 2, H), max(cx - bh // 2, 0), min(cx + bh // 2, H)
                x[:, :, y0:y1, x0:x1] = x[perm, :, y0:y1, x0:x1]
                lam = 1 - (y1 - y0) * (x1 - x0) / (H * H)
            with torch.autocast("cuda", dtype=torch.float16):
                out = net(x, m)
                loss = F.cross_entropy(out, y, weight=CW, label_smoothing=0.05)
                if use_cm:
                    loss = lam * loss + (1 - lam) * F.cross_entropy(out, y[perm], weight=CW, label_smoothing=0.05)
            opt.zero_grad(set_to_none=True); scaler.scale(loss).backward()
            scaler.unscale_(opt); nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            scaler.step(opt); scaler.update(); sched.step(); ema.update(model); tl += loss.item()
        zv = predict(ema.module, SPL["val"], size, bs * 2); mv = metrics(zv, Y[SPL["val"]])
        score = mv["bal_acc"] + mv["macro_f1"] + 0.5 * mv["mel_recall"]
        if score > best:
            best, best_ep = score, ep; torch.save(ema.module.state_dict(), f"{OUT}/{key}.pt")
        print(f"{key} ep{ep:02d} loss {tl/len(dl):.4f} | val bal_acc {mv['bal_acc']:.4f} f1 {mv['macro_f1']:.4f} mel {mv['mel_recall']:.4f} | {time.time()-te:.0f}s", flush=True)
        if BUDGET_S - (time.time() - T0) < 1200:
            print("budget stop", flush=True); break
    model.load_state_dict(torch.load(f"{OUT}/{key}.pt"))
    Z = {s: predict(net, SPL[s], size, bs * 2) for s in SPL}
    np.savez(f"{OUT}/{key}_logits.npz", **Z, **{f"y_{s}": Y[SPL[s]] for s in SPL})
    results[key] = {"timm_name": used, "size": size, "best_epoch": best_ep, "train_min": round((time.time() - t_model) / 60, 1),
                    "test": metrics(Z["test"], Y[SPL["test"]])}
    print(key, "TEST", json.dumps(results[key]["test"]), flush=True)
    del net, model, opt, ema; torch.cuda.empty_cache()
    json.dump(results, open(f"{OUT}/results.json", "w"), indent=2)

# ---------------- ensemble + calibration ----------------
keys = [k for k in results]
ZZ = {s: np.mean([softmax(np.load(f"{OUT}/{k}_logits.npz")[s]) for k in keys], 0) for s in SPL}
LZ = {s: np.log(np.clip(ZZ[s], 1e-8, 1)) for s in SPL}   # log of averaged probs as ensemble logits
yc, yt = Y[SPL["cal"]], Y[SPL["test"]]
def nll(T):
    p = softmax(LZ["cal"] / T); return -np.log(np.clip(p[np.arange(len(yc)), yc], 1e-12, 1)).mean()
T = float(minimize_scalar(nll, bounds=(0.3, 5), method="bounded").x)
ens = metrics(LZ["test"], yt, 1.0); ens_cal = metrics(LZ["test"], yt, T)
# melanoma-priority operating point chosen on CAL to reach >=0.85 mel recall, then applied to TEST
pc = softmax(LZ["cal"] / T); pt = softmax(LZ["test"] / T)
thr = 0.5
for t_ in np.linspace(0.5, 0.02, 97):
    if ((pc[:, 4] >= t_)[yc == 4]).mean() >= 0.85: thr = float(t_); break
pred = pt.argmax(1); pred[pt[:, 4] >= thr] = 4
mel_op = {"mel_threshold": thr, "mel_recall": float((pred[yt == 4] == 4).mean()),
          "mel_precision": float((yt[pred == 4] == 4).mean()), "bal_acc": float(balanced_accuracy_score(yt, pred)),
          "macro_f1": float(f1_score(yt, pred, average="macro"))}
results["ensemble"] = {"members": keys, "temperature": T, "test_raw": ens, "test_calibrated": ens_cal, "mel_priority_test": mel_op,
                       "confusion_test": confusion_matrix(yt, softmax(LZ["test"] / T).argmax(1), labels=range(7)).tolist(),
                       "n_test": int(len(yt)), "n_test_lesions": int(df.iloc[SPL["test"]].lesion_id.nunique())}
json.dump(results, open(f"{OUT}/results.json", "w"), indent=2)
print("\nENSEMBLE", json.dumps(results["ensemble"], indent=1), flush=True)
print(f"TOTAL {((time.time()-T0)/3600):.2f} h", flush=True)
