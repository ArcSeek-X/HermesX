# kline 功能模块 - 测试走查报告

**基本信息：**

- **报告名称**：`test_wt_kline_report_2026_08_07_18_51_21.md`
- **生成目录**：`/Users/gaocangxiong/Work/DevProject/HermesX/apps/hrs-web/.test_record/test_wt_report_2026_08_07_18_51_21`
- **执行脚本**：`apps/hrs-web/scripts/test_wt/test_wt.sh`
- **执行时间**：2026\_08\_07\_18\_51\_21
- **功能模块**：kline
- **执行结果**：✅ 通过（含良性 SKIP）

**环境信息：**

- **前端环境**：Node（npm/npx Vitest / tsc），由 test\_wt/kline/ 下前端走查脚本执行
- **后端环境**：Python（FastAPI TestClient，真实调用接口，非 mock）；联网访问外部行情源
- **执行目录**：`apps/hrs-web`
- **脚本退出码**：`0`（0=通过/良性SKIP，1=失败，2=环境未就绪）

## 一、走查范围（前后端同时走查）

本模块走查覆盖其同名子目录（`test_wt/kline/`），执行脚本进行测试：

- **后端**：`test_wt_kline_backend.py`
- **前端**：`test_wt_kline_frontend.sh`

## 二、执行介绍（前后端同时走查）

### 2.1 前端（mock 后端，验证请求拼装与返回解析）

1. 接口契约 + 调用正确性：`search / kline / info` 三个接口的 URL / Query 参数拼装，及返回结构解析
   - 参数覆盖：11 种 period、3 种 fqt、多种 search query（代码/拼音/中文名）、limit 边界（1/默认/10000）、before\_date 分页
2. 页面功能整体正确性：搜索中文名解析代码 → 加载信息头部 + K 线、11 种周期切换、全量开关、错误态
3. 组件层渲染：`KLineChart` 结构 / 样式 / 边界

### 2.2 后端（真实调用 FastAPI 接口，非 mock）

- 用 `FastAPI TestClient` 真实调用 `api.v1.endpoints.kline`，遍历全部参数组合，
  断言 HTTP 200 + 返回 JSON 结构与字段符合 `api/v1/schemas/kline.py` 模型定义：
  - 搜索接口：5 种 query 条件（代码 / 拼音简拼 / 中文名 / 港股代码 / 美股代码）
  - K 线接口：11 period × 3 fqt × 3 limit = 99 组合
  - 分页（before\_date 游标）
  - 信息接口

## 三、执行结果汇总

| 序号 | 端  | 检查项                    | 结果             | 明细                                            |
| :- | :- | :--------------------- | :------------- | :-------------------------------------------- |
| 1  | 前端 | KLineChart 组件单元测试      | ✅ 通过（含良性 SKIP） | 28 tests passed                               |
| 2  | 前端 | 接口契约与调用正确性测试           | ✅ 通过（含良性 SKIP） | 28 tests passed（11 周期 + 5 query + 3 limit 边界） |
| 3  | 前端 | 页面功能走查                 | ✅ 通过（含良性 SKIP） | 16 tests passed（含 11 周期切换矩阵）                  |
| 4  | 前端 | ESLint（测试文件）           | ✅ 通过（含良性 SKIP） | 无错误                                           |
| 5  | 前端 | TypeScript 类型检查（K 线相关） | ✅ 通过（含良性 SKIP） | 无类型错误                                         |
| 6  | 后端 | 后端集成测试（真实调用）           | ✅ 通过（含良性 SKIP） | PASS=106 / FAIL=0 / SKIP=0                    |
| 7  | —  | 人工 UI 走查清单             | ⏳ 待人工核对        | 不在自动化范围内（见第三节）                                |

- **通过项**：6（前端 5 + 后端 1），详见上方汇总（全部 PASS / 良性 SKIP）
- **跳过项**：见上方汇总（标 ⚠️ 环境未就绪 或 设计性 SKIP）
- **失败项**：0

## 四、集成测试明细

### 4.1 后端集成测试明细（真实联网调用）

> 测试脚本：`scripts/test_wt/kline/test_wt_kline_backend.py`，通过 `create_app()` 构建完整 FastAPI 应用后真实调用。
> 由于本地环境无法安装 `litellm`（analyzer 链路的 LLM 依赖），脚本内置最小 `litellm` 桩仅用于打通 import，
> K 线接口运行时并不依赖 LLM，因此真实行为不受影响。

#### 4.1.1 搜索接口（5 条件）

- `q=600519`（代码）✅
- `q=maotai`（拼音简拼）✅
- `q=贵州茅台`（中文名）✅
- `q=00700`（港股代码）✅
- `q=AAPL`（美股代码）✅

#### 4.1.2 K 线接口（11 period × 3 fqt × 3 limit = 99 组合）

所有组合均返回 HTTP 200，且：

