# W7：认证 / Cookie / CORS 与性能启动基线

> 对应 `ARCHITECTURE_TARGET.md` §9.2-5：「对公网/桌面两种运行场景的认证、Cookie、CORS 与修改类请求防护，以及性能/启动时间的基线和验收阈值，须在相关切片开始前记录」。
> 取证时间：**2026-10-31**｜基线 HEAD：`fe7410bb`（工作树含 W1–W9 未提交改动）｜实测环境：macOS 14 (darwin)、Python 3.11.15（`.venv`）
> 守卫用例：`tests/test_security_baseline.py`（15 条）｜测量脚本：`scripts/measure_performance_baseline.py`

本文件只记录**可核对的事实与阈值**，不宣称「已安全」「性能不变」。凡未实测的项，在 §5 明确列为未覆盖。

---

## 1. 认证与会话（现状取证）

| 关注点 | 实现位置 | 当前语义 |
| --- | --- | --- |
| 开关 | `src/auth.py::is_auth_enabled` | 只读 `.env` 的 `ADMIN_AUTH_ENABLED`（`true/1/yes`），进程内缓存，配置变更后由 `refresh_auth_state()` 失效 |
| 会话令牌 | `src/auth.py::create_session` / `verify_session` | `nonce.ts.hmac_sha256` 三段式；签名 `hmac.compare_digest` 常数时间比较；`ts` 超龄即失效（`ADMIN_SESSION_MAX_AGE_HOURS`，默认 24h） |
| 会话密钥 | `src/auth.py::_load_session_secret` | `DATA_DIR/.session_secret`，32 字节随机；文件权限 `0600`；长度 ≠ 32 视为损坏并重建（重建失败返回 `None`，会话不可签发） |
| 口令存储 | `src/auth.py::set_password` / `_verify_password_hash` | `pbkdf2_hmac(sha256, 100_000)` + 32 字节随机盐；凭据文件 `0600`，经临时文件 `replace()` 原子写 |
| 登录限流 | `src/auth.py::check_rate_limit` / `get_client_ip` | 5 次失败 / 300s 窗口（进程内字典）；`TRUST_X_FORWARDED_FOR=true` 时取 `X-Forwarded-For` **最右值**，避免客户端伪造最左值轮换限流桶 |
| 中间件 | `api/middlewares/auth.py` | 始终注册；`is_auth_enabled()` 为真时，除白名单外 `/api/v1/*` 一律要求有效会话，缺失/失效返回 `401 {"error":"unauthorized"}` |

白名单实测为 8 条：`/api/v1/auth/login`、`/api/v1/auth/status`、`/api/health`、`/api/v1/health`、`/health`、`/docs`、`/redoc`、`/openapi.json`。前缀匹配不成立（`/api/v1/auth/login/extra` 不放行），避免「前缀白名单」式绕过。

## 2. Cookie 与 CORS（现状取证）

| 关注点 | 实现位置 | 当前语义 |
| --- | --- | --- |
| Cookie 标志 | `api/v1/endpoints/auth.py::_cookie_params` | `HttpOnly=True`、`SameSite=Lax`、`Path=/`、`Max-Age=hours*3600`（非法值回落 24h） |
| Secure 判定 | 同上 | **不是写死**：`TRUST_X_FORWARDED_FOR=true` 时看 `X-Forwarded-Proto`，否则看 `request.url.scheme`；本地桌面端走 HTTP 时仍可登录，公网 HTTPS 部署自动带 `Secure` |
| CORS 默认 | `api/app.py::create_app` | 默认 4 个本地开发源（`localhost/127.0.0.1:5173/3000`）+ `CORS_ORIGINS` 追加；`allow_credentials=True` |
| CORS 放开 | 同上 | `CORS_ALLOW_ALL=true` 时 `allow_origins=["*"]` 且 **强制 `allow_credentials=False`**（不出现「通配源 + 凭证」组合）；认证未开启时额外打 WARN 日志 |
| 修改类请求防护 | — | **无独立 CSRF token**。防护由三层叠加：`SameSite=Lax`（跨站 POST 不携带会话 Cookie）+ CORS 源白名单 + 认证中间件对 `/api/v1/*` 全方法生效 |

`allow_methods` / `allow_headers` 均为 `["*"]`，在「源已白名单 + 凭证受限」前提下不构成越权面，记录为已知宽松项而非缺陷。

## 3. 决策：`src/auth.py` 维持原位（D-06 落法 A）

- **原状态**：ADR-005 把「端口化（选项 B）」的**前置条件**设为「先补 §9.2-5 的认证/CORS 清单与性能基线」。本文件即该前置条件。
- **本次结论**：**维持落法 A，不做 `AuthPort` 端口化**。理由：
  1. `auth.py` 的外部依赖只有本地文件（`.env`、`.session_secret`、`.admin_password_hash`）与 `os.environ`，不存在「可替换驱动」——端口化只会得到一个单实现的空壳，违反 AGENTS.md「优先复用现有模块，不新增平行实现」；
  2. `api/` 直连 `src.auth` 已被架构守卫判定合法（守卫只禁 `api → src.storage/repositories/infrastructure/data_provider`）；
  3. 真实风险（签名强度、Cookie 标志、CORS 组合、限流桶）已由 `tests/test_security_baseline.py` 静态+行为双重锁定，端口化不降低这些风险。
