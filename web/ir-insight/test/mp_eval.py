import cv2, numpy as np, glob, os, sys, json
import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision
S=sys.argv[1]
opts=vision.FaceLandmarkerOptions(base_options=mpt.BaseOptions(model_asset_path=S+'/models/face_landmarker.task'),running_mode=vision.RunningMode.IMAGE,num_faces=1)
det=vision.FaceLandmarker.create_from_options(opts)
COND={'291de158':'back','ebaad68d':'back','87c668eb':'back_sun','8e55dd41':'back_sun','4584e70b':'spot','50884581':'spot','acf13f5a':'spot'}
def frames():
    for d in sorted(glob.glob(S+'/x/*Session*')):
        k=os.path.basename(d)[:8]
        for f in sorted(glob.glob(d+'/frame_*/original.png')):
            yield k,COND[k],f
def run(rgb):
    r=det.detect(mp.Image(image_format=mp.ImageFormat.SRGB,data=np.ascontiguousarray(rgb)))
    return r.face_landmarks[0] if r.face_landmarks else None
if __name__=='__main__':
    res={}
    for k,c,f in frames():
        rgb=cv2.cvtColor(cv2.imread(f),cv2.COLOR_BGR2RGB); lm=run(rgb)
        res.setdefault(c,[]).append(lm is not None)
        print(k,c,f.split('/')[-2],len(lm) if lm else 0)
    for c,v in res.items(): print(c,sum(v),'/',len(v))
