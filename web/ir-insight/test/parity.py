import os
import cv2, numpy as np, json, sys, importlib.util
S, ENG = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location('flr', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'facelight_reference.py')); FL = importlib.util.module_from_spec(spec); spec.loader.exec_module(FL)
cases = json.load(open(S + '/parity/cases.json')); rep = {r['id']: r for r in json.load(open(f'{S}/parity/{ENG}/report.json'))['report']}
rows = []; vis = []
for c in cases:
    rgb = cv2.cvtColor(cv2.imread(c['path']), cv2.COLOR_BGR2RGB)
    eyes = [dict(contour=np.array(e['contour'], np.float32), iris=np.array(e['iris'], np.float32), r=e['r']) for e in c['eyes']]
    ref, dbg = FL.process(rgb, 'auto', roi=tuple(c['roi']), eyes=eyes, eye_amt=0.7, return_debug=True)
    js = cv2.cvtColor(cv2.imread(f"{S}/parity/{ENG}/{c['id']}.png"), cv2.COLOR_BGR2RGB)
    d = np.abs(ref.astype(int) - js.astype(int)); h, w = d.shape[:2]; r = c['roi']
    fd = d[int(r[1]*h):int(r[3]*h), int(r[0]*w):int(r[2]*w)]
    jw = rep[c['id']]['fl']['w']
    rows.append((c['id'], d.mean(), np.percentile(d, 99), d.max(), fd.mean(), np.percentile(fd, 99), dbg['weights'], jw))
    print(f"{c['id']:20s} tutto: media {d.mean():.2f} p99 {np.percentile(d,99):.0f} max {d.max():3d} | volto: media {fd.mean():.2f} p99 {np.percentile(fd,99):.0f} | pesi py b{dbg['weights']['back']:.2f}/s{dbg['weights']['spot']:.2f} js b{jw['back']:.2f}/s{jw['spot']:.2f}")
    vis.append(np.hstack([cv2.resize(x, (200, 266)) for x in (rgb, ref, js)]))
print('MEDIA complessiva |diff|', np.mean([r[1] for r in rows]).round(2), ' volto', np.mean([r[4] for r in rows]).round(2), ' p99 volto max', max(r[5] for r in rows))
cv2.imwrite(f'{S}/out/parity_{ENG}.jpg', cv2.cvtColor(np.vstack(vis[:6]), cv2.COLOR_RGB2BGR))
