# Generate Walkthrough Test Scripts (gen-wt)

为「前端功能页面」批量生成**前后端走查脚本**的脚手架 skill。每开发一个新功能模块，
按本规范生成一对脚本，即可被 `scripts/test_wt/test_wt.sh` 主流程自动发现、编排、跑测并产出报告。

**Repository**: HermesX（apps/dsa-web 前端 + 后端 api/）

## 触发条件

当用户满足以下任一情形时启用本 skill：
- 新增 / 改动了一个前端功能页面（路由页），需要配套走查脚本
- 明确要求「为某路由生成前后端测试走查脚本」
- 提到 sector-analysis / kline 类走查脚本需要复制到其他模块

## 输入信息（生成前必须收集）

1. **路由名**（用于文件夹与文件命名）：如 `kline`、`sector-analysis`、`xxx`
   - 命名规则：与页面路由 path 的最后一段一致，全小写、连字符分隔；**禁止首字母大写**
2. **核心页面代码文件**：`apps/dsa-web/src/pages/<Page>.tsx`
3. **前端 API 调用层**：页面 import 的 api 模块（如 `src/api/sectorData.ts`）——用于确认前端实际请求的接口与参数
4. **后端接口端点**：对应 `api/v1/endpoints/<x>.py` 的 router 定义——用于确认真实路由、Query 参数、返回 Schema
5. （可选）页面涉及的接口域名 / 监听端口约定

## 输出产物（严格契约）

在 `apps/dsa-web/scripts/test_wt/<route>/` 下生成**两个文件**：

| 文件 | 类型 | 作用 |
| ---- | ---- | ---- |
| `test_wt_<route>_frontend.sh` | Bash | 前端走查：接口契约 + 组件渲染(vitest) + 真实页面走查 + ESLint + tsc；**人工 UI 走查清单内联在本脚本步骤 4（带 `### 人工UI走查清单` 标记区间），由开发者基于页面实际代码/交互/边界填写** |
| `test_wt_<route>_backend.py` | Python | 后端集成测试：真实调用 FastAPI 接口，校验返回结构与字段契约 |

> 人工 UI 走查清单**不生成独立模板文件**。它必须基于功能页面真实内容（代码、注释、交互、边界）手写在 `frontend.sh` 步骤 4 的标记区间内，供主脚本报告"五、人工 UI 走查清单"章节读取；缺失该区间时主脚本回退通用兜底清单。

**主脚本自动发现机制**（无需改 `test_wt.sh`）：
- 主脚本 `find "$WT_ROOT" -mindepth 1 -maxdepth 1 -type d` 列出 `scripts/test_wt/` 下每个子目录为一个模块
- 对每个模块目录，匹配 `*.py`（后端）与 `*.sh`（前端）分别执行
- 因此**只要目录名与文件名符合上述规则，新模块即被自动纳入**

## 后端脚本契约（test_wt_<route>_backend.py）

- **运行位置**：仓库根目录（脚本内部 `sys.path` 上溯定位 `server.create_app`）
- **必须真实调用**：`from server import create_app` + `TestClient(app)`，遍历参数组合断言
- **输出格式**（供主脚本 `grep ^\[RESULT\]` 解析）：
  - 每个用例：`[PASS] <名称> <明细>` 或 `[FAIL] <名称> <明细>`
  - 结尾汇总：`[SUMMARY] 通过 X / 失败 Y / 共 Z`
  - 最终结果：`[RESULT] PASS` 或 `[RESULT] FAIL`
  - 失败逐条：`[FAIL] <原因>`（主脚本提取为问题清单）
- **退出码**：`0`=通过/良性 SKIP，`1`=失败，`2`=环境/依赖未就绪（依赖缺失时 `sys.exit(2)` 并输出 `[RESULT] SKIP`）
- **依赖缺失降级**：`try: from fastapi.testclient import TestClient; from server import create_app` 失败时 `sys.exit(2)`
- **字段契约校验**：对返回 JSON 校验类型（数值/数组/必填字段），不止断言 200

