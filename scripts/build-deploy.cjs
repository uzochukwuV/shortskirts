const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const rootDir = path.resolve(__dirname, '..');
const appDir = path.join(rootDir, 'artifacts', 'app');
const appDistDir = path.join(appDir, 'dist', 'public');
const distDir = path.join(rootDir, 'dist');
const distPublicDir = path.join(distDir, 'public');
const distServerDir = path.join(distDir, 'server');
const distOpenAiDir = path.join(distDir, '.openai');
const hostingJsonPath = path.join(distOpenAiDir, 'hosting.json');
const backendRunScript = path.join(rootDir, 'artifacts', 'pipeline', 'run.sh');

const build = spawnSync('npm', ['--prefix', 'artifacts/app', 'run', 'build'], {
  cwd: rootDir,
  stdio: 'inherit',
  env: { ...process.env, CI: 'true' },
  shell: false,
});

if (build.status !== 0) {
  process.exit(build.status ?? 1);
}

fs.rmSync(distDir, { recursive: true, force: true });
fs.mkdirSync(distPublicDir, { recursive: true });
fs.mkdirSync(distServerDir, { recursive: true });
fs.mkdirSync(distOpenAiDir, { recursive: true });

fs.cpSync(appDistDir, distPublicDir, { recursive: true });
fs.writeFileSync(
  hostingJsonPath,
  JSON.stringify({ project_id: 'appgprj_6a5a266eb2a48191b8ec37550e051774' }, null, 2) + '\n',
);
fs.writeFileSync(path.join(distServerDir, 'index.js'), makeServerBundle());

function makeServerBundle() {
  return `'use strict';

const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { spawn } = require('node:child_process');

const publicDir = path.resolve(__dirname, '..', 'public');
const backendPort = Number(process.env.PIPELINE_PORT || '8000');
const appPort = Number(process.env.PORT || '3000');
const backendUrl = new URL(\`http://127.0.0.1:\${backendPort}\`);
let backendStarted = false;

function contentType(filePath) {
  switch (path.extname(filePath).toLowerCase()) {
    case '.html':
      return 'text/html; charset=utf-8';
    case '.css':
      return 'text/css; charset=utf-8';
    case '.js':
      return 'application/javascript; charset=utf-8';
    case '.json':
      return 'application/json; charset=utf-8';
    case '.svg':
      return 'image/svg+xml';
    case '.png':
      return 'image/png';
    case '.jpg':
    case '.jpeg':
      return 'image/jpeg';
    case '.webp':
      return 'image/webp';
    case '.ico':
      return 'image/x-icon';
    default:
      return 'application/octet-stream';
  }
}

function startBackend() {
  if (backendStarted) return;
  const runScript = path.resolve(__dirname, '..', '..', 'artifacts', 'pipeline', 'run.sh');
  if (!fs.existsSync(runScript)) {
    console.warn('[deploy] backend run script not found, serving frontend only');
    return;
  }

  backendStarted = true;
  const child = spawn('bash', [runScript], {
    cwd: path.resolve(__dirname, '..', '..'),
    env: { ...process.env, PORT: String(backendPort) },
    stdio: 'inherit',
    detached: false,
  });

  child.on('exit', (code, signal) => {
    console.log(\`[deploy] backend exited code=\${code} signal=\${signal || ''}\`);
  });
}

function sendFile(res, filePath) {
  const stream = fs.createReadStream(filePath);
  res.writeHead(200, { 'content-type': contentType(filePath) });
  stream.on('error', () => {
    res.writeHead(500);
    res.end('Internal Server Error');
  });
  stream.pipe(res);
}

function resolveAsset(urlPath) {
  const cleaned = urlPath === '/' ? '/index.html' : urlPath;
  const candidate = path.join(publicDir, cleaned);
  if (!candidate.startsWith(publicDir)) return null;
  if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) return candidate;
  return null;
}

function proxyToBackend(req, res) {
  const upstream = http.request(
    {
      protocol: backendUrl.protocol,
      hostname: backendUrl.hostname,
      port: backendUrl.port,
      method: req.method,
      path: req.url,
      headers: req.headers,
    },
    (upstreamRes) => {
      res.writeHead(upstreamRes.statusCode || 502, upstreamRes.headers);
      upstreamRes.pipe(res);
    },
  );

  upstream.on('error', () => {
    res.writeHead(502, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('Backend unavailable');
  });

  req.pipe(upstream);
}

startBackend();

http
  .createServer((req, res) => {
    const url = new URL(req.url || '/', \`http://127.0.0.1:\${appPort}\`);

    if (url.pathname.startsWith('/pipeline') || url.pathname.startsWith('/api')) {
      proxyToBackend(req, res);
      return;
    }

    const assetPath = resolveAsset(url.pathname);
    if (assetPath) {
      sendFile(res, assetPath);
      return;
    }

    sendFile(res, path.join(publicDir, 'index.html'));
  })
  .listen(appPort, '0.0.0.0', () => {
    console.log(\`[deploy] StoryForge Studio listening on :\${appPort}\`);
  });
`;
}
