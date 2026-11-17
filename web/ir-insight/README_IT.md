# IR InSight Software 0.10.1 — filtri volto per il DMS

Banco di prova nel browser (telefono o PC) per i filtri d'immagine del Driver Monitoring System.
La 0.10.0 aggiunge alla 0.9.3 due **filtri volto di giorno** e un **potenziamento degli occhi**,
pensati per far arrivare al riconoscimento facciale un volto netto, con palpebre, iride e pupilla distinguibili.

File principale: `IR_InSight_Software_0_10_1.html` (la 0.10.0 resta per confronto) (pagina unica, nessuna installazione).
Va aperta via HTTPS o `localhost` per avere la fotocamera. Il rilevatore MediaPipe si scarica alla prima apertura (circa 13 MB).

## I due filtri

| Profilo | Quando | Cosa fa |
|---|---|---|
| **Controluce** (`back`) | sole o cielo dietro la testa, sole nell'inquadratura, flare sulle lenti | toglie il velo del flare (minimo locale per canale, limitato al velo misurato sul volto), porta il volto a una luminosità piena, comprime cielo e sfondo |
| **Luce puntata** (`spot`) | sole o lampada diretti sul volto | comprime le luci bruciate di fronte e naso (spalla morbida), schiarisce le ombre dure: orbite, ombra del naso, ombra del telefono/mano |
| Luce normale (`neutral`) | luce morbida | interventi leggeri |
| Classico 0.9.3 (`classic`) | confronto | livelli + CLAHE della versione precedente, nessun filtro volto |

In **automatico** il filtro sceglie da solo, con passaggio continuo, guardando il volto e lo sfondo
(sfondo molto più chiaro del volto o velo sul volto → controluce; luci del volto vicine alla saturazione con ombre dure → luce puntata).
La scelta si legge nel badge «profilo» dell'anteprima e nella scheda «Filtri volto».

Come funziona, in breve:

1. **Velo del flare**: sulla griglia 1/4 il minimo locale di ogni canale (ampio mezzo volto) stima la luce parassita; viene sottratta con trasmissione minima 0,4 e mai sulle zone bruciate.
2. **Base e dettaglio**: filtro guidato autoguidato in scala logaritmica sulla griglia 1/4. I bordi netti (contorno della testa contro il cielo, bordo dell'ombra del naso) restano nella base: la compressione non crea aloni e il dettaglio fine (palpebre, ciglia, iride) resta intatto.
3. **Ancoraggio sul volto**: la mediana della base nella zona del volto (dal rilevatore) va alla luminosità obiettivo del profilo; sopra e sotto il volto la base è compressa con pendenze diverse (controluce: sfondo chiaro molto compresso; luce puntata: ombre sollevate).
4. **Dettaglio** amplificato con soglia del rumore, **spalla** sulle alte luci, **colore** conservato con saturazione contenuta.
5. **Occhi** (vedi sotto).

Di notte i filtri volto si spengono con continuità e resta il filtro notte della 0.9.3 (media temporale, poco guadagno).

## Potenziamento degli occhi

Con i 478 landmark di MediaPipe (contorno dell'occhio di 16 punti, centro e raggio dell'iride) il filtro legge una patch
48×32 per occhio e misura quattro livelli: **pupilla**, **iride**, **sclera** e **pelle delle palpebre**.
Da questi costruisce una curva per occhio, applicata con una maschera ellittica sfumata:

- la pelle della palpebra resta al suo livello → **un occhio chiuso non diventa mai «aperto»** (requisito per PERCLOS/EAR);
- sotto quel livello il contrasto si espande (ciglia, bordo palpebrale, iride), tra iride e pupilla di più;
- sopra, la sclera si schiarisce un poco; il riflesso corneale è escluso dalle misure.

Livelli: nessuno / leggero / normale (predefinito) / forte. Se il volto sparisce il potenziamento si spegne in circa 0,2 s.
La vista **«Filtrata + zoom occhi»** mostra i due occhi ingranditi, grezzi sopra e filtrati sotto.

Nota: per «papilla» ho inteso la **palpebra** (bordo palpebrale e piega), che è la struttura usata dal DMS per apertura/chiusura.

## Frequenza e cadenza (0.10.1)

- La fotocamera si apre chiedendo almeno 20 FPS con esposizione automatica; se il telefono non lo accetta si apre senza minimo.
- L'esposizione non viene mai messa in manuale: resta il controllo automatico e i filtri lavorano su immagini non bruciate.
- «Rilevatore: ogni fotogramma (1×)» dà più misure degli occhi al secondo; «un fotogramma su 2 (2×)» dà più FPS ma riusa i landmark nei fotogrammi intermedi. Il badge mostra «FPS · ril/s»: per il DMS conta il secondo numero.

## Integrazione nel DMS

Il motore è il primo `<script>` del file e non dipende dalla pagina:

```js
const filter = IRFilter.create({ mode: 'auto', procW: 480, flProfile: 'auto', eyeBoost: 0.7 });
// a ogni fotogramma nuovo:
filter.process(video);                                   // risultato in filter.canvas
const res = landmarker.detectForVideo(filter.canvas, performance.now());
filter.setROI([x0, y0, x1, y1]);                         // riquadro del volto 0..1
filter.setEyes([{ contour: [[x, y], …16], iris: [x, y], r }, { … }]);   // pixel; null se il volto non c'è
```

`filter.stats.fl` riporta pesi dei profili, velo, livelli degli occhi e i contrasti pupilla↔iride / iride↔sclera
misurati sul grezzo e sul filtrato.

## Altri file

- `facelight_reference.py` — riferimento Python passo-passo (stessi parametri); l'uscita GPU coincide entro ~1 livello su 255.
- `test/` — script di verifica: valutazione sulle sessioni registrate, parità GPU/CPU ↔ Python, prova della pagina completa.
- `docs/` — confronti grezzo/filtrato su fotogrammi reali e vista zoom occhi.
- `TEST_REPORT.md`, `CHANGELOG.md`.
- `IR_InSight_Software_0_9_3.html` — versione precedente, per confronto.

## Limiti

- Filtro a esposizione singola: non ricostruisce pixel saturi in tutti i canali né dettagli assenti.
- Con lenti scure il segnale dell'occhio resta debole: il potenziamento ne aumenta il contrasto ma anche il rumore.
- Le prove fin qui sono su 38 fotogrammi di sette sessioni a luce visibile (480×640). Manca la validazione sul telefono in auto e con illuminatore IR 850/940 nm.
