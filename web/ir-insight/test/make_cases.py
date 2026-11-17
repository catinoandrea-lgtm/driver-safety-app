import cv2, numpy as np, sys, json, glob, os
S = sys.argv[1]; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mp_eval import frames, run
import importlib.util, os
spec = importlib.util.spec_from_file_location('flr', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'facelight_reference.py')); FL = importlib.util.module_from_spec(spec); spec.loader.exec_module(FL)
cases = []
for k, c, f in frames():
    fr = f.split('/')[-2]
    if fr not in ('frame_001', 'frame_004'): continue
    rgb = cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2RGB); h, w = rgb.shape[:2]
    lm = run(rgb)
    if lm is None: lm = run(FL.process(rgb, 'auto'))
    if lm is None: continue
    eyes = FL.eyes_from_landmarks(lm, w, h)
    cases.append(dict(id=f'{k}_{fr}', cond=c, path=f, w=w, h=h, roi=list(FL.face_roi(lm)),
                      eyes=[dict(contour=e['contour'].tolist(), iris=e['iris'].tolist(), r=e['r']) for e in eyes]))
json.dump(cases, open(S + '/parity/cases.json', 'w'))
print(len(cases))
