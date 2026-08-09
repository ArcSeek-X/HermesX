#!/bin/bash

# ===================================
# 股票智能分析系统 - 统一启动脚本
# ===================================
#
# 功能：一键启动前后端开发服务
#   - 后端：FastAPI (uvicorn) 运行在 8000 端口
#   - 前端：Vite 开发服务器运行在 5173 端口
#
# 前置条件：
#   - Python 3.11+（用于后端，通过 pyenv 切换 .python-version）
#   - Node.js v20+（用于前端，通过 nvm 切换）
#   - 已安装项目依赖（pip install -r requirements.txt && npm ci）
#
# 使用方式：
#   ./start.sh              # 同时启动前后端
#   ./start.sh backend      # 仅启动后端
#   ./start.sh frontend     # 仅启动前端
#
# ===================================

# 获取脚本所在目录（项目根目录）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# ----------------------------------
# 颜色定义（终端输出美化）
# ----------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 恢复默认颜色

# ----------------------------------
# 打印带颜色的提示信息
# ----------------------------------
info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ----------------------------------
# 加载 pyenv（若已安装）
# 返回 0 表示 pyenv 可用，1 表示未找到
# ----------------------------------
load_pyenv() {
    # 已初始化则跳过
    if command -v pyenv &> /dev/null; then
        return 0
    fi
    # 常见安装位置：brew 安装与 git 安装
    local pyenv_root="${PYENV_ROOT:-$HOME/.pyenv}"
    if [ -s "$pyenv_root/bin/pyenv" ]; then
        export PYENV_ROOT="$pyenv_root"
        export PATH="$PYENV_ROOT/bin:$PATH"
        eval "$(pyenv init -)"
        return 0
    fi
    return 1
}

# ----------------------------------
# 检查 Python 版本（后端依赖 3.11+）
# 优先使用 pyenv 切换到 .python-version 指定版本
# ----------------------------------
check_python() {
    info "检查 Python 版本..."

    # 优先尝试 pyenv：加载后切换到项目 .python-version 指定版本
    if load_pyenv; then
        if [ -f "$SCRIPT_DIR/.python-version" ]; then
            local req_version
            req_version="$(tr -d '[:space:]' < "$SCRIPT_DIR/.python-version")"
            info "使用 pyenv 切换到 $req_version (来自 .python-version)..."
            # 若本地未安装该版本，提示安装（不自动安装，避免耗时/权限问题）
            if ! pyenv versions --bare 2>/dev/null | grep -qx "$req_version"; then
                warn "pyenv 未安装 $req_version，尝试安装（耗时较长，可手动执行: pyenv install $req_version）"
                pyenv install "$req_version" || {
                    err "pyenv 安装 $req_version 失败，请手动安装后重试"
                    exit 1
                }
            fi
            pyenv local "$req_version" || {
                err "pyenv 切换到 $req_version 失败"
                exit 1
            }
            ok "pyenv 已切换至 $(python --version 2>&1)"
        else
            # 无 .python-version 时，使用 pyenv 默认的 3.11+
            local cur
            cur="$(python --version 2>&1 | awk '{print $2}')"
            local major minor
            major="$(echo "$cur" | cut -d. -f1)"
            minor="$(echo "$cur" | cut -d. -f2)"
            if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 11 ]); then
                err "Python 版本过低: $cur，需要 3.11+"
                exit 1
            fi
        fi
    elif ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
        err "未找到 python/python3，请先安装 Python 3.11+（建议通过 pyenv）"
        exit 1
    fi

    # 统一使用 python 命令（pyenv 切换后即为目标版本）
    local PYTHON_BIN="${PYTHON_BIN:-python}"
    if ! command -v "$PYTHON_BIN" &> /dev/null; then
        PYTHON_BIN="python3"
    fi

    PYTHON_VERSION=$("$PYTHON_BIN" --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
        err "Python 版本过低: $PYTHON_VERSION，需要 3.11+"
        exit 1
    fi
    ok "Python $PYTHON_VERSION"
}

