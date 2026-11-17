import cv2, numpy as np, sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mp_eval import frames, run
import importlib.util, os
spec = importlib.util.spec_from_file_location('flr', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'facelight_reference.py')); FL = importlib.util.module_from_spec(spec); spec.loader.exec_module(FL)
S = sys.argv[1]; MODES = sys.argv[2].split(',') if len(sys.argv) > 2 else ['auto', 'back', 'spot']
STABLE = [33, 133, 362, 263, 1, 4, 61, 291, 152, 10, 234, 454]
UP = {'r': [246, 161, 160, 159, 158, 157, 173], 'l': [466, 388, 387, 386, 385, 384, 398]}

def Yof(rgb): return (0.2126*rgb[..., 0] + 0.7152*rgb[..., 1] + 0.0722*rgb[..., 2]).astype(np.float32)/255

def eye_metrics(rgb, eyes, lm, w, h):
    Y = Yof(rgb); gx = cv2.Sobel(Y, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(Y, cv2.CV_32F, 0, 1, ksize=3); G = np.hypot(gx, gy)
    pi, isc, lid = [], [], []
    for e, side in zip(eyes, 'rl'):
        box_, _ = FL.eye_geometry(e, w, h); lv = FL.eye_levels(FL.sample_patch(Y, box_), e, box_)
        if lv: vp, vi, vs, va = lv; pi.append(vi - vp); isc.append((vs if vs is not None else va) - vi)
        pts = [(lm[i].x*w, lm[i].y*h) for i in UP[side]]
        lid.append(np.mean([G[int(round(y)), int(round(x))] for x, y in pts if 0 <= x < w and 0 <= y < h]))
    return dict(pupil_iris=float(np.mean(pi)) if pi else None, iris_sclera=float(np.mean(isc)) if isc else None, lid_edge=float(np.mean(lid)))

def face_metrics(rgb, roi):
    h, w = rgb.shape[:2]; Y = Yof(rgb)[int(roi[1]*h):int(roi[3]*h), int(roi[0]*w):int(roi[2]*w)]
    hp = Y - cv2.GaussianBlur(Y, (0, 0), 3)
    return dict(face_mean=float(Y.mean()*255), face_clip=float((Y > 0.97).mean()*100), face_dark=float((Y < 0.06).mean()*100), face_detail=float(hp.std()*255))

rows = []
for k, c, f in frames():
    rgb = cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2RGB); h, w = rgb.shape[:2]
    lm0 = run(rgb)
    rec = dict(sess=k, cond=c, frame=f.split('/')[-2], raw=dict(det=lm0 is not None))
    ref = lm0
    for m in MODES:
        if ref is None:   # come dal vivo: primo passaggio senza volto, poi ROI/occhi dal rilevamento sul filtrato
            o1 = FL.process(rgb, m); l1 = run(o1)
            if l1 is not None: ref_m = l1
            else: ref_m = None
        else: ref_m = ref
        if ref_m is not None:
            out, dbg = FL.process(rgb, m, roi=FL.face_roi(ref_m), eyes=FL.eyes_from_landmarks(ref_m, w, h), return_debug=True)
        else:
            out, dbg = FL.process(rgb, m, return_debug=True)
        lm = run(out)
        r = dict(det=lm is not None, weights={a: round(b, 2) for a, b in dbg['weights'].items()})
        if lm is not None and lm0 is not None:
            iod = np.hypot((lm0[33].x-lm0[263].x)*w, (lm0[33].y-lm0[263].y)*h)
            r['agree'] = float(np.mean([np.hypot((lm[i].x-lm0[i].x)*w, (lm[i].y-lm0[i].y)*h) for i in STABLE])/iod*100)
        geo = lm0 if lm0 is not None else lm
        if geo is not None:
            r.update(eye_metrics(out, FL.eyes_from_landmarks(geo, w, h), geo, w, h)); r.update(face_metrics(out, FL.face_roi(geo)))
        rec[m] = r
        cv2.imwrite(f"{S}/out/{k}_{rec['frame']}_{m}.png", cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
    if ref is not None:
        rec['raw'].update(eye_metrics(rgb, FL.eyes_from_landmarks(ref, w, h), ref, w, h)); rec['raw'].update(face_metrics(rgb, FL.face_roi(ref)))
    else:
        g2 = rec[MODES[0]]
    rows.append(rec)
json.dump(rows, open(S+'/out/eval.json', 'w'), indent=1)
# riepilogo per condizione
def agg(cond, m, key):
    v = [r[m].get(key) for r in rows if (cond == 'all' or r['cond'] == cond) and r[m].get(key) is not None]
    return (np.mean(v) if v and not isinstance(v[0], bool) else (sum(v), len(v))) if v else None
for cond in ['back', 'back_sun', 'spot', 'all']:
    print('==', cond)
    for m in ['raw'] + MODES:
        d = agg(cond, m, 'det'); line = f"{m:7s} det {d[0]}/{d[1]}"
        for key in ['agree', 'pupil_iris', 'iris_sclera', 'lid_edge', 'face_mean', 'face_clip', 'face_dark', 'face_detail']:
            v = agg(cond, m, key); line += f" {key} {v:.3f}" if v is not None else f" {key} —"
        print(line)
