#!/usr/bin/env node
// Browser execution of one bundle: node browse.mjs BUNDLE OUT BROWSER ISOLATED
// Serves the bundle over loopback HTTP, launches the named browser at that
// page, and records the JSON the page posts back. ISOLATED=1 sends the
// COOP/COEP headers the full profile requires; 0 omits them so the page
// records the non-isolated result. The page itself runs matrix.mjs unchanged.
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { spawn } from 'node:child_process';
const [bundle, out, browser, isolatedArg, profiles] = process.argv.slice(2);
if (!bundle || !out || !browser || !['0', '1'].includes(isolatedArg) || !profiles) throw Error('usage: node browse.mjs BUNDLE OUT chrome|firefox|safari 0|1 PROFILE_DIRECTORY');
const isolated = isolatedArg === '1';
const launchers = JSON.parse(fs.readFileSync(path.join(bundle, 'browsers.json')));
const launcher = launchers[browser];
if (!launcher) throw Error('unknown browser ' + browser);
const types = { '.mjs': 'text/javascript', '.wasm': 'application/wasm', '.json': 'application/json', '.html': 'text/html; charset=utf-8' };
const page = `<!doctype html><meta charset="utf-8"><title>engine matrix</title><script type="module">
import { runMatrix } from './matrix.mjs';
const fetchBytes = async name => new Uint8Array(await (await fetch(name)).arrayBuffer());
const probeNames = ${JSON.stringify(fs.readdirSync(path.join(bundle, 'probes')).filter(n => n.endsWith('.wasm')).sort())};
const record = { engine: { kind: 'browser', name: ${JSON.stringify(browser)}, userAgent: navigator.userAgent, isolated_page: ${isolated} } };
try {
  const bytes = { features: await fetchBytes('features.wasm'), featuresShared: await fetchBytes('features-shared.wasm'), suspend: await fetchBytes('suspend.wasm'), invalid: await fetchBytes('invalid.wasm'), probes: {} };
  for (const n of probeNames) bytes.probes[n.replace(/\\.wasm$/, '')] = await fetchBytes('probes/' + n);
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const spawnWaiter = data => new Promise((resolve, reject) => {
    const w = new Worker('./wait-worker.mjs', { type: 'module' });
    const timer = setTimeout(() => { w.terminate(); reject(Error('WAITER_TIMEOUT')); }, 15000);
    w.onmessage = e => { clearTimeout(timer); w.terminate(); resolve(e.data); };
    w.onerror = e => { clearTimeout(timer); reject(Error(e.message || 'worker error')); };
    w.postMessage(data);
  });
  Object.assign(record, await runMatrix({ engine: record.engine, bytes, spawnWaiter, sleep }));
} catch (e) { record.page_failure = { error: e.constructor.name, message: e.message }; }
await fetch('./result', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(record) });
document.body.textContent = 'engine matrix recorded; this tab can be closed';
</script>`;
let child = null, finished = false;
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1');
  if (req.method === 'POST' && url.pathname === '/result') {
    let body = '';
    req.on('data', d => { body += d; });
    req.on('end', () => {
      res.writeHead(200, { 'content-type': 'text/plain' }); res.end('recorded');
      const record = JSON.parse(body);
      fs.mkdirSync(out, { recursive: true });
      fs.writeFileSync(path.join(out, 'observed.json'), JSON.stringify(record, null, 2) + '\n');
      finished = true;
      setTimeout(() => finish(0), 250);
    });
    return;
  }
  const headers = { 'cache-control': 'no-store' };
  if (isolated) Object.assign(headers, { 'Cross-Origin-Opener-Policy': 'same-origin', 'Cross-Origin-Embedder-Policy': 'require-corp' });
  if (url.pathname === '/') { res.writeHead(200, { ...headers, 'content-type': types['.html'] }); res.end(page); return; }
  const file = path.join(bundle, path.normalize(url.pathname).replace(/^(\.\.[/\\])+/, ''));
  if (!file.startsWith(bundle) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404, headers); res.end(); return; }
  res.writeHead(200, { ...headers, 'content-type': types[path.extname(file)] || 'application/octet-stream' });
  res.end(fs.readFileSync(file));
});
function finish(code) {
  server.close();
  if (child && launcher.kill) child.kill();
  process.exit(code);
}
server.listen(0, '127.0.0.1', () => {
  const url = `http://127.0.0.1:${server.address().port}/?isolated=${isolatedArg}`;
  const profile = path.join(profiles, browser);
  fs.mkdirSync(profile, { recursive: true });
  const args = launcher.arguments.map(a => a.replaceAll('{url}', url).replaceAll('{profile}', profile));
  child = spawn(launcher.executable, args, { stdio: 'ignore' });
  child.on('error', e => { fs.mkdirSync(out, { recursive: true }); fs.writeFileSync(path.join(out, 'launch-failure.json'), JSON.stringify({ error: e.message }) + '\n'); finish(1); });
  setTimeout(() => { if (!finished) { fs.mkdirSync(out, { recursive: true }); fs.writeFileSync(path.join(out, 'launch-failure.json'), JSON.stringify({ error: 'BROWSER_TIMEOUT' }) + '\n'); finish(1); } }, 45000);
});
