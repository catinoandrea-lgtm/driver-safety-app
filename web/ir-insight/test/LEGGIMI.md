# Script di verifica

Richiedono Python 3 con `opencv-python-headless`, `numpy`, `mediapipe`, e Node con `playwright` (Chromium).
`DIR` è una cartella di lavoro con:
- `DIR/x/` — gli ZIP delle sessioni DMS Light5C estratti (una cartella per ZIP, con `frame_NNN/original.png`);
- `DIR/models/face_landmarker.task` — il modello MediaPipe (lo stesso usato dalla pagina);
- `DIR/out/`, `DIR/parity/` — create dagli script.

| Script | Cosa fa |
|---|---|
| `evaluate.py DIR` | rilevamento, contrasti degli occhi e metriche del volto su tutti i fotogrammi: grezza vs profili `auto`, `back`, `spot` |
| `make_cases.py DIR` | casi di parità (2 fotogrammi per sessione, con ROI e occhi dai landmark) in `DIR/parity/cases.json` |
| `node run_engine.js ../IR_InSight_Software_0_10_0.html DIR/parity/cases.json DIR/parity/gpu gpu` | esegue il motore della pagina in Chromium headless (`gpu` o `cpu`) |
| `parity.py DIR gpu` | confronta l'uscita del motore con `facelight_reference.py` |
| `node e2e.js ../IR_InSight_Software_0_10_0.html frames.json OUTDIR` | pagina completa con fotocamera simulata da un canvas (fotogrammi in `frames.json`: `[{path, sec}]`) |
| `node e2e_fps_cadenza.js ../IR_InSight_Software_0_10_1.html frames.json OUTDIR [1]` | 0.10.1: minimo FPS accettato (o rifiutato con `1`), cadenza 1×/2×, patch occhi nativa a 360 px |

`mp_eval.py` contiene l'elenco delle sessioni e la condizione di luce di ciascuna.
