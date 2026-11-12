// Render every carousel page: serves this folder, opens page.html?p=N in Chrome, saves art + final PNG and the type layout.
import { chromium } from 'playwright-core';
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path';
const root = path.dirname(new URL(import.meta.url).pathname);
const [contentPath, outDir] = process.argv.slice(2);
if (!contentPath || !outDir) { console.error('usage: node render.mjs CONTENT.json OUT_DIR'); process.exit(2); }
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.woff2': 'font/woff2' };
const srv = http.createServer((q, r) => { const u = decodeURIComponent(q.url.split('?')[0]); const f = u === '/content.json' ? path.resolve(contentPath) : path.join(root, u); if (!fs.existsSync(f)) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'content-type': types[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(r); }).listen(8765);
const content = JSON.parse(fs.readFileSync(contentPath));
const b = await chromium.launch({ executablePath: '/usr/bin/google-chrome', args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const pg = await b.newPage({ viewport: { width: 1080, height: 1350 } });
const errs = []; pg.on('pageerror', e => errs.push(e.message)); pg.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
const layout = [];
fs.mkdirSync(path.resolve(outDir), { recursive: true });
for (let i = 0; i < content.pages.length; i++) {
  await pg.goto(`http://localhost:8765/page.html?p=${i}`);
  await pg.waitForFunction('window.DONE', null, { timeout: 60000 }).catch(() => { throw new Error('page ' + i + ': ' + errs.join(' | ')); });
  const d = await pg.evaluate('window.DONE');
  for (const k of ['art', 'final']) fs.writeFileSync(path.join(path.resolve(outDir), `${d.id}-${k}.png`), Buffer.from(d[k].split(',')[1], 'base64'));
  layout.push({ id: d.id, layout: d.layout });
}
fs.writeFileSync(path.join(path.resolve(outDir), 'layout.json'), JSON.stringify(layout, null, 1));
await b.close(); srv.close(); console.log('rendered', layout.length, errs.length ? 'errors: ' + errs.join(' | ') : '');
