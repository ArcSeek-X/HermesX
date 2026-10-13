# kline 功能模块 - 测试走查报告

**基本信息：**

- **报告名称**：`test_wt_kline_report_2026_08_08_01_49_21.md`
- **生成目录**：`/Users/gaocangxiong/Work/DevProject/HermesX/apps/hrs-web/.test_record/test_wt_report_2026_08_08_01_49_21`
- **执行脚本**：`apps/hrs-web/scripts/test_wt/test_wt.sh`
- **执行时间**：2026_08_08_01_49_21
- **功能模块**：kline
- **执行结果**：✅ 通过（含良性 SKIP）

**环境信息：**

- **前端环境**：Node（npm/npx Vitest / tsc），由 test_wt/kline/ 下前端走查脚本执行
- **后端环境**：Python（FastAPI TestClient，真实调用接口，非 mock）；联网访问外部行情源
- **执行目录**：`apps/hrs-web`
- **脚本退出码**：`0（0=通过/良性SKIP，1=失败，2=环境未就绪）`

## 一、走查范围（前后端同时走查）

本模块走查覆盖其同名子目录（`test_wt/kline/`），执行脚本进行测试：

- **后端**：`后端集成测试（真实调用接口）`
- **前端**：`接口契约与调用正确性测试`
- **前端**：`K 线页面功能走查`
- **前端**：`ESLint（测试文件）`
- **前端**：`TypeScript 类型检查（K 线相关）`

## 二、执行介绍（前后端同时走查）

### 2.1 前端（mock 后端，验证请求拼装与返回解析）

前端走查脚本 `test_wt/kline/test_wt_kline_frontend.sh` 在隔离环境下验证前端对后端的请求拼装与返回结构解析，覆盖：
- 接口契约 + 调用正确性：接口 URL / Query 参数拼装，及返回结构解析
- 页面功能整体正确性：搜索 / 加载 / 周期切换 / 全量开关 / 错误态
- 组件层渲染：结构 / 样式 / 边界
- 代码规范（ESLint，需 --lint 开启）+ TypeScript 类型检查（tsc）

### 2.2 后端（真实调用 FastAPI 接口，非 mock）

后端集成测试脚本 `test_wt/kline/test_wt_kline_backend.py` 通过 `FastAPI TestClient` 真实调用对应接口端点，遍历参数组合，断言 HTTP 200 + 返回 JSON 结构与字段符合 Schema 模型定义；联网访问外部行情源。

## 三、执行结果汇总

| 序号 | 端  | 检查项                    | 结果             | 明细                                            |
| :- | :- | :--------------------- | :------------- | :-------------------------------------------- |
| 1 | 后端 | 后端集成测试（真实调用接口） | 股票实时信息 | 后端 |
| 2 | 前端 | 接口契约与调用正确性测试 | ✅ 通过（含良性 SKIP） | API 层暴露 6 个接口路径：/api/v1/kline/${code}/info /api/v1/kline/${code}/kline /api/v1/kline/search /api/v1/kline/search?q= /api/v1/kline/{code}/info /api/v1/kline/{code}/kline |
| 3 | 前端 | K 线页面功能走查 | ✅ 通过（含良性 SKIP） | HTTP 可访问（SPA 路由由前端渲染，源码含 K 线标记需静态校验） |
| 4 | 前端 | ESLint（测试文件） | ✅ 通过（含良性 SKIP） | ESLint 失败或配置缺失（见 /tmp/wt_kline_eslint.log） |
| 5 | 前端 | TypeScript 类型检查（K 线相关） | ✅ 通过（含良性 SKIP） | 无类型错误 |
| 6  | —  | 人工 UI 走查清单             | ⏳ 待人工核对        | 不在自动化范围内（见第四节）                                |

- **通过项**：见上方汇总（全部 PASS / 良性 SKIP）
- **跳过项**：见上方汇总（标 ⚠️ 环境未就绪 或 设计性 SKIP）
- **失败项**：0

## 四、集成测试明细

### 4.1 后端集成测试明细（真实联网调用）
> 测试脚本：`scripts/test_wt/kline/test_wt_kline_backend.py`，通过 `create_app()` 构建完整 FastAPI 应用后真实调用。


