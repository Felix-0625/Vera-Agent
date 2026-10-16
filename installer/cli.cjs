#!/usr/bin/env node

const { spawnSync } = require('node:child_process');
const path = require('node:path');

if (process.platform !== 'win32') {
  console.error('VeraAgent 当前的 npx 引导程序只支持 Windows 桌面版。');
  process.exit(1);
}

const script = path.join(__dirname, 'install.ps1');
const result = spawnSync(
  'powershell.exe',
  ['-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script],
  { stdio: 'inherit', windowsHide: true },
);

if (result.error) {
  console.error(`无法启动安装脚本：${result.error.message}`);
  process.exit(1);
}
process.exit(result.status ?? 1);
