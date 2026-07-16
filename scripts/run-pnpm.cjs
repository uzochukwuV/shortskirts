const { spawnSync } = require('child_process');

const args = process.argv.slice(2);
const pnpmEntry = process.env.npm_execpath;

if (!pnpmEntry) {
  console.error('npm_execpath is not set. Run this through pnpm.');
  process.exit(1);
}

const result = spawnSync(process.execPath, [pnpmEntry, ...args], {
  stdio: 'inherit',
  env: { ...process.env, CI: 'true' },
  windowsHide: true,
});

if (result.error) {
  console.error(result.error);
}

process.exit(result.status ?? 1);