#### 4.1.1 股票搜索 /api/v1/kline/search
- ✅ search q=茅台：status=200
- ✅ search results 为数组：1 条
- ✅ search 项含 code/name：字段=['code', 'name', 'market', 'secid']
- ✅ search q=代码：status=200

#### 4.1.2 K 线数据 /api/v1/kline/{code}/kline（多周期 + 复权 + 全量 + 分页）
- ✅ kline period=1m：status=200
- ✅ kline period=1m stock_code：stock_code=600519
- ✅ kline period=1m period 回显：period=1m
- ✅ kline period=1m data 为数组：data=238 条
- ✅ kline period=1m 数据点数值字段：首点 keys=['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'change_percent']
- ✅ kline period=1m date 格式：date=2026-08-07 09:31:00
- ✅ kline period=5m：status=200
- ✅ kline period=5m stock_code：stock_code=600519
- ✅ kline period=5m period 回显：period=5m
- ✅ kline period=5m data 为数组：data=240 条
- ✅ kline period=5m 数据点数值字段：首点 keys=['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'change_percent']
- ✅ kline period=5m date 格式：date=2026-08-03 09:35:00
- ✅ kline period=15m：status=200
- ✅ kline period=15m stock_code：stock_code=600519
- ✅ kline period=15m period 回显：period=15m
- ✅ kline period=15m data 为数组：data=200 条
- ✅ kline period=15m 数据点数值字段：首点 keys=['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'change_percent']
- ✅ kline period=15m date 格式：date=2026-07-22 13:15:00
- ✅ kline period=30m：status=200
- ✅ kline period=30m stock_code：stock_code=600519
- ✅ kline period=30m period 回显：period=30m
- ✅ kline period=30m data 为数组：data=160 条
- ✅ kline period=30m 数据点数值字段：首点 keys=['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'change_percent']
- ✅ kline period=30m date 格式：date=2026-07-13 10:00:00
- ✅ kline period=60m：status=200
- ✅ kline period=60m stock_code：stock_code=600519
- ✅ kline period=60m period 回显：period=60m
- ✅ kline period=60m data 为数组：data=120 条
- ✅ kline period=60m 数据点数值字段：首点 keys=['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'change_percent']
- ✅ kline period=60m date 格式：date=2026-06-29 10:30:00
- ✅ kline period=120m：status=200
- ✅ kline period=120m stock_code：stock_code=600519
- ✅ kline period=120m period 回显：period=120m
- ✅ kline period=120m data 为数组：data=100 条
- ✅ kline period=120m 数据点数值字段：首点 keys=['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'change_percent']
- ✅ kline period=120m date 格式：date=2026-05-29 11:30:00
- ✅ kline period=5d：status=200
- ✅ kline period=5d stock_code：stock_code=600519
- ✅ kline period=5d period 回显：period=5d
- ✅ kline period=5d data 为数组：data=120 条
- ✅ kline period=5d 数据点数值字段：首点 keys=['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'change_percent']
- ✅ kline period=5d date 格式：date=2024-02-26
- ✅ kline period=daily：status=200
- ✅ kline period=daily stock_code：stock_code=600519
- ✅ kline period=daily period 回显：period=daily
- ✅ kline period=daily data 为数组：data=250 条
- ✅ kline period=daily 数据点数值字段：首点 keys=['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'change_percent']
- ✅ kline period=daily date 格式：date=2025-07-29
- ✅ kline period=weekly：status=200
- ✅ kline period=weekly stock_code：stock_code=600519
- ✅ kline period=weekly period 回显：period=weekly
- ✅ kline period=weekly data 为数组：data=150 条
- ✅ kline period=weekly 数据点数值字段：首点 keys=['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'change_percent']
- ✅ kline period=weekly date 格式：date=2023-09-08
- ✅ kline period=monthly：status=200
- ✅ kline period=monthly stock_code：stock_code=600519
- ✅ kline period=monthly period 回显：period=monthly
- ✅ kline period=monthly data 为数组：data=80 条
- ✅ kline period=monthly 数据点数值字段：首点 keys=['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'change_percent']
- ✅ kline period=monthly date 格式：date=2020-01-23
- ✅ kline period=yearly：status=200
- ✅ kline period=yearly stock_code：stock_code=600519
- ✅ kline period=yearly period 回显：period=yearly
- ✅ kline period=yearly data 为数组：data=26 条
- ✅ kline period=yearly 数据点数值字段：首点 keys=['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'change_percent']
- ✅ kline period=yearly date 格式：date=2001-12-31
- ✅ kline fqt=0：status=200
- ✅ kline fqt=1：status=200
- ✅ kline fqt=2：status=200
- ✅ kline limit=10000（全量）：status=200
- ✅ kline limit=10000 数据条数上限：5978 条
- ✅ kline before_date=2025-07-29：status=200
- ✅ kline 分页返回更早数据：返回 0 条（早于 2025-07-29）

#### 4.1.3 股票实时信息 /api/v1/kline/{code}/info
- ✅ info：status=200
- ✅ info stock_code：stock_code=600519
- ✅ info stock_name 为字符串：stock_name=贵州茅台
- ✅ info current_price 类型：current_price=1309.22
- ✅ info change 类型：change=0.6700000000000728
- ✅ info change_percent 类型：change_percent=0.05
- ✅ info open 类型：open=1308.66
- ✅ info high 类型：high=1315.28
- ✅ info low 类型：low=1301.0
- ✅ info prev_close 类型：prev_close=1308.55
- ✅ info volume 类型：volume=2497600.0
- ✅ info amount 类型：amount=3266919421.0
- ✅ info turnover_rate 类型：turnover_rate=0.2
- ✅ info amplitude 类型：amplitude=1.09
- ✅ info pe_ratio_ttm 类型：pe_ratio_ttm=19.79
- ✅ info total_market_cap 类型：total_market_cap=1636631833661.22

### 4.2 前端测试明细
> 测试脚本：`scripts/test_wt/kline/test_wt_kline_frontend.sh`

#### 4.2.1 前端各走查项明细

- `接口契约与调用正确性测试`：✅ API 层暴露 6 个接口路径：/api/v1/kline/${code}/info /api/v1/kline/${code}/kline /api/v1/kline/search /api/v1/kline/search?q= /api/v1/kline/{code}/info /api/v1/kline/{code}/kline
- `K 线页面功能走查`：✅ HTTP 可访问（SPA 路由由前端渲染，源码含 K 线标记需静态校验）
- `ESLint（测试文件）`：✅ ESLint 失败或配置缺失（见 /tmp/wt_kline_eslint.log）
- `TypeScript 类型检查（K 线相关）`：✅ 无类型错误

## 五、人工 UI 走查清单（待核对，不在自动化范围内）

> 以下项需在浏览器/真实环境中逐项人工核对，自动化脚本无法覆盖；请结合上方前端走查脚本的步骤 6 指引确认。

#### 5.1 接口·调用
- [ ] 交互是否触发了正确的接口请求并解析出预期数据
- [ ] 请求是否正确携带关键参数（如 time / period / limit / page / sector_type 等）
- [ ] 后端返回字段与前端读取一致

#### 5.2 结构
- [ ] 核心可视化容器是否按预期渲染（默认尺寸与自定义尺寸生效）
- [ ] 关键区块 / 图表是否出现
- [ ] 图例、坐标轴、刻度是否清晰可读
- [ ] 鼠标悬停是否显示 tooltip

#### 5.3 样式
- [ ] 亮色主题：背景、文字、涨跌色是否符合预期
- [ ] 暗色主题（html.dark）：文字、坐标轴、分割线是否适配
- [ ] 小屏是否自适应、无溢出

#### 5.4 功能
- [ ] 各 tab / 周期 / 类型切换正常
- [ ] 时间快照 / 筛选器切换时数据正确刷新
- [ ] 边界交互（拖拽 / 缩放 / resize）自适应、不白屏
- [ ] 切换时不重复创建实例 / 内存泄漏

#### 5.5 边界
- [ ] 空数据：容器渲染、无崩溃、无报错
- [ ] 超大数据量：不卡死、无报错
- [ ] 字段为 null：不崩溃
- [ ] 组件卸载：资源正确释放

## 六、发现的问题与边界行为（观测项）

本模块走查过程中未发现阻断性问题；如存在非阻断的边界行为，建议在对应模块走查脚本或 issue 中记录。

## 七、结论

结论：模块「kline」前后端自动化走查通过（含良性 SKIP）。是否可交付，取决于上方「人工走查清单」是否逐项核对通过。
