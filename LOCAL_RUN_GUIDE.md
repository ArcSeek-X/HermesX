# 本地运行指南

本文档整理了在本地把本项目的**后端**与**前端**跑起来所需的全部命令。

---

## 目录

1. [环境要求](#1-环境要求)
2. [初始配置](#2-初始配置)
3. [后端启动命令](#3-后端启动命令)
4. [前端启动命令](#4-前端启动命令)
5. [前后端联调（开发模式）](#5-前后端联调开发模式)
6. [生产模式（前端打包 + 后端托管）](#6-生产模式前端打包--后端托管)
7. [桌面端启动](#7-桌面端启动)
8. [Docker 启动](#8-docker-启动)
9. [常用 CLI 参数速查](#9-常用-cli-参数速查)
10. [常见问题](#10-常见问题)

---

## 1. 环境要求

| 依赖 | 版本要求 | 说明 |
|------|---------|------|
| Python | ≥ 3.10（推荐 3.11/3.12） | Docker 镜像使用 3.11-bookworm |
| Node.js | ≥ 20.19.0 且 < 27 | 前端构建要求；`start-frontend.sh` 会自动切换 nvm v20 |
| npm | ≥ 10 | 随 Node.js 一起安装 |
| Git | 任意版本 | 前端构建时会读取 git 信息生成版本号 |

---

## 2. 初始配置

### 2.1 克隆代码后，复制环境变量模板

```bash
cp .env.example .env
```

然后编辑 `.env`，至少配置以下项：

```ini
# 必填：自选股列表
STOCK_LIST=600519,300750,002594

# 必填（至少填一个）：AI 模型 API Key
GEMINI_API_KEY=your_key_here          # Gemini（有免费额度）
# DEEPSEEK_API_KEY=your_key_here       # DeepSeek（性价比高）
# ANSPIRE_API_KEYS=your_key_here       # Anspire（一站式模型+搜索）

# 可选：搜索引擎 Key（用于获取股票新闻，不配也能跑但新闻为空）
TAVILY_API_KEYS=
```

> 完整配置项说明见 `.env.example` 中的注释，或 `docs/` 目录下的专题文档。

### 2.2 安装后端依赖

```bash
# 建议先创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2.3 安装前端依赖

```bash
cd apps/dsa-web
npm ci                           # 如果没有 package-lock.json，用 npm install
cd ../..
```

---

## 3. 后端启动命令

后端基于 **FastAPI + Uvicorn**，有以下几种启动方式：

### 方式一：仅启动 Web/API 服务（推荐用于日常开发）

```bash
python main.py --serve-only
```

- 默认监听 `http://127.0.0.1:8000`
- 不执行自动分析，通过 API 接口手动触发
- API 文档：`http://127.0.0.1:8000/docs`

### 方式二：启动 Web 服务 + 自动执行一次分析

```bash
python main.py --serve
```

### 方式三：直接用 uvicorn（支持热重载）

```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### 方式四：用 webui.py 快捷启动

```bash
python webui.py
# 等效于 python main.py --webui-only
# 可通过环境变量覆盖地址：
WEBUI_HOST=0.0.0.0 WEBUI_PORT=8000 python webui.py
```

### 自定义监听地址和端口

```bash
python main.py --serve-only --host 0.0.0.0 --port 9000
```

或通过 `.env` 配置：

```ini
WEBUI_HOST=0.0.0.0
WEBUI_PORT=8000
```

### 仅运行分析（不启动 Web 服务）

```bash
python main.py                    # 正常分析
python main.py --debug            # 调试模式（详细日志）
python main.py --dry-run          # 仅获取数据，不调用 AI
python main.py --stocks 600519,300750   # 指定股票
python main.py --market-review    # 仅运行大盘复盘
python main.py --schedule         # 定时任务模式
```

---

## 4. 前端启动命令

前端位于 `apps/dsa-web/`，基于 **React 19 + Vite 7 + TypeScript + Tailwind CSS 4**。

### 4.1 开发服务器（热更新）

```bash
cd apps/dsa-web
npm run dev
```

- 默认端口：`http://localhost:5173`
- 已配置代理：`/api` 请求自动转发到 `http://127.0.0.1:8000`（后端）
- 因此**需要同时启动后端**才能正常使用

也可以用项目根目录的快捷脚本（自动切换 Node v20）：

```bash
./start-frontend.sh
```

### 4.2 生产构建

```bash
cd apps/dsa-web
npm run build
```

构建产物输出到项目根目录的 `static/` 文件夹，后端启动时会自动托管这些静态文件。

### 4.3 其他前端命令

```bash
cd apps/dsa-web
npm run lint          # ESLint 代码检查
npm run test          # Vitest 单元测试
npm run preview       # 本地预览生产构建
```

---

## 5. 前后端联调（开发模式）

日常开发推荐**同时开两个终端**：

**终端 1 — 启动后端（端口 8000）：**

```bash
# 确保在项目根目录，且已激活虚拟环境
python main.py --serve-only
```

**终端 2 — 启动前端开发服务器（端口 5173）：**

```bash
cd apps/dsa-web
npm run dev
```

然后浏览器访问 `http://localhost:5173` 即可。

> 前端 Vite 配置中已将 `/api` 代理到 `http://127.0.0.1:8000`，所以前端页面发出的 API 请求会自动转发到后端，无需额外配置跨域。

---

## 6. 生产模式（前端打包 + 后端托管）

生产环境下，前端打包后由后端 FastAPI 直接托管静态文件，只需一个服务：

```bash
# 第一步：构建前端
cd apps/dsa-web
npm run build
cd ../..

# 第二步：启动后端（会自动检测并托管 static/ 目录下的前端文件）
python main.py --serve-only
# 或
python main.py --serve
```

访问 `http://127.0.0.1:8000` 即可看到前端页面。

> `main.py` 启动时会调用 `prepare_webui_frontend_assets()` 检查前端资源是否就绪。如果 `static/` 目录不存在或为空，会打印警告但不会阻止服务启动（Web 页面可能不可用，API 仍正常）。

---

## 7. 桌面端启动

桌面端基于 **Electron**，位于 `apps/dsa-desktop/`。

```bash
cd apps/dsa-desktop
npm install
npm run dev          # 启动 Electron 桌面应用
npm run build        # 打包桌面应用（Windows NSIS / macOS DMG）
```

> 桌面端打包时需要先构建 Web 前端和后端，详见 `docs/desktop-package.md`。

---

## 8. Docker 启动

项目提供了 Dockerfile 和 docker-compose.yml，可以一键启动：

```bash
# 定时任务模式（默认）
docker-compose -f ./docker/docker-compose.yml up -d

# 仅 FastAPI 服务模式
docker-compose -f ./docker/docker-compose.yml up -d server

# 同时启动分析器和 API 服务
docker-compose -f ./docker/docker-compose.yml up -d analyzer server
```

Docker 镜像为多阶段构建：
1. **web-builder 阶段**：用 Node 20 构建前端，输出到 `static/`
2. **运行阶段**：基于 Python 3.11-slim-bookworm，安装后端依赖，复制前端产物

默认端口映射 `8000:8000`，数据卷挂载 `data/`、`logs/`、`reports/`。

---

## 9. 常用 CLI 参数速查

| 参数 | 说明 |
|------|------|
| `--serve` | 启动 FastAPI 服务 **并** 执行一次分析 |
| `--serve-only` | 仅启动 FastAPI 服务，不自动分析 |
| `--webui-only` | 同 `--serve-only`（兼容旧参数） |
| `--host <addr>` | 指定监听地址（默认 `127.0.0.1` 或 `WEBUI_HOST`） |
| `--port <port>` | 指定监听端口（默认 `8000` 或 `WEBUI_PORT`） |
| `--debug` | 调试模式，输出 DEBUG 级日志 |
| `--dry-run` | 仅获取数据，不调用 AI 分析 |
| `--stocks <code1,code2>` | 指定分析的股票代码（覆盖 `.env` 中的 `STOCK_LIST`） |
| `--market-review` | 仅运行大盘复盘 |
| `--no-market-review` | 跳过大盘复盘 |
| `--schedule` | 启用定时任务模式 |
| `--no-run-immediately` | 定时模式启动时不立即执行一次 |
| `--force-run` | 跳过交易日检查，强制执行 |
| `--no-notify` | 不发送推送通知 |
| `--single-notify` | 单股推送模式（分析完一只立即推送） |
| `--check-notify` | 仅检查通知渠道配置，不发送 |
| `--workers <n>` | 并发线程数 |
| `--portfolio futu` | 使用富途真实持仓覆盖股票列表 |
| `--backtest` | 运行回测 |
| `--no-context-snapshot` | 不保存分析上下文快照 |

---

## 10. 常见问题

### Q: 前端页面白屏 / API 请求 404？

确保后端已启动并监听在 `127.0.0.1:8000`。前端开发服务器（5173）通过 Vite 代理把 `/api` 转发到后端，后端没开就会 404。

### Q: 后端启动报 `ModuleNotFoundError`？

确保已激活虚拟环境并安装了依赖：

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Q: `npm run build` 报 Node 版本不兼容？

前端要求 Node ≥ 20.19.0。用 nvm 切换：

```bash
nvm install 20
nvm use 20
```

或直接运行项目自带的 `start-frontend.sh`，它会自动切换到 v20。

### Q: 如何修改后端监听端口？

三种方式任选：

```bash
# 1. 命令行参数
python main.py --serve-only --port 9000

# 2. 环境变量
WEBUI_PORT=9000 python main.py --serve-only

# 3. .env 文件
# WEBUI_PORT=9000
```

如果同时修改了后端端口，记得同步修改前端 Vite 代理目标（`apps/dsa-web/vite.config.ts` 中的 `server.proxy['/api'].target`）。

### Q: 生产模式下前端没显示？

确保已执行 `npm run build`，产物在项目根目录 `static/` 文件夹中。后端启动时会自动检查并托管。

### Q: 如何启用登录认证？

在 `.env` 中设置：

```ini
ADMIN_AUTH_ENABLED=true
```

首次访问时网页会引导设置密码。忘记密码可重置：

```bash
python -m src.auth reset_password
```