- **重评触发条件**（满足任一才重新考虑选项 B）：引入多用户/OAuth 等第二种会话载体；会话需要跨进程或多实例共享；需要把 `api/auth` 与会话存储拆到不同部署单元。
- **回滚**：本决策无代码改动，无需回滚。

## 4. 性能基线（实测数值 + 验收阈值）

复现命令（离线、无网络、不触碰开发库）：

```bash
./.venv/bin/python scripts/measure_performance_baseline.py          # 人类可读
./.venv/bin/python scripts/measure_performance_baseline.py --json   # 机器可读
```

测量口径：`lifespan` 在隔离子进程内跑，`DATABASE_PATH` 指向临时目录、`HRS_RUNTIME_SCHEDULER_SUPPRESS_START=true` 抑制调度器；接口延迟走 `httpx.ASGITransport` 且**不进入 lifespan**，因此不写库、不触网。每次 5 次预热 + 40 次采样。

### 4.1 实测（3 次运行区间，本机）

| 指标 | 实测 | 说明 |
| --- | --- | --- |
| `import api.app`（冷子进程，含解释器启动） | min **1427–1450 ms**，median **1461–1480 ms** | 3 次采样逐次 1427/1440/1450 附近，单次最长 ~1990 ms（磁盘冷缓存） |
| 完整 lifespan 启动 | **4421–4547 ms** | 临时库建表 + 幂等迁移 + 全部 `configure_*` 装配 + 后台任务调度；退出时临时库 **32 张表**，与既有 schema 基线一致 |
| `create_app()`（进程内） | min **0.88–0.91 ms**，median **0.89–0.94 ms** | 当前 FastAPI 的 `include_router` 惰性，路由装配成本主要体现在首访而非工厂 |
| OpenAPI 首次生成（`/docs` 首访） | **637–658 ms** | paths 数 **153**（真实 API 面口径；`app.routes` 只反映顶层 11 条） |
| `GET /api/health` | p50 **0.61–0.74 ms**，p95 **0.91–0.94 ms** | 纯内存响应 |
| `GET /api/v1/health` | p50 **0.91–1.00 ms**，p95 **1.16–2.63 ms** | 纯内存响应 |
| `GET /api/v1/auth/status` | p50 **0.53–0.61 ms**，p95 **0.71–1.03 ms** | 只读配置/文件存在性 |

### 4.2 验收阈值（回归门）

阈值取实测值的 **2–3 倍**，目的是抓「数量级回归」而非微观抖动（本机与 CI 硬件差异、随机化 pytest 并发都会带来数倍噪声）：

| 指标 | 阈值 | 判据 |
| --- | --- | --- |
| `import api.app` median | ≤ **3000 ms** | 超过即说明 import 期引入了新的重依赖（如顶层 SDK 初始化） |
| lifespan 启动 | ≤ **10000 ms** | 超过 10s 视为启动路径新增阻塞 IO 或重复建表 |
| `create_app()` median | ≤ **50 ms** | 工厂不应再承担重活 |
| OpenAPI 首次生成 | ≤ **2000 ms** | 防止 schema 爆炸 |
| 健康/状态接口 p95 | ≤ **20 ms** | 纯内存接口不应出现 IO |

搜索解析预算（`tests/test_search_performance.py`，`benchmark` marker 已登记到 `setup.cfg`）：快路径 < **20 ms/次**、单字误写兜底 < **100 ms/次**、5000 候选项模糊匹配 < **200 ms/次**。

## 5. 守卫映射与未覆盖项

`tests/test_security_baseline.py`（15 条）逐条对应的不变量：

1. Cookie：`httponly/lax/secure(https)`、`secure(http)=False`、代理分支 `X-Forwarded-Proto`、`max_age` 非法值回落；
2. 密钥：32 字节 + `0600`、长度异常自动重建、令牌三段式往返、篡改签名失效、过期失效、`hmac.compare_digest` 静态断言；
3. 中间件：白名单精确匹配（含 `.../extra` 不放行）、无 Cookie 401、伪造 Cookie 401、有效 Cookie 放行、豁免路径放行、认证关闭时直通；
4. CORS：`*` 与凭证互斥、默认源不含 `*` 且带凭证；
5. 客户端 IP：信任代理时取最右值、不信任时忽略该头。

**未覆盖（刻意不在此切片处理）**：

- 无 CSRF token：依赖 `SameSite=Lax` + CORS 白名单；若未来出现跨站表单写入需求，须重新评估；
- 登录限流是**进程内**字典（多 worker 不共享），与 §9.2.1-4「单进程假设」一致，水平扩展时需另设方案；
- 未做渗透/扫描类验证，也未在真实反向代理（nginx/Cloudflare）后面验证 `X-Forwarded-Proto` 注入行为；
- 启动耗时只测「空库建表」路径，未测「大库（24.8 MB / 14762 行）升级」路径（该数据见 W1.4 的幂等实测，不在本文件）；
- 桌面端（Electron）打包产物的启动耗时未测，本文件的数字是后端进程口径。

## 6. 与 §9.2 状态的关系

本文件落地后，`ARCHITECTURE_TARGET.md` §9.2-5 的两个未满足项（认证/CORS 防护清单、性能与启动基线）均已有记录，故该条转「已决」，见 §9.2.1 新增行；`src/auth.py` 的落法仍为 A（ADR-005 已同步复核结论）。
