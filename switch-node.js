#!/usr/bin/env node

/**
 * 切换 Node.js 版本到 v20+
 * 使用 nvm 管理 Node.js 版本
 */

const { execSync } = require('child_process');
const path = require('path');

console.log('🔄 正在切换 Node.js 版本...\n');

// 获取脚本所在目录（根目录）
const rootDir = __dirname;
const targetDir = path.join(rootDir, 'apps', 'hrs-web');

try {
  // 检查当前 Node.js 版本
  const currentVersion = execSync('node --version', { encoding: 'utf-8' }).trim();
  console.log(`当前 Node.js 版本: ${currentVersion}`);

  // 检查是否安装了 nvm
  const nvmDir = process.env.NVM_DIR || `${process.env.HOME}/.nvm`;
  console.log(`NVM 目录: ${nvmDir}\n`);

  // 使用 nvm 切换到 v20
  console.log('📦 尝试切换到 Node.js v20...');
  
  // 执行 nvm 命令并切换到 apps/hrs-web 目录
  const nvmCommand = `
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    nvm use 20
    cd "${targetDir}"
    node --version
  `;

  const output = execSync(nvmCommand, { 
    encoding: 'utf-8',
    shell: '/bin/bash'
  });

  // 提取最后一行作为版本号
  const lines = output.trim().split('\n');
  const newVersion = lines[lines.length - 1].trim();

  console.log(`✅ 已切换到 Node.js ${newVersion}`);
  console.log(`📂 当前目录: apps/hrs-web\n`);

  // 验证版本
  const majorVersion = parseInt(newVersion.replace('v', '').split('.')[0]);
  if (majorVersion >= 20) {
    console.log('✅ 版本检查通过: Node.js v20+');
    console.log('\n💡 提示: 此切换仅在当前 shell 会话中有效。');
    console.log('   如需永久切换，请运行: nvm alias default 20');
    process.exit(0);
  } else {
    console.error('❌ 版本切换失败，当前版本仍低于 v20');
    process.exit(1);
  }

} catch (error) {
  console.error('❌ 切换失败:', error.message);
  console.error('\n💡 可能的解决方案:');
  console.error('   1. 确保已安装 nvm: https://github.com/nvm-sh/nvm');
  console.error('   2. 安装 Node.js v20: nvm install 20');
  console.error('   3. 检查 ~/.nvm/nvm.sh 文件是否存在');
  process.exit(1);
}
