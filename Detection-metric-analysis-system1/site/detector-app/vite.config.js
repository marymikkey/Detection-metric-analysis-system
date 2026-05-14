import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { createReadStream, existsSync, statSync, readdirSync } from 'fs';
import { resolve, extname, basename } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import { spawnSync } from 'child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '../..');
const BACKEND = resolve(ROOT, 'backend_api.py');
const IMG_EXT = /\.(jpg|jpeg|png|webp|gif|bmp)$/i;
const MIME = { '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.gif': 'image/gif', '.bmp': 'image/bmp' };

function runPy(args) {
  const r = spawnSync('python', [BACKEND, ...args], { cwd: ROOT, encoding: 'utf8', maxBuffer: 1024 * 1024 * 80 });
  if (r.status !== 0) throw new Error((r.stderr || r.stdout || `python exited ${r.status}`).slice(-4000));
  return r.stdout;
}

function sendJson(res, data) {
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.end(typeof data === 'string' ? data : JSON.stringify(data));
}

let imageIndex = null;
function buildImageIndex() {
  if (imageIndex) return imageIndex;
  imageIndex = new Map();
  try {
    const setup = JSON.parse(runPy(['setup']));
    const dirs = (setup.datasets || []).flatMap(d => d.imageDirs || []);
    for (const dir of dirs.filter(Boolean)) {
      walkImages(String(dir));
    }
  } catch {}
  return imageIndex;
}

function walkImages(dir) {
  try {
    for (const ent of readdirSync(dir, { withFileTypes: true })) {
      const p = resolve(dir, ent.name);
      if (ent.isDirectory()) walkImages(p);
      else if (IMG_EXT.test(ent.name)) imageIndex.set(ent.name, p);
    }
  } catch {}
}

function apiPlugin() {
  return {
    name: 'detector-api',
    configureServer(server) {
      server.middlewares.use('/api/setup', (_req, res) => {
        try { sendJson(res, runPy(['setup'])); } catch (e) { res.statusCode = 500; sendJson(res, { error: e.message }); }
      });
      server.middlewares.use('/api/eda', async (req, res) => {
        try {
          const u = new URL(req.url, 'http://localhost');
          const ds = u.searchParams.get('datasets') || '';
          sendJson(res, runPy(['eda', '--datasets', ds]));
        } catch (e) { res.statusCode = 500; sendJson(res, { error: e.message }); }
      });
      server.middlewares.use('/api/validation', async (_req, res) => {
        try { sendJson(res, runPy(['validation'])); } catch (e) { res.statusCode = 500; sendJson(res, { error: e.message }); }
      });
      server.middlewares.use('/api/results', (_req, res) => {
        try { sendJson(res, runPy(['results'])); } catch (e) { res.statusCode = 500; sendJson(res, { error: e.message }); }
      });
      server.middlewares.use('/api/detection-errors', (_req, res) => {
        try { sendJson(res, runPy(['detection-errors'])); } catch (e) { res.statusCode = 500; sendJson(res, { error: e.message }); }
      });
      server.middlewares.use('/api/image', (req, res, next) => {
        const u = new URL(req.url, 'http://localhost');
        const name = decodeURIComponent(u.searchParams.get('path') || '');
        const idx = buildImageIndex();
        const filePath = idx.get(basename(name));
        if (!filePath) return next();
        if (!existsSync(filePath)) return next();
        try {
          const stat = statSync(filePath);
          if (!stat.isFile()) return next();
          const mime = MIME[extname(filePath).toLowerCase()] || 'application/octet-stream';
          res.setHeader('Content-Type', mime);
          res.setHeader('Content-Length', stat.size);
          res.setHeader('Cache-Control', 'public, max-age=3600');
          createReadStream(filePath).pipe(res);
        } catch { next(); }
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), apiPlugin()],
  server: { port: 5173 },
});