# ----------------------------------
# 检查 Node.js 版本（前端依赖 v20+）
# 优先使用 nvm 切换到 v20
# ----------------------------------
check_node() {
    info "检查 Node.js 版本..."
    NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
    if [ -s "$NVM_DIR/nvm.sh" ]; then
        \. "$NVM_DIR/nvm.sh"
        # 尝试切换到 v20
        nvm use 20 > /dev/null 2>&1
    fi
    if ! command -v node &> /dev/null; then
        err "未找到 node，请先安装 Node.js v20+"
        exit 1
    fi
    NODE_VERSION=$(node --version)
    NODE_MAJOR=$(echo "$NODE_VERSION" | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_MAJOR" -lt 20 ]; then
        err "Node.js 版本过低: $NODE_VERSION，需要 v20+"
        warn "如果已安装 nvm，请执行: nvm use 20"
        exit 1
    fi
    ok "Node.js $NODE_VERSION"
}

# ----------------------------------
# 检查后端依赖是否已安装
# ----------------------------------
check_backend_deps() {
    info "检查后端依赖..."
    local PYTHON_BIN="${PYTHON_BIN:-python}"
    if ! command -v "$PYTHON_BIN" &> /dev/null; then
        PYTHON_BIN="python3"
    fi
    if [ ! -d ".venv" ] && ! "$PYTHON_BIN" -c "import fastapi" 2>/dev/null; then
        warn "后端依赖未安装，执行: pip install -r requirements.txt"
        "$PYTHON_BIN" -m pip install -r requirements.txt
    else
        ok "后端依赖已就绪"
    fi
}

# ----------------------------------
# 检查前端依赖是否已安装
# ----------------------------------
check_frontend_deps() {
    info "检查前端依赖..."
    if [ ! -d "apps/hrs-web/node_modules" ]; then
        warn "前端依赖未安装，执行: npm ci"
        cd "$SCRIPT_DIR/apps/hrs-web" && npm ci
        cd "$SCRIPT_DIR"
    else
        ok "前端依赖已就绪"
    fi
}

# ----------------------------------
# 启动后端服务（FastAPI / uvicorn）
# ----------------------------------
start_backend() {
    echo ""
    info "启动后端服务 (port: 8000)..."
    echo "   访问地址: http://localhost:8000"
    echo "   API 文档: http://localhost:8000/docs"
    echo ""
    # --reload: 代码修改后自动重启
    # --host 0.0.0.0: 允许外部访问
    # --port 8000: 监听 8000 端口
    # 使用 python -m uvicorn 确保走 pyenv 切换后的解释器环境
    local PYTHON_BIN="${PYTHON_BIN:-python}"
    if ! command -v "$PYTHON_BIN" &> /dev/null; then
        PYTHON_BIN="python3"
    fi
    "$PYTHON_BIN" -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
}

# ----------------------------------
# 启动前端服务（Vite 开发服务器）
# ----------------------------------
start_frontend() {
    echo ""
    info "启动前端服务 (port: 5173)..."
    echo "   访问地址: http://localhost:5173"
    echo ""
    cd "$SCRIPT_DIR/apps/hrs-web"
    # Vite 开发服务器，支持热更新（HMR）
    # 已配置代理，/api 请求自动转发到后端 8000 端口
    npm run dev
}

# ----------------------------------
# 主流程
# ----------------------------------
main() {
    echo ""
    echo "=========================================="
    echo "  股票智能分析系统 - 开发环境启动"
    echo "=========================================="
    echo ""

    # 根据参数决定启动模式
    MODE="${1:-all}"  # 默认同时启动前后端

    case "$MODE" in
        backend)
            info "仅启动后端"
            check_python
            check_backend_deps
            start_backend
            ;;
        frontend)
            info "仅启动前端"
            check_node
            check_frontend_deps
            start_frontend
            ;;
        all)
            info "同时启动前后端"
            check_python
            check_node
            check_backend_deps
            check_frontend_deps

            echo ""
            info "启动后端服务（后台运行）..."
            # 后台启动后端，日志输出到 logs/dev_backend.log
            mkdir -p "$SCRIPT_DIR/logs"
            local PYTHON_BIN="${PYTHON_BIN:-python}"
            if ! command -v "$PYTHON_BIN" &> /dev/null; then
                PYTHON_BIN="python3"
            fi
            "$PYTHON_BIN" -m uvicorn server:app --reload --host 0.0.0.0 --port 8000 \
                > "$SCRIPT_DIR/logs/dev_backend.log" 2>&1 &
            BACKEND_PID=$!
            ok "后端已启动 (PID: $BACKEND_PID)"

            # 等待后端就绪（最多 10 秒）
            info "等待后端就绪..."
            for i in $(seq 1 20); do
                if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
                    ok "后端已就绪"
                    break
                fi
                sleep 0.5
            done

            echo ""
            info "启动前端服务..."
            echo "   前端: http://localhost:5173"
            echo "   后端: http://localhost:8000/docs"
            echo ""
            cd "$SCRIPT_DIR/apps/hrs-web"
            npm run dev
            ;;
        *)
            err "未知参数: $1"
            echo ""
            echo "用法: $0 [backend|frontend|all]"
            echo "  backend   - 仅启动后端"
            echo "  frontend  - 仅启动前端"
            echo "  all       - 同时启动前后端（默认）"
            exit 1
            ;;
    esac
}

# 执行主流程
main "$@"
