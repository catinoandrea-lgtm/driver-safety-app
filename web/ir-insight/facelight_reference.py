"""FaceLight 1.0 — riferimento Python dei filtri volto di IR InSight 0.10.

Due profili di giorno per il volto del conducente, con passaggio continuo tra i due:
  back   CONTROLLUCE: sole o cielo dietro la testa, volto scuro, velo di flare sulle lenti.
  spot   LUCE PUNTATA: sole/lampada diretti sul volto, luci bruciate su fronte e naso, ombre dure.
  neutral luce normale: interventi leggeri.
Più un potenziamento locale degli occhi (palpebre, iride, pupilla) guidato dai landmark.

Ogni passaggio corrisponde a uno shader del motore GPU (IRFilter.GPU):
  griglia 1/4  : media 4x4 → minimo locale per canale (velo) → media → filtro guidato in log
  CPU          : mediana del velo e della base sul volto, scelta del profilo, LUT degli occhi
  per pixel    : togli velo → base compressa intorno al volto → dettaglio → spalla → occhi → colore

Uso:  out, dbg = process(rgb_uint8, profile='auto', roi=(x0,y0,x1,y1), eyes=eyes_from_landmarks(lm, w, h))
"""
from __future__ import annotations
import numpy as np, cv2

VERSION = '1.0'
# w: forza del velo · cs/ch: pendenza della base sotto/sopra il volto (1 = invariata)
# kd: dettaglio · target: luminosità del volto (0..1) · sat: colore · knee: inizio della spalla sulle luci
PROFILES = {
    'back':    dict(w=0.80, cs=0.80, ch=0.38, kd=1.55, target=0.51, sat=0.90, knee=0.80),
    'spot':    dict(w=0.30, cs=0.50, ch=0.70, kd=1.50, target=0.56, sat=0.95, knee=0.78),
    'neutral': dict(w=0.15, cs=0.85, ch=0.80, kd=1.20, target=0.50, sat=1.00, knee=0.86),
}
IDENTITY = dict(w=0.0, cs=1.0, ch=1.0, kd=1.0, sat=1.0)      # verso cui scala «intensità»
EYE_W, EYE_H = 48, 32                                          # patch per occhio letta dalla CPU
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)
RC = [33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 163, 7]
LC = [263, 466, 388, 387, 386, 385, 384, 398, 362, 382, 381, 380, 374, 373, 390, 249]


