# Changelog

## 0.10.1 — frequenza della fotocamera e cadenza del rilevatore
- Apertura della fotocamera con `frameRate { ideal: 30, min: 20, max: 30 }`: l'esposizione resta **automatica** ma non si allunga oltre ~50 ms; se il driver rifiuta il minimo la fotocamera si riapre senza (evento `fps-min`). Lo stesso minimo vale quando il pilota automatico o i pulsanti tornano a 20-30 FPS; la scelta notturna dei 15 FPS resta possibile.
- **Nessuna esposizione manuale**: niente `exposureMode: "manual"`, `exposureTime` o `iso` fissi (di giorno brucerebbero l'immagine, con luci a 100 Hz creerebbero sfarfallio, e i filtri non potrebbero recuperare).
- Cadenza del rilevatore selezionabile: ogni fotogramma (1×, predefinita) o uno su due (2×). Nei fotogrammi senza rilevamento restano i landmark precedenti; metriche, prove A/B e prova occhi contano solo i rilevamenti nuovi.
- Badge «FPS · ril/s»: FPS della fotocamera e rilevamenti al secondo, separati. Nuove colonne `detectorStride`, `detHzA`, `detHzB`, `cameraMinFps` in `prove.csv`.
- Contatore FPS corretto: media degli intervalli invece della media delle frequenze istantanee, che con fotogrammi irregolari (cadenza 2×) sovrastimava (17 FPS mostrati contro ~11 reali nella prova).
- Patch degli occhi letta dal video a risoluzione nativa (di giorno): con l'elaborazione a 360 px pupilla e iride restano misurabili.
- Modalità a ramo singolo (solo B filtrata / solo A senza filtro): rimandate, da aggiungere su conferma.


## 0.10.0 — filtri volto
- Nuovi filtri volto di giorno (FaceLight): **controluce** e **luce puntata**, più «luce normale», con scelta automatica e passaggio continuo; «classico 0.9.3» resta disponibile.
- Velo del flare stimato per canale sulla griglia 1/4 e sottratto solo fino al velo misurato sul volto; zone bruciate lasciate intatte.
- Base/dettaglio con filtro guidato in scala logaritmica: compressione dello sfondo e recupero delle ombre senza aloni sul contorno della testa.
- Esposizione ancorata alla mediana della base sul volto, con compensazione immediata dei salti di luce.
- **Potenziamento degli occhi** guidato dai landmark (contorno a 16 punti e iride): curva per occhio da pupilla, iride, sclera e pelle delle palpebre, ancorata alla palpebra perché un occhio chiuso resti chiuso. Livelli nessuno/leggero/normale/forte.
- Nuova vista «Filtrata + zoom occhi» (grezza sopra, filtrata sotto).
- Nuove metriche: pesi dei profili, contrasti pupilla↔iride e iride↔sclera su grezza e filtrata (anche nella tabella A/B).
- Esportazione: colonne `FL_*`, `eyePI_A/B`, `eyeIS_A/B` in `prove.csv` e `campioni.csv`; riepilogo `faceLight` in `prove.json`.
- API: `filter.setEyes(eyes)`; `filter.stats.fl`; `IRFilter.FACE_PROFILES`, `IRFilter.FL`.
- Motore CPU di riserva: FaceLight completo, a colori.
- Di notte i filtri volto si spengono con continuità; il ramo notturno è invariato rispetto alla 0.9.3.
- Riferimento Python `facelight_reference.py` e script di verifica in `test/`.