- `period` 回显与入参一致
- 响应含 `stock_code / period / secid / data` 字段
- `data` 为列表且每根含 `date/open/close/high/low`
- `limit=1` 与 `limit=10000` 均能拉到非空数据（limit 透传生效）
- 覆盖：1m / 5m / 15m / 30m / 60m / 120m / 5d / daily / weekly / monthly / yearly
- 覆盖 fqt：0（不复权）/ 1（前复权）/ 2（后复权）

#### 4.1.3 分页（before\_date）

- 首屏 `daily` 取 10 根，取最后一根日期作为 `before_date` 再取下一页，
  下一页所有日期均早于游标日期 → 分页方向正确 ✅

#### 4.1.4 信息接口

- 返回 HTTP 200，含 `stock_code / current_price` 等字段 ✅

### 4.2、前端测试明细

> 测试脚本：`scripts/test_wt/kline/test_wt_kline_frontend.sh`

#### 4.2.1 KLineChart 组件单元测试（28 tests）

结构 / 样式 / 边界渲染全部通过。

#### 4.2.2 接口契约与调用正确性（28 tests）

- 原始契约：3 个接口 URL 拼装、返回结构解析
- 新增：`period` 全 11 种正确下发；`search` 5 种 query 条件正确拼装 `q`；`limit` 边界（1/500/10000）正确下发

#### 4.2.3 页面功能走查（16 tests）

- 原始：初始渲染、搜索中文名加载、周期切换（周K）、全量开关、错误态
- 新增：11 周期切换矩阵，每个周期按钮均触发 `fetchKLine(对应 period)`

## 五、人工 UI 走查清单（待核对，不在自动化范围内）

> 以下项需在浏览器/真实环境中逐项人工核对，自动化脚本无法覆盖；请结合上方前端走查脚本的步骤 6 指引确认。

#### 5.1 接口·调用

- [ ] 搜索中文名/代码/拼音时是否真正发起 `GET /api/v1/kline/search?q=` 并解析出代码
- [ ] K 线请求是否携带 `period / fqt / limit / page / before_date`（全量 `limit=10000`）
- [ ] 后端返回的 `KLinePoint` 字段（open/close/high/low/volume...）与 `KLineChart` 读取一致
- [ ] `StockInfo` 蛇形字段（stock\_name/current\_price...）与 `StockInfoHeader` 读取一致
- [ ] `searchStocks` 返回 `[{code,name}]` 与页面解析一致

#### 5.2 结构

- [ ] K 线图容器是否按预期渲染（默认高度 500px，自定义 height 生效）
- [ ] 图表区是否出现蜡烛图 + 成交量副图 + MACD 副图
- [ ] 图例是否展示 MA5/MA10/MA30/MA60、MACD 等系列名称
- [ ] 横轴时间刻度、纵轴价格刻度是否清晰可读
- [ ] 鼠标悬停是否显示 tooltip（时间 + OHLC + 涨跌幅 + 量）

#### 5.3 样式

- [ ] 亮色主题：背景透明、文字 `#333333`、红涨绿跌（`#ef5350` / `#26a69a`）
- [ ] 暗色主题（`html.dark`）：文字 `#e0e0e0`、坐标轴/分割线变深
- [ ] 小屏（<1000px）是否自动隐藏部分刻度/压缩间距，无溢出
- [ ] MA 线颜色是否符合规范（MA5 橙 / MA10 紫 / MA30 蓝 / MA60 绿）

#### 5.4 功能

- [ ] 分时(1m)：以 prevClose 为基准线，正确显示涨跌幅
- [ ] 日/周/月/年：蜡烛图 + 均线正常
- [ ] 5 日 K：由日 K 聚合，单根代表 5 个交易日
- [ ] 分钟线(5/15/30/60/120m)：正常显示
- [ ] 全量数据开关：拉取 `limit=10000`，拖到最左显示全部历史
- [ ] dataZoom 拖到左边界触发分页加载（`onDataZoomBoundary` → `before_date`）
- [ ] 窗口缩放(resize)图表自适应、不白屏
- [ ] 切换股票/周期时图表平滑更新，不重复创建实例/内存泄漏

#### 5.5 边界

- [ ] 空数据：容器渲染、无崩溃、无报错
- [ ] 单根数据：正常渲染
- [ ] 超大数据量(>=1000 根)：不卡死、无报错
- [ ] volume/amount/change\_percent 为 null：不崩溃
- [ ] 组件卸载：echarts 资源正确释放

## 六、发现的问题与边界行为（观测项）

本模块走查过程中未发现阻断性问题；如存在非阻断的边界行为，建议在对应模块走查脚本或 issue 中记录。

## 七、结论

结论：模块「kline」前后端自动化走查通过（含良性 SKIP）。是否可交付，取决于上方「人工走查清单」是否逐项核对通过。
