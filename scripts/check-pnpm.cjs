const fs = require('fs');

const ua = process.env.npm_config_user_agent || '';
const exec = process.env.npm_execpath || '';
if (!/pnpm/i.test(ua) && !/pnpm/i.test(exec)) {
  console.error('Use pnpm instead');
  process.exit(1);
}

for (const file of ['package-lock.json', 'yarn.lock']) {
  try {
    fs.unlinkSync(file);
  } catch {}
}
