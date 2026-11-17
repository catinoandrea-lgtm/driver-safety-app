// Test della pagina completa: la fotocamera è sostituita da un flusso di canvas che riproduce fotogrammi reali.
// MediaPipe vero (CDN). Avvio, aggancio occhi, viste, prova A/B breve, ZIP, cambio profili e motore.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path');
const [HTML, FRAMES, OUT] = process.argv.slice(2);
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const frames = JSON.parse(fs.readFileSync(FRAMES, 'utf8')).map(f => ({ sec: f.sec, url: 'data:image/png;base64,' + fs.readFileSync(f.path).toString('base64') }));
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const ctx = await browser.newContext({ viewport: { width: 1000, height: 1400 }, acceptDownloads: true });
  await ctx.route('http://localhost:9/**', r => r.fulfill({ body: fs.readFileSync(HTML), contentType: 'text/html' }));
  await ctx.addInitScript(frames => {
    // finta fotocamera: canvas 480×640 a 15 FPS con la sequenza di fotogrammi, esposta come getUserMedia
    const cv = document.createElement('canvas'); cv.width = 480; cv.height = 640; const cx = cv.getContext('2d'); const imgs = frames.map(f => { const i = new Image(); i.src = f.url; return { i, sec: f.sec }; });
    const total = frames.reduce((s, f) => s + f.sec, 0); let t0 = 0;
    const draw = () => { const t = ((performance.now() - t0) / 1000) % total; let acc = 0, cur = imgs[0]; for (const f of imgs) { if (t < acc + f.sec) { cur = f; break; } acc += f.sec; } if (cur.i.complete) cx.drawImage(cur.i, 0, 0); };
    navigator.mediaDevices.getUserMedia = async () => { t0 = performance.now(); draw(); setInterval(draw, 1000 / 15); const s = cv.captureStream(15); const tr = s.getVideoTracks()[0]; tr.getSettings = () => ({ width: 480, height: 640, frameRate: 15, facingMode: 'user' }); tr.getCapabilities = () => ({}); return s; };
  }, frames);
  const page = await ctx.newPage(); const errs = [];
  page.on('pageerror', e => { errs.push(e.message); console.log('[pageerror]', e.message); });
  page.on('console', m => { if (m.type() === 'error') console.log('[console.error]', m.text()); });
  await page.goto('http://localhost:9/index.html'); await page.click('#start');
  const t0 = Date.now(); let st;
  while (Date.now() - t0 < 150000) { await sleep(2000); st = await page.evaluate(() => ({ ab: __ir.ab.ready, status: document.getElementById('abStatus').textContent, eyes: !!__ir.engine?._eyes })); if (st.ab && st.eyes) break; }
  console.log('rilevatore:', JSON.stringify(st));
  const snap = label => page.evaluate(label => { const e = __ir.engine, s = e.stats, r = x => (x == null ? null : Math.round(x * 1000) / 1000); return { label, kind: e.kind, W: e.W, H: e.H, flW: r(s.flW), w: s.fl && Object.fromEntries(Object.entries(s.fl.w).map(([k, v]) => [k, r(v)])), eyes: s.fl && s.fl.eyes.map(x => x && x.map(r)), eyeAmt: s.fl && s.fl.eyeAmt.map(r), bProf: document.getElementById('bProf').textContent, det: [document.getElementById('aDet').textContent, document.getElementById('bDet').textContent], PI: [document.getElementById('aPI').textContent, document.getElementById('bPI').textContent], IS: [document.getElementById('aIS').textContent, document.getElementById('bIS').textContent], fps: r(__ir.fps), ms: r(__ir.tim.filter) }; }, label);
  const shots = [];
  for (let i = 0; i < 4; i++) { const s = await snap('t' + i); console.log(JSON.stringify(s)); shots.push(s); await page.locator('.preview').screenshot({ path: path.join(OUT, `preview_${i}.png`) }); await sleep(5000); }
  await page.selectOption('#viewMode', 'eyes'); await sleep(1500); await page.locator('.preview').screenshot({ path: path.join(OUT, 'eyes_view.png') });
  console.log('flNote:', (await page.textContent('#flNote')).slice(0, 400));
  await page.selectOption('#viewMode', 'side');
  await page.selectOption('#abDur', '10'); await page.click('#abTrial'); await sleep(13000);
  console.log('verdetto:', await page.textContent('#abVerdict'));
  const dl = page.waitForEvent('download'); await page.click('#zip'); const d = await dl; await d.saveAs(path.join(OUT, 'archivio.zip'));
  for (const p of ['back', 'spot', 'classic', 'auto']) { await page.selectOption('#flProfile', p); await sleep(1500); console.log('profilo', p, JSON.stringify(await snap(p))); }
  await page.evaluate(() => document.querySelectorAll('details').forEach(d => d.open = true)); await page.selectOption('#mode', 'night'); await sleep(2500); console.log('notte', JSON.stringify(await snap('night'))); await page.selectOption('#mode', 'auto');
  await page.selectOption('#engineSel', 'cpu'); await sleep(4000); console.log('cpu', JSON.stringify(await snap('cpu')));
  await page.locator('.preview').screenshot({ path: path.join(OUT, 'preview_cpu.png') });
  await page.screenshot({ path: path.join(OUT, 'page.png'), fullPage: true });
  fs.writeFileSync(path.join(OUT, 'e2e.json'), JSON.stringify({ errs, shots }, null, 1));
  console.log('errori pagina:', errs.length);
  await browser.close();
})();
