# Rapporto di prova — IR InSight 0.10.0 (filtri volto)

Data: 2026-11-17. Dati: 38 fotogrammi reali 480×640 da 7 sessioni DMS Light5C (luce visibile, fotocamera frontale).
Condizioni: **controluce** (2 sessioni, 12 fotogrammi), **controluce con sole in campo / flare** (2 sessioni, 12), **luce puntata sul volto** (3 sessioni, 14; con occhiali scuri e occhi socchiusi).
Rilevatore: MediaPipe Face Landmarker (stesso modello della pagina), modalità immagine singola, senza tracking.

## 1. Effetto sul volto e sugli occhi (riferimento Python, profilo automatico)

Livelli misurati sui landmark: pupilla (20° percentile nel disco centrale dell'iride), iride (mediana dell'anello), sclera (70° percentile dentro il contorno, fuori dall'iride), pelle delle palpebre. Contrasti in frazione di 255. «Bordo palpebra» = gradiente medio sul contorno superiore.

| Condizione | | Volto rilevato | Pupilla↔iride | Iride↔sclera | Bordo palpebra | Volto bruciato | Ombre nere sul volto |
|---|---|---|---|---|---|---|---|
| Controluce | grezza | 12/12 | 0,015 | 0,051 | 0,215 | 3,8 % | 0,0 % |
| | **filtrata** | 12/12 | **0,033** | **0,098** | **0,424** | **0,0 %** | 0,1 % |
| Sole in campo / flare | grezza | **7/12** | 0,014 | 0,020 | 0,100 | 0,9 % | 0,0 % |
| | **filtrata** | **12/12** | **0,065** | **0,052** | **0,311** | 0,1 % | 0,0 % |
| Luce puntata | grezza | 14/14 | 0,043 | 0,151 | 0,439 | 0,2 % | 3,5 % |
| | **filtrata** | 14/14 | **0,065** | **0,178** | **0,502** | **0,0 %** | **0,5 %** |
| Totale | grezza | 33/38 | 0,027 | 0,087 | 0,286 | 1,6 % | 1,5 % |
| | **filtrata** | **38/38** | **0,055** | **0,113** | **0,417** | **0,03 %** | **0,2 %** |

Il profilo automatico ha scelto «controluce» su tutti i fotogrammi di controluce e «luce puntata» su quelli con sole sul volto.
Forzare il profilo sbagliato peggiora (es. «controluce» con sole sul volto: ombre nere 3,7 %, bordo palpebra 0,41).

Spostamento dei landmark filtrato ↔ grezzo (dove il grezzo trova il volto), in % della distanza tra gli occhi: 1,6 % in controluce, 1,6 % con luce puntata, 9,6 % con sole in campo. In quest'ultimo caso non c'è una verità di riferimento: con il flare anche i landmark grezzi possono essere sbagliati. Da verificare con la prova occhi guidata sul telefono.

Taratura: i parametri della luce puntata sono stati scelti con una scansione su 36 combinazioni (obiettivo volto 0,47–0,56, dettaglio 1,3–1,7, pendenze ombre/luci). Con l'obiettivo iniziale 0,47 bordo palpebra e iride↔sclera restavano sotto il grezzo (0,41 contro 0,44); con 0,56 lo superano. Per il controluce è stato scelto un valore intermedio (0,51) per non amplificare troppo il rumore su volti molto scuri.

Immagini: `docs/confronto_volto.jpg`, `docs/confronto_occhi.jpg`.

## 2. Parità motore ↔ riferimento

13 casi (2 fotogrammi per sessione, landmark reali), 14 fotogrammi per caso per far convergere i valori smorzati.

| Motore | Differenza media | Media sul volto | 99° percentile sul volto | Pesi dei profili |
|---|---|---|---|---|
| GPU (WebGL2, SwiftShader in Chromium headless) | 1,05 livelli | 1,25 | ≤ 6 | identici al riferimento |
| CPU (riserva JavaScript) | 0,62 livelli | 0,66 | ≤ 4 | identici al riferimento |

Tempi indicativi in Chromium headless su CPU di server (rendering software): GPU-SwiftShader ~39 ms per fotogramma, CPU ~74 ms. **Non** rappresentano il telefono: su GPU reale i passaggi aggiunti sono 11 sulla griglia 1/4 (120×160) più un'uscita a piena risoluzione più ricca.

## 3. Pagina completa

Chromium headless, fotocamera sostituita da un flusso di canvas che alterna 4 fotogrammi reali (5 s ciascuno), MediaPipe scaricato dalla CDN.

- Nessun errore JavaScript. Rilevatore caricato e occhi agganciati al filtro (potenziamento portato a 0,7 in ~1 s).
- Profilo automatico: «luce puntata 74 %» sulla scena con sole sul volto, «controluce 82–100 %» su quelle in controluce.
- Contrasti misurati dalla pagina (A grezza → B filtrata, livelli su 255): pupilla↔iride 13 → 23, 4 → 16, 2 → 17; iride↔sclera 14 → 32, 8 → 32, 6 → 21.
- Prova A/B da 10 s: rilevamento 95 % e 97 %, «landmark più stabili con il filtro: jitter 0,78 → 0,50».
- Modalità notte e profilo classico: filtri volto spenti, contrasti non riportati, badge coerente. Motore CPU: funziona, profilo e occhi come su GPU.
- ZIP esportato con le nuove colonne `FL_*` ed `eyePI_*`/`eyeIS_*` in `prove.csv` e `campioni.csv`.

## 4. Da fare sul telefono

1. Prova A/B e prova occhi guidata in controluce e con sole sul volto, profilo automatico, poi forzato.
2. Stesse prove con «Occhi: nessun potenziamento» per isolare l'effetto sugli occhi; controllare che la separazione EAR aperto/chiuso in B non sia peggiore di A.
3. Misurare FPS e tempo filtro sul telefono (badge «GPU … ms»).
4. Prova con illuminatore IR (850/940 nm): i filtri volto sono pensati per la luce del giorno; di notte resta il filtro notte.

Script: `test/` (vedi intestazioni). La parità si rilancia con `make_cases.py` → `run_engine.js` (gpu|cpu) → `parity.py`.
