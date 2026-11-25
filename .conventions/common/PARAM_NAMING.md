# <a id="参数命名规范"></a>参数命名规范（后缀与前缀约定）

> 📝 **方案简述**：本规范面向 HermesX 前端 React + TypeScript 代码中的变量、函数参数、Hook 返回值与组件 Props 数据字段，规定按值的语义使用统一后缀（`Msg` / `Code` / `Data` / `State` / `Fn`）与动作前缀（`open` / `close`），解决同类值命名摇摆、看名字无法判断类型与用途的问题。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-11-25

## 方案目录

- [一、总则](#一总则)
- [二、后缀规则总览](#二后缀规则总览)
- [三、数据类后缀判定](#三数据类后缀判定)
- [四、状态类后缀](#四状态类后缀)
- [五、方法类后缀与动作前缀](#五方法类后缀与动作前缀)
- [六、功能点前缀](#六功能点前缀)
- [七、正反对照](#七正反对照)
- [八、执行流程](#八执行流程)
- [九、交付检查清单](#九交付检查清单)

---

<a id="一总则"></a>

## 一、总则

- 【强制】适用范围：`apps/hrs-web` 等前端 TS / TSX 代码中的**局部变量、函数参数、Hook 对外返回值、组件 Props 中承载数据的字段**。
- 【强制】按**值的语义**分类，不按实现类型机械判断：同样是字符串，可能是消息（`Msg`）也可能是结果码（`Code`）；同样是对象，可能是数据（`Data`）。
- 【强制】结构统一：`前缀 + 功能点 + 语义词 + 后缀`，后缀永远在名称末尾。
- 【推荐】一个值只归入一类；边界不清时按"三、数据类后缀判定"的顺序逐级判断。
- 【强制】批量重命名时优先用带单词边界的精确匹配，只改目标范围（Hook 内部引用、调用方），**不要误改组件 Props 名、后端 API 方法名和类型名**；改完必须跑 lint / 测试 / build 确认。

---

<a id="二后缀规则总览"></a>

## 二、后缀规则总览

| 语义类别 | 判定条件 | 后缀 | 示例 |
|---|---|---|---|
| 消息 / 文案 | 字符串，且**本身就是展示给用户的消息或文案** | `Msg` | `errorMsg`、`connectionErrorMsg` |
| 状态码 / Code | 字符串或数字，且**表示状态码、业务码、标识值**（常用于拼 i18n key 或查映射表） | `Code` | `resultCode`、`orgActionFeedbackCode` |
| 数据 | 对象，且明确是数据类：表格数据、查询条件、弹窗上下文、异常对象等 | `Data` | `orgTableData`、`orgSearchDraftData`、`orgQueryErrorData` |
| 状态 | 布尔值，表示某个进行中 / 开关态 | `State` | `isOrgSavingState`、`isOrgFetchingState` |
| 方法 | 函数 | `Fn` | `submitOrgFormFn`、`openOrgEditorDialogFn` |

> 判定顺序：先排除函数（`Fn`）与布尔（`State`），再在字符串 / 数字中区分 `Msg` 与 `Code`，最后对象归 `Data`。

---

<a id="三数据类后缀判定"></a>

## 三、数据类后缀判定

**规定**：字符串分 `Msg` 与 `Code`，对象统一 `Data`。

### 3.1 `Msg`：值是文案本身

- 该字符串可以直接展示给用户，不需要再映射。
- 例：`const errorMsg = t('orgManagement.error.connection')`。

### 3.2 `Code`：值是码 / 标识

- 该字符串或数字是**标识**，需要经映射表或 i18n 转换成文案。
- 例：`orgActionFeedbackCode` 的取值是 `'created' | 'updated' | 'savedRefreshFailed' | ...`，页面通过 `t('orgManagement.feedback.' + orgActionFeedbackCode)` 转成文案，因此是 `Code` 而非 `Msg`。
- 例：`resultCode`、`statusCode`、`orgActionErrorCode`。

### 3.3 `Data`：值是对象

- 表格数据：`orgTableData`（分页树数据）。
- 查询条件：`orgSearchDraftData`（表单草稿）。
- 弹窗上下文：`orgEditorDialogData`、`orgDeleteDialogData`。
- **异常对象也算数据**：`orgQueryErrorData`、`orgActionErrorData` 存的是 `OrganizationApiError` / `Error` 实例，虽然名称含 `Error`，但类型是对象且带 `resultCode`，按规则用 `Data`。若转成字符串会丢失业务码，导致错误退化成通用文案，因此不能改成 `Msg`。

**Why**：后缀表达的是"这个值怎么用"——能直接展示的是 `Msg`，需要映射的是 `Code`，承载结构的是 `Data`。只按 JS 的 `typeof` 判断会把 `orgActionFeedbackCode` 误分成 `Msg`。

**How to apply**：新增变量时先问"这个字符串会被直接渲染吗"——会则是 `Msg`，不会则是 `Code`；对象一律 `Data`。

---

<a id="四状态类后缀"></a>

## 四、状态类后缀

**规定**：布尔状态用 `is + 功能点 + 动作 + State`。

- 格式：`is{功能点}{动作}State`，如 `isOrgSavingState`、`isOrgFetchingState`、`isOrgDeletingState`、`isOrgPreparingEditorState`。
- 【强制】只有布尔值才能用 `State`；非布尔的状态值（如 `'created'`）用 `Code`。
- 【推荐】避免 `loading` / `state` / `flag` 这类通名，动作词要具体（Saving / Fetching / Deleting / Preparing）。

**Why**：`is` 开头一眼可识别布尔，`State` 后缀与 `Data` / `Fn` 形成对称，避免 `isSavingOrganization` 与 `savingOrganizationState` 混用。

**How to apply**：Hook 返回的加载态、开关态、进行中标志统一按此格式命名。

---

<a id="五方法类后缀与动作前缀"></a>

## 五、方法类后缀与动作前缀

**规定**：函数末尾加 `Fn`；动作词从 §5.1 词表统一选取，打开用 `open`、关闭用 `close`。

### 5.1 通用方法

- 格式：`{动作词}{功能点}{对象}Fn`。
- 【强制】动作词统一从下表选取。`save` / `store` / `persist` 为**禁用词**，使用即视为命名违规（评审应报错）；「提交表单」用 `submit`，「设置状态」用 `set`。

| 动作 | 动作词 | 示例 |
|---|---|---|
| 设置 | `set` | `setOrgSearchDraftFn` |
| 查询 | `query` | `queryOrgTableFn` |
| 重置 | `reset` | `resetOrgSearchFn` |
| 重试 | `retry` | `retryOrgQueryFn` |
| 变更 / 切换 | `change` | `changeOrgTablePageFn` |
| 新增 | `create` | `createOrgFn` |
| 删除 | `delete` | `deleteOrgFn` |
| 更新 | `update` | `updateOrgFn` |
| 提交 | `submit` | `submitOrgFormFn` |
| 确认 | `confirm` | `confirmOrgDeletionFn` |
| 打开 | `open` | `openOrgEditorDialogFn` |
| 关闭 | `close` | `closeOrgEditorDialogFn` |

### 5.2 打开 / 关闭动作

- 【强制】展示 UI 的方法用 `open`，隐藏 UI 的方法用 `close`，不使用 `prepare` / `request` / `dismiss`。
- 例：

| 旧命名（不推荐） | 新命名（强制） |
|---|---|
| `prepareOrgEditorDialogFn` | `openOrgEditorDialogFn` |
| `dismissOrgEditorDialogFn` | `closeOrgEditorDialogFn` |
| `requestOrgDeletionFn` | `openOrgDeletionFn` |
| `dismissOrgDeletionFn` | `closeOrgDeletionFn` |

**Why**：`prepare` / `request` 无法一眼看出是打开动作，`dismiss` 与 `close` 语义重叠；统一 `open` / `close` 后，调用方看到方法名即可判断是否会展示弹窗。

**How to apply**：只要方法有"展示 / 隐藏 UI（弹窗、抽屉、浮层）"的语义，一律用 `open` / `close` 开头。

---

<a id="六功能点前缀"></a>

## 六、功能点前缀

- 【强制】用业务功能点的简短标识作为前缀，同一模块内保持一致。例：组织管理模块统一用 `org`——`orgTableData`、`orgQueryErrorData`、`isOrgSavingState`、`submitOrgFormFn`。
- 【推荐】Hook 实例变量可加 `Hook` 后缀表明来源，例：`orgManagementHook = useOrganizationManagement()`。
- 【推荐】表格数据采用"功能点 + Table + 含义"，例：`organizationPage` → `orgTableData`。

**Why**：前缀让同一模块的值在 IDE 中聚集，跨模块调用时能立刻判断归属；`Hook` 后缀区分"hook 返回值整体"与"其中某一项"。

**How to apply**：新模块先确定简短前缀（如 `org`、`stock`），模块内所有对外值统一使用。

---

<a id="七正反对照"></a>

## 七、正反对照

| ✅ 推荐 | ❌ 避免 | 原因 |
|---|---|---|
| `orgActionFeedbackCode` | `orgActionFeedbackData` | 字符串结果码不是 Data |
| `orgQueryErrorData` | `orgQueryErrorMsg` | 异常是对象，转字符串会丢 `resultCode` |
| `isOrgSavingState` | `isSavingOrganization` | 缺少功能点前缀与 `State` 后缀 |
| `submitOrgFormFn` | `saveOrganization` | 动作词应为 `submit`，且方法缺 `Fn` 后缀 |
| `openOrgEditorDialogFn` | `prepareOrgEditorDialogFn` | 打开动作必须用 `open` |
| `closeOrgDeletionFn` | `dismissOrgDeletionFn` | 关闭动作必须用 `close` |
| `orgTableData` | `organizationPage` | 表格数据用 `Data` 后缀统一 |

---

<a id="八执行流程"></a>

## 八、执行流程

1. 列出目标值（Hook 返回值 / 参数 / 局部变量），逐个判断语义类别。
2. 按"二、后缀规则总览"选后缀；字符串按"三、数据类后缀判定"区分 `Msg` 与 `Code`。
3. 为每项加统一的功能点前缀；打开 / 关闭动作改用 `open` / `close`。
4. 批量替换时用带 `\b` 单词边界的精确匹配，限定目标文件范围。
5. 替换后检查是否误改组件 Props 名、API 方法名、类型名——这些不在命名范围内。
6. 同步更新注释与文档，跑 ESLint、相关测试与 `npm run build` 验证。

---

<a id="九交付检查清单"></a>

## 九、交付检查清单

- [ ] 每个变量 / 参数 / Hook 返回值按语义分类并带正确后缀（`Msg` / `Code` / `Data` / `State` / `Fn`）
- [ ] 字符串消息用 `Msg`，字符串 / 数字状态码用 `Code`，对象数据（含异常对象）用 `Data`
- [ ] 布尔状态用 `is + 功能点 + 动作 + State`
- [ ] 方法用 `Fn` 后缀，打开 / 关闭动作用 `open` / `close`
- [ ] 功能点前缀在同一模块内一致
- [ ] 批量重命名未误改组件 Props 名、后端 API 方法名与类型名
- [ ] 注释与文档同步更新
- [ ] ESLint、相关测试与 `npm run build` 全部通过
