# 组件 Demo 示例页面批量生成方案

> 状态：第一批（11 个组件）已实施完成；本批为第二批增量（Input / TextArea / Chip 共 3 个组件），待评审。

## 1. 目标与范围

第一批已为 11 个组件生成组件文档 Demo 页面；本批新增 3 个基础输入类组件，完全对齐现有参考实现 `Docs_checkbox.tsx` 的挂载链路与页面风格：

| # | 批次 | 组件 | 组件源码路径 |
|---|------|------|-------------|
| 1 | 第一批（已完成） | Drawer（HrsDrawer） | `apps/hrs-web/src/components/basic/Drawer/Drawer.tsx` |
| 2 | 第一批（已完成） | HrsButton | `apps/hrs-web/src/components/basic/HrsButton/HrsButton.tsx` |
| 3 | 第一批（已完成） | HrsSelect | `apps/hrs-web/src/components/basic/HrsSelect/HrsSelect.tsx` |
| 4 | 第一批（已完成） | Separator | `apps/hrs-web/src/components/basic/Separator/Separator.tsx` |
| 5 | 第一批（已完成） | Table | `apps/hrs-web/src/components/basic/Table/Table.tsx` |
| 6 | 第一批（已完成） | Toast | `apps/hrs-web/src/components/basic/Toast/Toast.tsx` |
| 7 | 第一批（已完成） | Modal | `apps/hrs-web/src/components/basic/Modal.tsx` |
| 8 | 第一批（已完成） | AnimCard | `apps/hrs-web/src/components/common/Card/AnimCard.tsx` |
| 9 | 第一批（已完成） | NewsCard | `apps/hrs-web/src/components/common/Card/newsCard.tsx` |
| 10 | 第一批（已完成） | ListCard | `apps/hrs-web/src/components/common/ListCard.tsx` |
| 11 | 第一批（已完成） | TabNav | `apps/hrs-web/src/components/common/TabNav.tsx` |
| 12 | 第二批（本批） | Input | `apps/hrs-web/src/components/basic/Input.tsx` |
| 13 | 第二批（本批） | TextArea | `apps/hrs-web/src/components/basic/TextArea.tsx` |
| 14 | 第二批（本批） | Chip | `apps/hrs-web/src/components/basic/Chip.tsx` |

## 2. 现状：参考实现的挂载链路（4 个挂载点）

`Docs_checkbox.tsx` 一个页面需要同步改动 4 处（每处按组件重复）：

1. **页面文件**：`apps/hrs-web/src/pages/DocsPage/Components/Docs_checkbox.tsx`
   - 导出命名组件 `DocsCheckboxPage` + default 导出
   - 结构：`<AppPage>` → header（h1 用 `t('layout.nav.development.docsXxx.title')` + 简介 p）→ 多个示例 section（`rounded-lg border border-border/70 bg-card/75 p-6` 卡片风格）
2. **路由注册**：`apps/hrs-web/src/App.tsx`
   - `lazy(() => import('./pages/DocsPage/Components/Docs_xxx'))` + Shell 内 `<Route path="/docs/component/xxx" element={...} />`（现有 checkbox 路由在第 157 行附近）
3. **调试菜单**：`apps/hrs-web/src/components/layout/SidebarNav.tsx`
   - 追加到 `DEBUG_NAV_ITEMS` 数组（仅开发调试模式显示），需要 `key / labelKey / to / icon` 四项
4. **三语 i18n**：`apps/hrs-web/src/i18n/uiText-zh.ts`、`uiText-zh-Hant.ts`、`uiText-en.ts`
   - 每个组件新增 2 个 key：`layout.nav.development.docsXxx.title` 与 `.description`
   - zh 是 key 真源（`UiTextKey` 类型由此文件推导），三语 key 集合必须完全对齐，否则 `tsc -b` 报错

## 3. 命名方案总表

文件命名沿用现有参考的 `Docs_checkbox.tsx` snake_case 风格（多词组件按单词下划线连接，与路由段一致）：

