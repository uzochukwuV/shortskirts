const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');
const pipelineDir = path.join(rootDir, 'artifacts', 'pipeline');
const srcDir = path.join(pipelineDir, 'src');
const requirementsPath = path.join(pipelineDir, 'requirements.txt');
const venvDir = path.join(pipelineDir, '.venv-py311');
const workload = process.env.WORKER_WORKLOAD || process.argv[2] || 'story';

function candidatePythonBins() {
  const uvPython = process.env.APPDATA
    ? path.join(process.env.APPDATA, 'uv', 'python', 'cpython-3.11.15-windows-x86_64-none', 'python.exe')
    : null;

  return [
    process.env.PYTHON_BIN,
    uvPython,
    process.platform === 'win32' ? 'py -3.11' : 'python3.11',
    process.platform === 'win32' ? 'python' : 'python3',
    process.platform === 'win32' ? 'python3' : 'python',
  ].filter(Boolean);
}

function runCheck(command, args) {
  const result = spawnSync(command, args, { stdio: 'ignore', shell: false });
  return !result.error && result.status === 0;
}

function resolvePython() {
  const localPython = process.platform === 'win32'
    ? path.join(venvDir, 'Scripts', 'python.exe')
    : path.join(venvDir, 'bin', 'python');

  if (fs.existsSync(localPython)) {
    return localPython;
  }

  for (const candidate of candidatePythonBins()) {
    if (candidate.includes('py -3.11')) {
      if (runCheck('py', ['-3.11', '--version'])) {
        return ['py', ['-3.11']];
      }
      continue;
    }

    if (runCheck(candidate, ['--version'])) {
      return [candidate, []];
    }
  }

  return null;
}

function runOrDie(command, args, options = {}) {
  const result = spawnSync(command, args, {
    stdio: 'inherit',
    env: { ...process.env, CI: 'true' },
    shell: false,
    ...options,
  });

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0) {
    process.exit(result.status || 1);
  }
}

function pythonCmd(base, extraArgs = []) {
  if (Array.isArray(base)) {
    return { command: base[0], args: [...base[1], ...extraArgs] };
  }
  return { command: base, args: extraArgs };
}

const bootstrap = resolvePython();
if (!bootstrap) {
  console.error('[worker] Python 3.11 is required but was not found.');
  process.exit(1);
}

if (!fs.existsSync(venvDir)) {
  console.log(`[worker] Creating Python 3.11 virtualenv in ${venvDir}...`);
  const create = pythonCmd(bootstrap, ['-m', 'venv', venvDir]);
  runOrDie(create.command, create.args);
}

const pythonBin = process.platform === 'win32'
  ? path.join(venvDir, 'Scripts', 'python.exe')
  : path.join(venvDir, 'bin', 'python');
if (!fs.existsSync(pythonBin)) {
  console.error('[worker] Virtualenv interpreter is missing. Remove artifacts/pipeline/.venv-py311 and rerun.');
  process.exit(1);
}

const depsCheck = spawnSync(pythonBin, ['-c', 'import asyncpg, redis'], { stdio: 'ignore', shell: false });
if (depsCheck.status !== 0) {
  console.log('[worker] Installing backend dependencies into the Python 3.11 virtualenv...');
  runOrDie(pythonBin, ['-m', 'pip', 'install', '--upgrade', 'pip']);
  runOrDie(pythonBin, ['-m', 'pip', 'install', '-r', requirementsPath]);
}

console.log(`[worker] Starting StoryForge queue worker (${workload})...`);
const worker = spawn(pythonBin, ['-m', 'worker'], {
  cwd: srcDir,
  stdio: 'inherit',
  env: { ...process.env, WORKER_WORKLOAD: workload },
  windowsHide: true,
  shell: false,
});

worker.on('exit', (code, signal) => {
  if (signal) {
    process.exit(1);
  }
  process.exit(code ?? 1);
});
