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
  return `
function backendBase(env) {
  return (
    env.PIPELINE_API_BASE ||
    env.VITE_PIPELINE_API_BASE ||
    env.BACKEND_API_BASE ||
    ''
  ).replace(/\\/+$/, '');
}

async function proxyToBackend(request, env) {
  const base = backendBase(env);
  if (!base) {
    return new Response('Backend API base is not configured', {
      status: 500,
      headers: { 'content-type': 'text/plain; charset=utf-8' },
    });
  }

  const url = new URL(request.url);
  const target = new URL(url.pathname.replace(/^\\/(pipeline|api)/, '/pipeline') + url.search, base);
  const headers = new Headers(request.headers);
  headers.set('host', new URL(base).host);
  const init = {
    method: request.method,
    headers,
    redirect: 'manual',
  };
  if (!['GET', 'HEAD'].includes(request.method)) {
    init.body = await request.arrayBuffer();
  }
  return fetch(new Request(target, init));
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith('/pipeline') || url.pathname.startsWith('/api')) {
      return proxyToBackend(request, env);
    }

    if (env.ASSETS?.fetch) {
      const assetResponse = await env.ASSETS.fetch(request);
      if (assetResponse.status !== 404) return assetResponse;
      const fallback = new URL(request.url);
      fallback.pathname = '/index.html';
      return env.ASSETS.fetch(new Request(fallback, request));
    }

    return new Response('Asset binding unavailable', {
      status: 500,
      headers: { 'content-type': 'text/plain; charset=utf-8' },
    });
  },
};
`;
}