| 组件 | 菜单名称（调试菜单） | 路由 | 页面文件 | 导出组件名 | i18n key 前缀 |
|------|---------------------|------|----------|-----------|---------------|
| Drawer | 抽屉 | `/docs/component/drawer` | `Docs_drawer.tsx` | `DocsDrawerPage` | `layout.nav.development.docsDrawer` |
| HrsButton | 按钮 | `/docs/component/button` | `Docs_button.tsx` | `DocsButtonPage` | `layout.nav.development.docsButton` |
| HrsSelect | 下拉选择 | `/docs/component/select` | `Docs_select.tsx` | `DocsSelectPage` | `layout.nav.development.docsSelect` |
| Separator | 分割线 | `/docs/component/separator` | `Docs_separator.tsx` | `DocsSeparatorPage` | `layout.nav.development.docsSeparator` |
| Table | 表格 | `/docs/component/table` | `Docs_table.tsx` | `DocsTablePage` | `layout.nav.development.docsTable` |
| Toast | 轻提示 | `/docs/component/toast` | `Docs_toast.tsx` | `DocsToastPage` | `layout.nav.development.docsToast` |
| Modal | 模态框 | `/docs/component/modal` | `Docs_modal.tsx` | `DocsModalPage` | `layout.nav.development.docsModal` |
| AnimCard | 动画卡片 | `/docs/component/animCard` | `Docs_animCard.tsx` | `DocsAnimCardPage` | `layout.nav.development.docsAnimCard` |
| NewsCard | 快讯卡片 | `/docs/component/newsCard` | `Docs_newsCard.tsx` | `DocsNewsCardPage` | `layout.nav.development.docsNewsCard` |
| ListCard | 列表卡片 | `/docs/component/listCard` | `Docs_listCard.tsx` | `DocsListCardPage` | `layout.nav.development.docsListCard` |
| TabNav | 标签页 | `/docs/component/tabNav` | `Docs_tabNav.tsx` | `DocsTabNavPage` | `layout.nav.development.docsTabNav` |

菜单顺序按用户列出的组件顺序排列（Drawer → HrsButton → ... → TabNav），追加在现有「复选框」菜单之后。

第二批 3 个组件（本批新增）：

| 组件 | 菜单名称（调试菜单） | 路由 | 页面文件 | 导出组件名 | i18n key 前缀 |
|------|---------------------|------|----------|-----------|---------------|
| Input | 输入框 | `/docs/component/input` | `Docs_input.tsx` | `DocsInputPage` | `layout.nav.development.docsInput` |
| TextArea | 文本域 | `/docs/component/textArea` | `Docs_textArea.tsx` | `DocsTextAreaPage` | `layout.nav.development.docsTextArea` |
| Chip | 标签芯片 | `/docs/component/chip` | `Docs_chip.tsx` | `DocsChipPage` | `layout.nav.development.docsChip` |

命名说明：Input / Chip 为单词直接用小写；TextArea 为多词组件，沿用第一批 camelCase 约定（`textArea`，与 animCard / newsCard / listCard / tabNav 一致）。菜单追加在第一批「标签页」之后。

## 4. 各组件 Demo 页面内容设计

每个页面统一：header（标题 + 一句话组件简介）+ 3~6 个示例 section，示例覆盖组件真实 API 能力，交互状态用 `useState` 维护（对齐 Docs_checkbox 风格）。

### 4.1 Docs_drawer.tsx（抽屉）
- 示例一：声明式基础用法（`isOpen` + `title` + `HrsDrawer.Body`/`Footer`，HrsButton 触发）
- 示例二：四个滑出方向（`placement`: top/bottom/left/right，各一个按钮）
- 示例三：尺寸对比（`size`: sm/md/lg/xl，演示左右控宽、上下控高）
- 示例四：遮罩变体（`variant`: opaque/blur/transparent）
- 示例五：`showHandle` 拖拽手柄 + `hideCloseButton` 隐藏关闭按钮 + `footer` 快捷 prop

