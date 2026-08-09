# 声明 Dockerfile 语法版本，启用 1.7 的新特性（如更稳定的 heredoc / mount 行为）
# syntax=docker/dockerfile:1.7

# ===================================
# A股自选股智能分析系统（HermesX）- Docker 镜像
# ===================================
# 构建策略：多阶段构建（multi-stage build）
#   - 阶段一（web-builder）：用 Node 构建前端静态产物
#   - 阶段二（运行时）：用 Python 镜像承载后端 + 拷贝前端产物
# 这样最终镜像不含 Node 工具链，体积更小、攻击面更窄。

# ---------- 阶段一：前端构建 ----------
FROM node:20-slim AS web-builder

# 进入前端工程目录（与仓库目录结构保持一致，便于 COPY 相对路径）
WORKDIR /app/apps/hrs-web
# 前端版本号与短提交哈希，由 CI（docker-publish.yml）通过 --build-arg 传入，
# 注入到前端打包产物里用于「关于/版本」展示；缺省给占位值，保证本地也能构建。
ARG HRS_WEB_VERSION=0.0.0
ARG HRS_WEB_REVISION=unknown

# 先只拷贝依赖清单，利用 Docker 层缓存：依赖不变时无需重新 npm install
COPY apps/hrs-web/package.json apps/hrs-web/package-lock.json ./
# 用缓存挂载加速 npm，避免每次重新下载整个 node_modules
RUN --mount=type=cache,target=/root/.npm npm ci

# 拷贝全部前端源码并执行生产构建，产物默认输出到 build/ 目录
COPY apps/hrs-web/ ./
RUN HRS_WEB_VERSION="${HRS_WEB_VERSION}" HRS_WEB_REVISION="${HRS_WEB_REVISION}" npm run build

# ---------- 阶段二：后端运行时 ----------
# 钉死 bookworm：wkhtmltopdf 已从 Debian testing（2025 起）移除，
# 必须固定在仍带该包的 bookworm，否则 Markdown 转图片能力会断。
FROM python:3.11-slim-bookworm

# 设置工作目录
WORKDIR /app

# 设置时区为上海（A股/港股交易时间相关，避免日志与时间戳错乱）
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装系统依赖（--no-install-recommends 精简体积）
#   gcc        : 部分 Python 包需要编译 C 扩展
#   curl       : 健康检查 / 容器内调试
#   git        : 某些数据源或脚本需要
#   gosu       : 以非 root 身份安全执行命令（entrypoint 里降权用）
#   wkhtmltopdf: 含 wkhtmltoimage，用于把 Markdown 报告渲染成图片（Issue #289）
#   fontconfig / libjpeg62-turbo / libxrender1 / libxext6: 渲染图片所需字体与图形库
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    git \
    gosu \
    wkhtmltopdf \
    fontconfig \
    libjpeg62-turbo \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户（固定 UID/GID 1000），运行应用不用 root，降低安全风险；
# 后续所有可写目录都授权给该用户。注意：该用户名为： hrs。
RUN groupadd -g 1000 hrs && \
    useradd -u 1000 -g hrs -m hrs

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（用缓存挂载加速 pip 下载）
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

# 复制应用代码（按模块分目录 COPY，便于利用层缓存：某模块改动只重建对应层）
COPY *.py ./
COPY api/ ./api/
COPY data_provider/ ./data_provider/
COPY bot/ ./bot/
COPY src/ ./src/
COPY strategies/ ./strategies/
# 从前端构建阶段拷贝静态产物到 /app/static，供后端直接托管
COPY --from=web-builder /app/static ./static/
# 拷贝容器启动脚本并放到标准 PATH 下
COPY docker/entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# 冒烟校验全局依赖在镜像内确实可用，且不残留 SDK 日志：
# 在临时 HOME 下导入 alphasift.dsa_adapter 与 futu，验证富途 SDK 链路可加载；
# 校验完成后删除临时 HOME，避免把 SDK 的日志/缓存写进最终镜像层。
RUN mkdir -p /tmp/futu-sdk-smoke-home && \
    HOME=/tmp/futu-sdk-smoke-home python -c "import alphasift.dsa_adapter; import futu" && \
    rm -rf /tmp/futu-sdk-smoke-home

# 确保数据目录存在并授权给 non-root 用户；
# 同时给 entrypoint 脚本加可执行权限（COPY 后默认可能无 x 权限）。
RUN mkdir -p /app/data /app/logs /app/reports && \
    chown -R hrs:hrs /app && \
    chmod +x /usr/local/bin/docker-entrypoint.sh

# efinance 将搜索缓存（search-cache.json）写入自身安装包内的 data 目录，
# 该目录默认归 root 所有；容器以非 root 用户 hrs 运行时写入会 PermissionError，
# 导致 efinance 数据源每次抓取 A 股数据都失败并降级。预置目录属主给 hrs 修复此问题。
# 动态解析路径，避免写死 Python 版本目录（如 site-packages/python3.11/...）。
RUN EF_DATA_DIR="$(python -c 'import efinance, pathlib; print(pathlib.Path(efinance.__file__).parent / "data")')" && \
    mkdir -p "$EF_DATA_DIR" && \
    chown -R hrs:hrs "$EF_DATA_DIR"

# 设置环境变量默认值（均可在 docker run / compose 时覆盖）
ENV PYTHONUNBUFFERED=1                       # Python 日志实时输出，不缓冲，便于看容器日志
ENV LOG_DIR=/app/logs                        # 应用日志目录
ENV DATABASE_PATH=/app/data/stock_analysis.db# SQLite 数据库路径（持久化卷内）
# Web/API service 监听配置
ENV WEBUI_HOST=0.0.0.0                       # 监听所有网卡，便于容器外访问
ENV API_PORT=8000                           # API/Web 服务端口

# 暴露 API 端口（仅文档性声明，真正映射由 run/compose 的 -p 决定）
EXPOSE 8000

# 数据卷（持久化数据）：data 库、logs、reports 挂到命名卷/挂载点，镜像重建不丢数据
VOLUME ["/app/data", "/app/logs", "/app/reports"]

# 健康检查（FastAPI 模式）：每 30s 探一次 /api/health 或 /health，
# 启动宽限 10s，连续 3 次失败才标记不健康；末尾 python 兜底返回 0，
# 避免非 API 运行模式下健康检查误杀容器。
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || curl -f http://localhost:8000/health \
    || python -c "import sys; sys.exit(0)"

# 启动入口先修复 bind mount 目录权限，再降权为 hrs 执行应用；
# 文档化 docker-compose exec 命令需显式使用 -u hrs，避免手动进程写入 root-owned 文件。
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# 默认命令（可被 docker run 末尾参数覆盖）：以调度模式启动分析主流程
CMD ["python", "main.py", "--schedule"]
