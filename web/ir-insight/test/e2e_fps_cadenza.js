// 0.10.1: FPS minimo (accettato o rifiutato), cadenza 1×/2×, patch occhi nativa con elaborazione a 360 px, prova occhi e A/B.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path');
const [HTML, FRAMES, OUT, REJECT] = process.argv.slice(2);
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const frames = JSON.parse(fs.readFileSync(FRAMES, 'utf8')).map(f => ({ sec: f.sec, url: 'data:image/png;base64,' + fs.readFileSync(f.path).toString('base64') }));
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const ctx = await browser.newContext({ viewport: { width: 1000, height: 1400 }, acceptDownloads: true });
  await ctx.route('http://localhost:9/**', r => r.fulfill({ body: fs.readFileSync(HTML), contentType: 'text/html' }));
  await ctx.addInitScript(({ frames, reject }) => {
    const cv = document.createElement('canvas'); cv.width = 720; cv.height = 960; const cx = cv.getContext('2d'); const imgs = frames.map(f => { const i = new Image(); i.src = f.url; return { i, sec: f.sec }; });
    const total = frames.reduce((s, f) => s + f.sec, 0); let t0 = 0;
    const draw = () => { const t = ((performance.now() - t0) / 1000) % total; let acc = 0, cur = imgs[0]; for (const f of imgs) { if (t < acc + f.sec) { cur = f; break; } acc += f.sec; } if (cur.i.complete) cx.drawImage(cur.i, 0, 0, 720, 960); };
    window.__gum = [];
    navigator.mediaDevices.getUserMedia = async c => { window.__gum.push(JSON.stringify(c.video.frameRate));
      if (reject && c.video.frameRate && c.video.frameRate.min) { const e = new Error('min fps'); e.name = 'OverconstrainedError'; throw e; }
      t0 = performance.now(); draw(); setInterval(draw, 1000 / 20); const s = cv.captureStream(20); const tr = s.getVideoTracks()[0]; tr.getSettings = () => ({ width: 720, height: 960, frameRate: 20, facingMode: 'user' }); tr.getCapabilities = () => ({}); return s; };
  }, { frames, reject: REJECT === '1' });
  const page = await ctx.newPage(); const errs = [];
  page.on('pageerror', e => { errs.push(e.message); console.log('[pageerror]', e.message); });
  await page.goto('http://localhost:9/index.html');
  await page.selectOption('#procW', '360'); await page.click('#start');
  const t0 = Date.now(); let st;
  while (Date.now() - t0 < 150000) { await sleep(2000); st = await page.evaluate(() => ({ ab: __ir.ab.ready, eyes: !!__ir.engine?._eyes })); if (st.ab && st.eyes) break; }
  const info = () => page.evaluate(() => { const e = __ir.engine, s = e.stats, r = x => (x == null ? null : Math.round(x * 100) / 100);
    return { W: e.W, H: e.H, gum: window.__gum, badge: document.getElementById('bFps').textContent, hz: __ir.ab.hz && Object.fromEntries(Object.entries(__ir.ab.hz).map(([k, v]) => [k, r(v)])), fps: r(__ir.fps), eyes: s.fl && s.fl.eyes.map(x => x && x.map(r)), eyeAmt: s.fl && s.fl.eyeAmt.map(r), PI: [document.getElementById('aPI').textContent, document.getElementById('bPI').textContent], IS: [document.getElementById('aIS').textContent, document.getElementById('bIS').textContent], det: [document.getElementById('aDet').textContent, document.getElementById('bDet').textContent], log: document.getElementById('pilotLog').textContent }; });
  await sleep(3000); console.log('2x', JSON.stringify(await info()));
  await page.selectOption('#abDur', '10'); await page.click('#abTrial'); await sleep(12500);
  console.log('verdetto 2x:', await page.textContent('#abVerdict'));
  await page.click('#eyeTest'); await sleep(33000);
  console.log('prova occhi 2x:', JSON.stringify(await page.evaluate(() => ['eaDet', 'ebDet', 'eaOpen', 'ebOpen', 'eaOk', 'ebOk'].map(id => id + '=' + document.getElementById(id).textContent))));
  await page.selectOption('#abStride', '1'); await sleep(4000); console.log('1x', JSON.stringify(await info()));
  await page.click('#abTrial'); await sleep(12500); console.log('verdetto 1x:', await page.textContent('#abVerdict'));
  const dl = page.waitForEvent('download'); await page.click('#zip'); const d = await dl; await d.saveAs(path.join(OUT, 'archivio.zip'));
  await page.selectOption('#viewMode', 'eyes'); await sleep(1500); await page.locator('.preview').screenshot({ path: path.join(OUT, 'eyes_view_360.png') });
  console.log('errori pagina:', errs.length);
  await browser.close();
})();
