# Changelog

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
