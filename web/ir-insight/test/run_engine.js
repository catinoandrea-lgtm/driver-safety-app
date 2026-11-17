// Esegue IRFilter (dal file HTML) in Chromium headless sui casi di parità e salva le uscite PNG + statistiche.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path');
const [HTML, CASES, OUT, ENGINE] = process.argv.slice(2);
(async () => {
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage(); const errs = [];
  page.on('console', m => console.log('[page]', m.text())); page.on('pageerror', e => { errs.push(e.message); console.log('[pageerror]', e.message); });
  const src = fs.readFileSync(HTML, 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
  await page.setContent('<!doctype html><html><body></body></html>'); await page.addScriptTag({ content: src });
  const cases = JSON.parse(fs.readFileSync(CASES, 'utf8')); fs.mkdirSync(OUT, { recursive: true }); const report = [];
  for (const c of cases) {
    const url = 'data:image/png;base64,' + fs.readFileSync(c.path).toString('base64');
    const r = await page.evaluate(async ({ url, c, eng }) => {
      const img = new Image(); img.src = url; await img.decode();
      const e = IRFilter.create({ mode: 'day', procW: 480, flProfile: 'auto', eyeBoost: 0.7, flStrength: 1 }, eng);
      e.setROI(c.roi); let st = null; const times = [];
      for (let i = 0; i < 14; i++) { if (i === 2) e.setEyes(c.eyes); const t0 = performance.now(); st = e.process(img, 1000 + i * 66); times.push(performance.now() - t0); }
      const cv = document.createElement('canvas'); cv.width = e.W; cv.height = e.H; cv.getContext('2d').drawImage(e.canvas, 0, 0);
      return { kind: e.kind, renderer: e.info.renderer, err: IRFilter.lastError || null, png: cv.toDataURL('image/png'), fl: st.fl, flW: st.flW, ms: times.slice(4) };
    }, { url, c, eng: ENGINE || 'gpu' });
    fs.writeFileSync(path.join(OUT, c.id + '.png'), Buffer.from(r.png.split(',')[1], 'base64'));
    report.push({ id: c.id, kind: r.kind, renderer: r.renderer, err: r.err, flW: r.flW, fl: r.fl, ms: r.ms });
    console.log(c.id, r.kind, r.flW, r.fl && JSON.stringify(r.fl.w), r.fl && r.fl.eyes && JSON.stringify(r.fl.eyes.map(x => x && x.map(v => v == null ? null : +v.toFixed(3)))), 'ms', (r.ms.reduce((a, b) => a + b, 0) / r.ms.length).toFixed(1));
  }
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify({ errors: errs, report }, null, 1));
  await browser.close();
})();