### 4.2 Docs_button.tsx（按钮）
- 示例一：主操作变体（primary / primary-soft / gradient / secondary / outline / ghost）
- 示例二：语义变体（danger / danger-soft / success / success-soft / warning / warning-soft）
- 示例三：尺寸对比（xs / sm / md / lg / xl）
- 示例四：加载态（`isLoading` + `loadingText`，点击模拟 2s 加载）
- 示例五：禁用态（`isDisabled`）与发光（`glow`）
- 示例六：`onClick` 事件桥接演示（点击计数，验证 onClick→onPress 桥接生效）

### 4.3 Docs_select.tsx（下拉选择）
- 示例一：基础单选（受控 `value`/`onChange`，含 disabled 选项）
- 示例二：分组选项（`HrsSelectSectionDef` 分组 + 自动分隔线）
- 示例三：多选模式（`selectionMode="multiple"`，对比 `collapseTags` true/false）
- 示例四：尺寸对比（xs / sm / md / lg）
- 示例五：`label` + `description` + `isInvalid` + `errorMessage` 校验态
- 示例六：整组件禁用（`isDisabled`）与 `renderItem` 自定义选项渲染

### 4.4 Docs_separator.tsx（分割线）
- 示例一：水平三档颜色变体（default / secondary / tertiary）
- 示例二：两端渐隐渐变（`gradient`）
- 示例三：垂直分割线（flex row 中左右分区，含 `self-stretch` 用法）
- 示例四：组合场景（模拟 Modal/Drawer 的 Header-Body 分割线用法）

### 4.5 Docs_table.tsx（表格）
- 示例一：基础数据驱动表格（columns / rows，注意 `minWidth` 与 `defaultWidth` 为必填）
- 示例二：列排序（`allowsSorting` + `sortDescriptor`/`onSortChange` 受控）
- 示例三：行选择（`selectionMode`: single / multiple，回显 `onSelectionChange`）
- 示例四：操作列（`column.render` 插槽渲染 HrsButton）
- 示例五：空态（`renderEmptyState` 自定义）+ 加载态（`isLoading`）
- 示例六：分页（`pagination` 受控模式，`pageNum`/`onPageChange`）

### 4.6 Docs_toast.tsx（轻提示）
- 示例一：5 种视觉变体（`showToast({variant})` 与 `showToast.info/success/warning/danger` 便捷方法）
- 示例二：6 个浮层方位（`placement` 六宫格按钮）
- 示例三：自动关闭时长（默认 3000ms；`duration: 0` 不自动关闭）
- 示例四：`rawMessage` 查看详情展开 + 右侧 `action` 插槽
- 示例五：`dismissToast(id)` / `dismissAllToasts()` 手动关闭
- 说明：全局 `<Toast />` 宿主已挂在 App.tsx，Demo 页直接命令式调用即可，无需额外挂载

### 4.7 Docs_modal.tsx（模态框）
- 示例一：声明式基础用法（`Modal.Header/Heading/Body/Footer` 组织，含默认关闭按钮）
- 示例二：尺寸对比（xs / sm / md / lg / full / cover）
- 示例三：弹出位置（`placement`: top / center / bottom）
- 示例四：遮罩变体（opaque / blur / transparent）+ `isDismissable` 禁遮罩关闭 + `hideCloseButton`
- 示例五：长内容滚动（`scroll`: inside / outside 对比）

### 4.8 Docs_anim_card.tsx（动画卡片）
- 示例一：基础卡片 + `ordinal` 错位入场动画（3 张卡片依次淡入上移）
- 示例二：`variant="gradient"` 渐变边框 + `gradBorderAngle` 角度调节
- 示例三：`gradientBackground` 主题色渐变背景
- 示例四：网格布局组合（grid 容器中混合 default/gradient 卡片）

### 4.9 Docs_news_card.tsx（快讯卡片）
- 示例一：普通快讯列表（页面内构造 mock `LiveNewsItem[]`，含时间/标题/正文/作者）
- 示例二：重要快讯（`showImportant` + `item.important`，红色强调 + 重要标签）
- 示例三：长正文展开/收起（验证 2 行截断与「展开/收起」按钮）
- 说明：`uri` 用 mock 链接，点击整卡会新开原文页（demo 中可给真实墙见闻链接或 `'#'`）