## 前端脚本契约（test_wt_<route>_frontend.sh）

- **运行位置**：`cd apps/dsa-web`（脚本内部 `cd "$(dirname "$0")/../../.."` 自适应）
- **接收参数**：`$1="lint"` 时开启 ESLint（由主脚本 `--lint` 透传）；否则跳过 lint
- **退出码**：`0`=通过(含良性 SKIP)，`1`=失败，`2`=环境/依赖未就绪
- **步骤**（参考 kline / sector-analysis 实现）：
  1. 环境预检：页面文件、API 层文件存在性
  2. 写内联 vitest 测试文件 `__<route>_walkthrough.test.tsx`（**结束必须 `rm -f` 清理**），mock `apiClient` 验证：
     - 前端正确拼装请求（URL / Query 参数）
     - 返回结构解析正确（字段类型 / 数组长度）
     - 页面组件 `render` 挂载无崩溃、关键结构出现
  3. 真实页面走查：读 `.$ROUTE-walkthrough-port` 端口文件，`curl http://localhost:<port>/<route>` 校验可访问；文件缺失则 `mark_skip`（非阻断）
  4. ESLint（`--lint` 时）+ `npx tsc --noEmit`
  5. 内联人工走查清单（主题/涨跌色/交互/边界，不阻断）
- **颜色工具**：`green`/`red`/`cyan`；`mark_pass`/`mark_fail`/`mark_skip`/`mark_unavailable`
- **npm 缺失**：`check_cmd npm` 为 false 时 `mark_unavailable` 并 `exit 2`

## 生成步骤（SOP）

1. 读页面 `.tsx`：提取路由 path、调用了哪些 api 函数、渲染了哪些区块（treemap/列表/卡片/图表）
2. 读前端 api 层：确认每个 api 函数对应的 `apiClient.get` 路径与参数
3. 读后端 router：确认真实端点、Query 参数、返回 Schema（用于后端断言）
4. 用 `scaffold_wt.sh <route>` 生成骨架（占位符 `__ROUTE__` 已替换）
5. 在后端 `.py` 中按接口逐个补充 `client.get(...)` + 字段断言
6. 在前端 `.sh` 内联测试里补充 api 契约用例 + 组件渲染断言
7. 基于功能页面真实内容（代码 / 注释 / 交互 / 边界），在 `frontend.sh` 步骤 4 的 `### 人工UI走查清单` 标记区间内逐项手写人工走查清单；该区间内容会被主脚本报告"五、人工 UI 走查清单"章节读取（缺失则回退通用兜底清单）
8. 验证：
   ```bash
   cd apps/dsa-web/scripts/test_wt && bash test_wt.sh --list        # 确认新模块被识别
   bash test_wt.sh <route>            # 跑测（依赖齐备时产生真实结果）
   bash test_wt.sh <route> --lint     # 带 ESLint
   ```
9. 真实联网端到端（可选）：装依赖后运行，检查报告产物 `.test_record/test_wt_report_<TS>/`

## 参考范例（已存在，可直接借鉴）

- `scripts/test_wt/kline/`：完整范例（K 线图页面）
- `scripts/test_wt/sector-analysis/`：完整范例（板块分析页面，覆盖 treemap / 指数 / 云图多周期）

## 命名与治理

- 文件夹 / 文件名一律小写 + 连字符，与页面路由一致
- 报告文件名：`test_wt_<route>_report_<TS>.md`（整体报告：`test_wt_report_<TS>.md`），由主脚本生成
- 本 skill 是脚本生成器，真源约定见仓库根 `AGENTS.md`；如需多 agent 兼容，按 AGENTS.md 单一真源原则镜像，勿手工维护多份同义内容

## 注意事项

- 主脚本 `WT_ROOT` 下若有 `__template__` 等空目录会被列为空模块（存量问题，忽略即可）
- 真实接口调用需要后端依赖（`pip install -r requirements.txt`）与前端依赖（`npm ci`）
- 环境未就绪时脚本应优雅降级为 `SKIP/exit 2`，不应因缺依赖而直接失败导致主流程中断
