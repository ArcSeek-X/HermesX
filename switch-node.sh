#!/bin/bash

# 切换 Node.js 版本到 v20+
# 使用 nvm 管理 Node.js 版本

echo "🔄 正在切换 Node.js 版本..."
echo ""

# 获取脚本所在目录（根目录）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TARGET_DIR="$SCRIPT_DIR/apps/hrs-web"

# 检查当前 Node.js 版本
CURRENT_VERSION=$(node --version 2>/dev/null || echo "未安装")
echo "当前 Node.js 版本: $CURRENT_VERSION"

# 检查是否安装了 nvm
NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
echo "NVM 目录: $NVM_DIR"
echo ""

# 加载 nvm
if [ -s "$NVM_DIR/nvm.sh" ]; then
    \. "$NVM_DIR/nvm.sh"
else
    echo "❌ 错误: 未找到 nvm"
    echo ""
    echo "💡 解决方案:"
    echo "   1. 安装 nvm: https://github.com/nvm-sh/nvm"
    echo "   2. 或手动切换: nvm use 20"
    exit 1
fi

# 切换到 Node.js v20
echo "📦 尝试切换到 Node.js v20..."
nvm use 20

if [ $? -ne 0 ]; then
    echo "❌ 切换失败"
    echo ""
    echo "💡 可能的解决方案:"
    echo "   1. 安装 Node.js v20: nvm install 20"
    echo "   2. 检查已安装版本: nvm list"
    exit 1
fi

# 切换到目标目录
echo ""
echo "📂 切换到目录: $TARGET_DIR"
cd "$TARGET_DIR"

# 验证版本
NEW_VERSION=$(node --version)
MAJOR_VERSION=$(echo "$NEW_VERSION" | sed 's/v//' | cut -d. -f1)

echo ""
if [ "$MAJOR_VERSION" -ge 20 ]; then
    echo "✅ 已切换到 Node.js $NEW_VERSION"
    echo "✅ 当前目录: $(pwd)"
    echo ""
    echo "💡 提示:"
    echo "   - 此切换在当前 shell 会话中有效"
    echo "   - 如需永久切换默认版本: nvm alias default 20"
    echo "   - 现在可以运行: npm run dev"
else
    echo "❌ 版本检查失败，当前版本: $NEW_VERSION"
    exit 1
fi