### 4.10 Docs_list_card.tsx（列表卡片）
- 示例一：基础用法（`icon`/`title`/`description`/`count` 徽标）
- 示例二：选中态（`isActive` + `onClick` 单选切换，高亮 + 左侧主题色边）
- 示例三：hover 编辑/删除操作（`onEdit`/`onDelete`，hover 替换计数徽标）
- 示例四：组合列表（3 项列表，结合选中态与操作按钮）

### 4.11 Docs_tab_nav.tsx（标签页）
- 示例一：primary 变体基础用法（受控 `value`/`onChange`，下方内容区随选中切换）
- 示例二：secondary 变体（直角容器 + 主题色指示条）
- 示例三：图标 + 禁用项（`icon` / `disabled`）
- 示例四：`rightSlot` 右侧插槽（放 HrsButton 操作按钮）

### 4.12 Docs_input.tsx（输入框，第二批）
- 示例一：尺寸对比（`size`: xs / sm / md / lg，四档并列静态展示）
- 示例二：受控输入（`useState` + `onChange`，回显当前值，HrsButton 清空）
- 示例三：`type` 变体（text / email / number / search，分别受控）
- 示例四：只读展示与禁用（`value` 无 `onChange` 时组件自动补 `readOnly`，演示纯展示语义；`disabled`）
- 示例五：`placeholder` + `maxLength`（带实时字数回显）
- 示例六：表单组合（Input + HrsButton 搜索模拟，`onKeyDown` Enter 触发 `showToast` 回显）

### 4.13 Docs_textArea.tsx（文本域，第二批）
- 示例一：基础受控用法（`value`/`onChange` 原生写法，实时字数回显）
- 示例二：尺寸对比（`size`: xs / sm / md / lg）
- 示例三：`rows` 可见行数（3 / 5 / 8 对比；注：组件实际默认 rows=5，源码 JSDoc 写「默认 3」与实现不一致，demo 按实际行为演示）
- 示例四：`variant` 对比（primary 带阴影 / secondary 无阴影适配 Surface）
- 示例五：禁用与只读（`disabled`；`value` 无 `onChange` 自动补 `readOnly`）+ `maxLength` 字数回显
- 示例六：表单组合（TextArea + HrsButton 提交，`showToast` 回显内容首行）

### 4.14 Docs_chip.tsx（标签芯片，第二批）
- 示例一：`variant` 四档（primary / secondary / tertiary / soft，同一语义色横向对比）
- 示例二：语义色 `color`（default / accent / success / warning / danger / blue / purple / indigo 共 8 色）
- 示例三：尺寸对比（`size`: xs / sm / md / lg / xl）
- 示例四：`radius` 圆角（full 胶囊 / sm / md / lg）
- 示例五：`onClose` 可关闭标签（受控列表，点击 × 删除项并回显剩余）+ `isDisabled` 禁用态
- 示例六：组合场景（lucide 图标 + 文字 children；模拟筛选器已选条目「标签 + × 取消」）

## 5. 改动文件清单

### 新增（11 个页面文件）

全部位于 `apps/hrs-web/src/pages/DocsPage/Components/`：

```
Docs_drawer.tsx     Docs_button.tsx     Docs_select.tsx   Docs_separator.tsx
Docs_table.tsx      Docs_toast.tsx      Docs_modal.tsx    Docs_anim_card.tsx
Docs_news_card.tsx  Docs_list_card.tsx  Docs_tab_nav.tsx
```

### 修改（4 个既有文件）