def toL(y):  return np.log2(np.clip(y, 0, 1) * 255.0 + 1.0) / 8.0
def fromL(L): return (np.exp2(L * 8.0) - 1.0) / 255.0
def q4(img): h, w = img.shape[:2]; return cv2.resize(img[:h // 4 * 4, :w // 4 * 4], (w // 4, h // 4), interpolation=cv2.INTER_AREA)
def box(img, r): return cv2.blur(img, (2 * r + 1, 2 * r + 1), borderType=cv2.BORDER_REPLICATE)
def erode(img, r): return cv2.erode(img, np.ones((2 * r + 1, 2 * r + 1), np.uint8), borderType=cv2.BORDER_REPLICATE)
def up(img, w, h):
    """Campionamento bilineare della griglia 1/4 ai centri dei pixel, come texture() su GPU."""
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_LINEAR)


def radii(roi, LW):
    fw = max(8.0, (roi[2] - roi[0]) * LW)                      # larghezza del volto in celle 1/4
    return int(np.clip(np.floor(fw * 0.25 + 0.5), 2, 16)), int(np.clip(np.floor(fw * 0.10 + 0.5), 2, 10))      # come Math.round in JS


def roi_cells(roi, LW, LH):
    x0 = int(np.clip(np.floor(roi[0] * LW), 0, LW - 2)); x1 = int(np.clip(np.ceil(roi[2] * LW), x0 + 2, LW))
    y0 = int(np.clip(np.floor(roi[1] * LH), 0, LH - 2)); y1 = int(np.clip(np.ceil(roi[3] * LH), y0 + 2, LH))
    return x0, y0, x1, y1


def dehaze(c, v, cap, w):
    v = np.minimum(v, cap) * w
    t = np.maximum(1.0 - v, 0.40)
    J = np.clip((c - v) / t, 0, 1)
    k = np.clip((c.max(axis=-1, keepdims=True) - 0.92) / 0.07, 0, 1)    # zone bruciate: restano come sono
    return J + k * (c - J)


def auto_weights(st):
    """Scelta continua del profilo dalle statistiche del volto e dello sfondo."""
    back = np.clip((st['bg_p90'] - st['face_med'] - 25.0) / 95.0, 0, 1)
    if st['frame_hot'] > 5 and st['bg_p90'] > 240: back = max(back, 0.6)          # sole in campo
    back = max(back, np.clip((st['veil'] - 35.0) / 50.0, 0, 1))                     # velo sul volto = flare
    contrast = np.log2((st['face_p95'] + 1) / (st['face_p05'] + 1))                # stop tra luci e ombre del volto
    spot = max(np.clip((st['face_p95'] - 185.0) / 50.0, 0, 1) * np.clip((contrast - 1.2) / 1.3, 0, 1),
               np.clip(st['face_hot'] / 4.0, 0, 1))
    spot *= 1 - back
    return dict(back=float(back), spot=float(spot), neutral=float(max(0.0, 1 - back - spot)))


def blend_params(wts, strength=1.0):
    P = {k: sum(wts[n] * PROFILES[n][k] for n in PROFILES) for k in PROFILES['back']}
    for k, v in IDENTITY.items(): P[k] = v + strength * (P[k] - v)
    return P


def eye_curve(vp, vi, vs, va, strength=1.0, gmax=1.8, gpmax=2.4):
    """LUT (256) di un occhio, ancorata alla pelle delle palpebre (va → va).
    La palpebra non si schiarisce mai: un occhio chiuso resta un occhio chiuso.
    Sotto l'ancora si espande (ciglia, iride) e tra iride e pupilla di più; sopra, la sclera si schiarisce un po'."""
    xs = np.linspace(0, 1, 256)
    vi = min(vi, va - 0.004); vp = min(vp, vi - 0.002)
    G = max(1.0, min(gmax, (va - 0.10) / max(va - vi, 1e-3)))
    oi = va - G * (va - vi)
    Gp = max(1.0, min(gpmax, (oi - 0.03) / max(vi - vp, 1e-3)))
    op = max(0.02, oi - Gp * (vi - vp))
    pin, pout = [0.0, vp, vi, va], [0.0, op, oi, va]
    if vs is not None and vs > va + 0.01:
        pin.append(vs); pout.append(min(0.90, va + 1.4 * (vs - va)))
    pin.append(1.0); pout.append(1.0)
    pin = np.maximum.accumulate(np.array(pin, np.float64))
    for k in range(1, len(pin)): pin[k] = max(pin[k], pin[k - 1] + 1e-4)
    pout = np.maximum.accumulate(np.array(pout, np.float64))
    lut = np.interp(xs, pin, pout)
    return (xs + strength * (lut - xs)).astype(np.float32)


def eye_geometry(e, w, h):
    """Riquadro della patch (pixel) e ellisse della maschera, come nel motore JS."""
    c, r = e['contour'], e['r']
    box_ = (c[:, 0].min() - r, c[:, 1].min() - 2 * r, c[:, 0].max() + r, c[:, 1].max() + 2 * r)
    cx, cy = (c[:, 0].min() + c[:, 0].max()) / 2, (c[:, 1].min() + c[:, 1].max()) / 2
    ax = 0.5 * (c[:, 0].max() - c[:, 0].min()) * 1.15 + 0.4 * r
    ay = max(0.5 * (c[:, 1].max() - c[:, 1].min()), r) + 1.0 * r
    return box_, (cx, cy, ax, ay)


def eye_levels(patch, e, box_):
    """Livelli pupilla / iride / sclera / pelle dalla patch EYE_W×EYE_H (valori 0..1)."""
    x0, y0, x1, y1 = box_
    gx = x0 + (np.arange(EYE_W) + 0.5) / EYE_W * (x1 - x0); gy = y0 + (np.arange(EYE_H) + 0.5) / EYE_H * (y1 - y0)
    X, Y = np.meshgrid(gx, gy)
    r = np.hypot(X - e['iris'][0], Y - e['iris'][1]); R = e['r']
    inside = point_in_poly(X, Y, e['contour'])
    ok = patch < 0.985                                                # niente riflesso corneale
    pup = patch[(r < 0.45 * R) & inside & ok]; iri = patch[(r >= 0.5 * R) & (r < 0.95 * R) & inside & ok]
    scl = patch[(r > 1.15 * R) & inside & ok]; lid = patch[~inside & ok]
    if pup.size < 2 or iri.size < 3 or lid.size < 3: return None
    return (float(np.percentile(pup, 20)), float(np.median(iri)),
            float(np.percentile(scl, 70)) if scl.size >= 3 else None, float(np.median(lid)))


def point_in_poly(X, Y, poly):
    ins = np.zeros(X.shape, bool); n = len(poly)
    for i in range(n):
        xa, ya = poly[i]; xb, yb = poly[(i + 1) % n]
        cond = ((ya > Y) != (yb > Y)) & (X < (xb - xa) * (Y - ya) / ((yb - ya) + 1e-12) + xa)
        ins ^= cond
    return ins


def sample_patch(img, box_):
    """Patch EYE_W×EYE_H campionata bilinearmente ai centri, come lo shader della patch."""
    x0, y0, x1, y1 = box_
    gx = x0 + (np.arange(EYE_W) + 0.5) / EYE_W * (x1 - x0) - 0.5; gy = y0 + (np.arange(EYE_H) + 0.5) / EYE_H * (y1 - y0) - 0.5
    X, Y = np.meshgrid(gx.astype(np.float32), gy.astype(np.float32))
    return cv2.remap(img.astype(np.float32), X, Y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def ellipse_mask(w, h, ell):
    cx, cy, ax, ay = ell
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32) + 0.5
    rr = ((xx - cx) / ax) ** 2 + ((yy - cy) / ay) ** 2
    m = np.clip((1.0 - rr) / 0.6, 0, 1)
    return m * m * (3 - 2 * m)


def process(rgb8, profile='auto', roi=(0.25, 0.18, 0.75, 0.70), eyes=None, eye_amt=0.7, strength=1.0, return_debug=False):
    """Un fotogramma, senza memoria (i valori che su GPU arrivano dalla CPU un fotogramma dopo qui sono istantanei)."""
    rgb = rgb8[..., :3].astype(np.float32) / 255.0
    h, w = rgb.shape[:2]; h4, w4 = h // 4 * 4, w // 4 * 4; rgb = rgb[:h4, :w4]; h, w = h4, w4
    q = q4(rgb); LH, LW = q.shape[:2]
    er, gr = radii(roi, LW)
    x0, y0, x1, y1 = roi_cells(roi, LW, LH)

    # velo: minimo locale per canale (mezzo volto), poi media; limitato al velo mediano del volto
    veil_q = np.stack([box(erode(q[..., c], er), er) for c in range(3)], -1)
    face_veil = veil_q[y0:y1, x0:x1].reshape(-1, 3)
    cap = np.median(face_veil, axis=0) * 1.25 + 0.02

    # statistiche di scena (dalla griglia 1/4) e profilo
    Yq = (q @ LUMA) * 255.0; m = np.zeros(Yq.shape, bool); m[y0:y1, x0:x1] = True
    h2 = cv2.resize(rgb[:h // 2 * 2, :w // 2 * 2], (w // 2, h // 2), interpolation=cv2.INTER_AREA).max(axis=-1)
    hot = h2[:LH * 2, :LW * 2].reshape(LH, 2, LW, 2).max(axis=(1, 3)) * 255.0 >= 245          # come lo shader: massimo delle 4 medie 2×2
    face = Yq[m]; bg = Yq[~m]
    st = dict(face_med=float(np.median(face)), face_p05=float(np.percentile(face, 5)), face_p95=float(np.percentile(face, 95)),
              face_hot=float(hot[m].mean() * 100), bg_p90=float(np.percentile(bg, 90)) if bg.size else 128.0,
              frame_hot=float(hot.mean() * 100), veil=float(np.median(face_veil.min(axis=1)) * 255.0))
    wts = auto_weights(st) if profile == 'auto' else {k: float(k == profile) for k in PROFILES}
    P = blend_params(wts, strength)

    # base/dettaglio: filtro guidato autoguidato in log sulla griglia 1/4
    Jq = dehaze(q, veil_q, cap, P['w'])
    Lq = toL(Jq @ LUMA)
    eps = 0.040 ** 2
    mI = box(Lq, gr); mII = box(Lq * Lq, gr); var = mII - mI * mI
    a = var / (var + eps); b = mI - a * mI
    a = box(a, gr); b = box(b, gr)
    mid = float(np.median((a * Lq + b)[y0:y1, x0:x1]))

    # per pixel
    J = dehaze(rgb, up(veil_q, w, h), cap, P['w'])
    Y = J @ LUMA
    L = toL(Y)
    base = up(a, w, h) * L + up(b, w, h)
    det = L - base
    d = base - mid
    s = 0.5 + 0.5 * np.tanh(d / 0.04)
    base2 = toL(P['target']) + d * (P['cs'] + (P['ch'] - P['cs']) * s)
    core = 0.006
    Lo = base2 + P['kd'] * det * np.clip((np.abs(det) - core) / (2 * core), 0, 1)
    Yo = fromL(Lo); k = P['knee']
    Yo = np.clip(np.where(Yo > k, k + (1 - k) * (1 - np.exp(-(Yo - k) / (1 - k))), Yo), 0, 1)

    # occhi
    eyemask = np.zeros((h, w), np.float32); eyeinfo = []
    if eyes and eye_amt > 0:
        for e in eyes:
            box_, ell = eye_geometry(e, w, h)
            lv = eye_levels(sample_patch(Yo, box_), e, box_)
            if lv is None: continue
            lut = eye_curve(*lv)
            mm = ellipse_mask(w, h, ell) * eye_amt
            Ye = np.interp(Yo * 255.0, np.arange(256), lut)
            Yo = Yo + mm * (Ye - Yo); eyemask = np.maximum(eyemask, mm)
            eyeinfo.append(dict(levels=lv, lut=lut, box=box_, ellipse=ell))

    # colore: rapporto rispetto alla luminanza ripulita, saturazione contenuta (meno negli occhi), niente canali oltre 1
    C = J * (Yo / np.maximum(Y, 2e-3))[..., None]
    g = Yo[..., None]; C = g + (P['sat'] * (1 - 0.3 * eyemask[..., None])) * (C - g)
    mx = C.max(axis=-1, keepdims=True)
    C = np.where(mx > 1, g + (C - g) * ((1 - g) / np.maximum(mx - g, 1e-4)), C)
    out = np.clip(C * 255 + 0.5, 0, 255).astype(np.uint8)
    if return_debug:
        return out, dict(stats=st, weights=wts, params=P, mid=mid, cap=cap.tolist(), eyes=eyeinfo, Yo=Yo)
    return out


def eyes_from_landmarks(lm, w, h):
    """Contorno (16 punti) e iride (468-472 / 473-477) dei due occhi MediaPipe, in pixel."""
    P = lambda i: (lm[i].x * w, lm[i].y * h)
    out = []
    for cont, ic, ring in ((RC, 468, (469, 470, 471, 472)), (LC, 473, (474, 475, 476, 477))):
        c = np.array([P(i) for i in cont], np.float32); cen = np.array(P(ic), np.float32)
        r = float(np.mean([np.hypot(*(np.array(P(i)) - cen)) for i in ring]))
        out.append(dict(contour=c, iris=cen, r=max(r, 1.5)))
    return out


def face_roi(lm):
    xs = [p.x for p in lm]; ys = [p.y for p in lm]
    return (max(0.0, min(xs)), max(0.0, min(ys)), min(1.0, max(xs)), min(1.0, max(ys)))