| 文件 | 改动内容 |
|------|---------|
| `apps/hrs-web/src/App.tsx` | +11 个 `lazy` import；+11 条 `<Route path="/docs/component/xxx">`（紧随 checkbox 路由之后） |
| `apps/hrs-web/src/components/layout/SidebarNav.tsx` | +11 条 `DEBUG_NAV_ITEMS`；lucide-react 图标 import 追加：`PanelRight`(抽屉)、`MousePointerClick`(按钮)、`ChevronsUpDown`(下拉选择)、`Minus`(分割线)、`Table`(表格)、`BellRing`(轻提示)、`AppWindow`(模态框)、`Sparkles`(动画卡片)、`Newspaper`(快讯卡片，已 import 可复用)、`List`(列表卡片)、`LayoutList`(标签页) |
| `apps/hrs-web/src/i18n/uiText-zh.ts` | +22 个 key（11 × title/description，含中文注释，插入「调试开发模式」区块） |
| `apps/hrs-web/src/i18n/uiText-zh-Hant.ts` | +22 个 key（繁体） |
| `apps/hrs-web/src/i18n/uiText-en.ts` | +22 个 key（英文） |

## 5.1 第二批增量改动清单（Input / TextArea / Chip）

### 新增（3 个页面文件）

全部位于 `apps/hrs-web/src/pages/DocsPage/Components/`：

```
Docs_input.tsx    Docs_textArea.tsx    Docs_chip.tsx
```

### 修改（4 个既有文件，在第一批基础上继续追加）

| 文件 | 改动内容 |
|------|---------|
| `apps/hrs-web/src/App.tsx` | +3 个 `lazy` import；+3 条 `<Route path="/docs/component/input|textArea|chip">`（紧随第一批路由之后） |
| `apps/hrs-web/src/components/layout/SidebarNav.tsx` | +3 条 `DEBUG_NAV_ITEMS`（菜单名：输入框/文本域/标签芯片）；lucide-react 图标 import 追加：`TextCursorInput`(输入框)、`WrapText`(文本域)、`Tags`(标签芯片)（已验证 lucide-react 0.555.0 均存在） |
| `apps/hrs-web/src/i18n/uiText-zh.ts` | +6 个 key（3 × title/description，含中文注释） |
| `apps/hrs-web/src/i18n/uiText-zh-Hant.ts` | +6 个 key（繁体） |
| `apps/hrs-web/src/i18n/uiText-en.ts` | +6 个 key（英文） |

### 本批组件 API 契约要点（调研结论）

- **barrel 导出**：`Input`、`TextArea` 以 `export { X }` 形式导出、`Chip` 以 `export *` 形式导出，3 个组件实例均可用 `import { ... } from '../../../components'` 统一入口；`InputProps` / `TextAreaProps` 类型未从 barrel 导出，但 demo 页按原生受控写法（`onChange={(e) => setX(e.target.value)}`）无需引用组件类型。
- **Input**：继承原生 input 属性全透传；`size` 四档控制高度/字号/圆角；「传 `value` 未传 `onChange`」时组件自动补 `readOnly`（只读展示语义），demo 示例四演示该特性。
- **TextArea**：继承原生 textarea 属性全透传；`size` 四档控制最小高度/字号/圆角；`rows` 默认 5（源码 JSDoc 写 3，与实现不一致，demo 按实际行为演示，不改源码）；`variant` primary/secondary。
- **Chip**：`variant` 四档 × `color` 八色 × `size` 五档 × `radius` 四档；`onClose` 传入时渲染内置 × 按钮（已 stopPropagation）；`isDisabled` 半透明禁用；children 由调用方组合（图标 + 文字）。
- **既有用法参照**：`CodeTestPage.tsx` 已有三组件演示块（TextArea 受控、Chip 关闭受控列表）、`LiveCalendarFilter.tsx` 用 `Input className="w-full pl-7"`、`HrsSelect.tsx` 内部用 `Chip size={size} radius="sm" variant="secondary" onClose` 渲染多选折叠态，demo 页风格与之保持一致。

## 6. 实现要点与约定

- **import 来源**（与组件实际使用方一致）：
  - `Table` 未在 `basic/Index.ts` barrel 导出 → 页面用 `import { Table, type TableColumnDef, ... } from '../../../components/basic/Table'`（与 `WatchlistStockTable.tsx` 一致），**不改 barrel**
  - `ListCard` 未在 `common/Index.ts` barrel 导出 → `import { ListCard } from '../../../components/common/ListCard'`（与 `WatchlistGroupPanel.tsx` 一致），**不改 barrel**
  - 其余 9 个组件均可用 `import { ... } from '../../../components'` 统一入口
- **i18n 硬规则**：三语文件 key 集合必须完全一致（`uiText-zh.ts` 是类型真源），少一个 key 直接编译失败；zh 文件每条 key 带 `// 注释`（对齐现有风格）
- **Toast**：全局宿主已挂载（App.tsx 第 185 行 `<Toast />`），Demo 页只做命令式调用，不重复挂载宿主
- **NewsCard**：`LiveNewsItem` mock 数据在页面内本地构造（含 `id/title/content/displayTime/score/important/channels/uri/author` 全部字段），不请求接口
- **Table**：`TableColumnDef` 的 `minWidth`（number）与 `defaultWidth`（string|number）为必填，Demo 列定义必须提供
- **页面风格**：统一沿用 Docs_checkbox 的 section 样式（`rounded-lg border border-border/70 bg-card/75 p-6`）、标题层级（h1/h2/p）、`useUiLanguage().t()` 取标题
- **注释规范**：文件头 `@fileoverview` 注明组件、路由地址、菜单名（对齐 Docs_checkbox 头注释格式）

## 7. 验证方案

1. 类型与构建：`cd apps/hrs-web && npm run lint && npm run build`（build 含 `tsc -b`，可暴露 i18n key 缺失、icon 不存在、类型错误）
2. 人工走查：`npm run dev` 启动后切换开发调试模式，验证：
   - 侧边栏出现 11 个新菜单项，点击可正常跳转对应路由
   - 每个页面各示例区块交互正常（弹窗/抽屉/Toast 弹出、表格排序选页、卡片动画）
   - 切换三语（zh / zh-Hant / en），菜单名与页面标题正确联动
3. 交付说明：按 AGENTS.md 验证矩阵输出「改了什么 / 为什么 / 验证情况 / 未验证项 / 风险点 / 回滚方式」

## 8. 风险与注意事项

- **风险 1（中）**：11 个页面 × 4 个挂载点改动面较大，App.tsx / SidebarNav / 三语文件均为并发改动热点，容易产生 merge 冲突；建议一次提交完成，review 时按挂载点核对
- **风险 2（低）**：Debug 菜单在普通产品模式下不显示，Demo 页仅开发调试模式可达；不影响线上用户可见面
- **风险 3（低）**：HeroUI 弹层类组件（Modal/Drawer/Toast/Select 弹层）在 Demo 页嵌套使用时需避免触发器嵌套导致的焦点/事件冲突，页面设计已规避（各示例独立按钮触发）
- **风险 4（低，本批）**：TextArea 源码 JSDoc 写「rows 默认 3」但实现默认 5，demo 页按实际行为演示；是否顺手修正该注释待评审确认（默认不改，遵循最小改动原则）
- **回滚方式**：纯前端新增 + 少量挂载点追加，无数据库/接口变更；回滚即删除新增文件并还原挂载文件（git revert）
- **CHANGELOG**：第一批已追加 `- [文档] 新增 11 个组件文档 Demo 页（/docs/component/*）` 条目；本批建议在 `docs/CHANGELOG.md` `[Unreleased]` 再追加一条 `- [文档] 新增 Input / TextArea / Chip 三个组件文档 Demo 页（/docs/component/input|textArea|chip）`，是否更新由评审确认

## 9. 待评审确认点

第一批已实施。本批评审点：

1. 菜单名称（第 3 节第二批表格）是否符合预期（Input → 输入框、TextArea → 文本域、Chip → 标签芯片）
2. TextArea 路由与文件名的 camelCase 命名（`/docs/component/textArea` + `Docs_textArea.tsx`）是否符合多词组件约定
3. 各页面示例区块划分（第 4.12~4.14 节）是否需要增删
4. 是否同步更新 `docs/CHANGELOG.md`（本批条目）
5. TextArea 源码 `rows` 默认值注释与实现不一致（JSDoc 写 3、代码为 5），是否顺手修正注释
