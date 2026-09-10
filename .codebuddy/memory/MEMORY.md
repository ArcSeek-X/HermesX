# 长期记忆（MEMORY.md）

## 用户偏好
- **代码注释风格**：偏好精简。删除「修改过程产物」类注释（如"已移除 XX""已移到 XX 文件""原先的 XX 联动已移除"）、与代码自明/彼此重复的冗余说明；保留有价值的 why（设计取舍、踩坑原因）与简短步骤标记（如 `// 1) 收集...`）。
- 注释语言：中英文混合项目中，中文注释做概述级补充，原有英文 docstring 原样保留。

- **避免过度封装（组件粒度）**：简单 UI 不要单独封装成组件塞进 `components/` 目录。判断标准：只是用基础组件（如 `HrsButton`）拼几个图标/文案/角标、没有独立状态与复用场景的，直接在使用它的页面里内联实现即可。例：消息日历的「筛选按钮」原封装为 `LiveCalendarFilterButton`（放在 `components/common/LiveCalendar/LiveCalendarFilter.tsx`），用户要求撤掉，改为在 `LiveCalendarPage.tsx` 直接用 `HrsButton` + lucide 图标 + `cn` 渲染，页面只保留筛选区域面板 `LiveCalendarFilterPanel`。

## 项目约定（hrs-web）
- **类型检查必须用 `npx tsc -p tsconfig.app.json --noEmit`**：根 `tsconfig.json` 是 solution 风格（`files:[]` + `references`），`tsc -p tsconfig.json` **什么都不校验**，会给出"无报错"的假象。仓库当前有大量存量错误（`@testing-library/react` 缺 `screen`/`fireEvent` 导出、HrsButton forwardRef、Pagination `xs`、PasswordInput `prefixNode` 等），校验自己改动时要按文件名过滤，别被存量错误淹没。
- **全局跨子树状态放 `contexts/` 并挂到 `App.tsx`**：头部与侧边栏是兄弟子树，需要共享状态时（如运行模式）必须在共同祖先提供 Provider。Provider 一律提供降级值（`useContext(...) ?? fallback`），保证单测不包 Provider 也能渲染。
- **抽屉组件**：统一用 `components/basic/Drawer.tsx`（HrsDrawer，HeroUI 底座）；`components/common/Drawer.tsx` 为旧版，新代码不用。
- **消息日历点击语义**：点消息 = 打开 `LiveCalendarEventDrawer` 详情抽屉（不切视图）；点日期格空白 / 日期标题 = 切到日视图看当天全部。两条路径刻意分开。
- **i18n 命名空间**：日历相关文案为 `component.LiveCalendar.*`（非 `liveCalendar.*`）；新增 key 需 zh / zh-Hant / en 三语同时补齐（`UiTextKey` 由 uiText-zh.ts 推导）。
- **消息日历筛选**：四个条件（重要度 / 类型 FE·FD / 国家 / 关键词）一律走**客户端过滤**（整月数据已在内存），在 `useLiveCalendarMonths` 的 `events` useMemo 内完成，不新增请求；与 `includeEconomicData`（后端开关，会触发重拉）是两套东西，勿混用。UI 上草稿与生效值分离，点「确认」才提交，输入过程不触发日历重算。
- **消息日历筛选重置必须返回新对象**：`LiveCalendarFilterPanel` 用引用比较（`value !== syncedValue`）把草稿拉回已生效值，因此重置/初始化默认值一律用 `createDefaultLiveCalendarFilter()`（每次新对象），不要用共享常量 `DEFAULT_LIVE_CALENDAR_FILTER`，否则「同引用 → 判定无变化 → 点了重置面板不变」。
- **国家下拉**：按中文名拼音首字母 A-Z 分组用 `pinyin-pro`（`pattern:'first'`、`toneType:'none'`、`type:'array'`），国旗取 `CalendarCountryDef.flagUri`，`HrsSelect` 分组靠数据结构（含 `options` 数组的项即识别为分组），自定义选项内容走 `renderItem`。
- **日期时间格式化**：一律复用 `utils/format.ts` 的 `formatDate` / `formatDateTime` / `formatTime`（接受秒级时间戳，内部自动 ×1000，输出固定 zh-CN 数字格式），**不要**在组件里手写 `new Date(ts*1000)` + `Intl.DateTimeFormat`。需要随 UI 语言本地化的（星期 / 月份长格式）用 `toIntlLocale(language)`——全站唯一的 locale 映射，勿在各组件重复写 zh-CN / zh-TW / en-US 三元判断。
- **新增侧边导航菜单项**：导航项由 `components/layout/SidebarNav.tsx` 的 `NAV_ITEMS` 数组驱动（顺序即菜单顺序）。新增项需在 `NAV_ITEMS` 加 `{ key, labelKey, to, icon }`，并在 `lucide-react` import 行补图标；同时必须在 `App.tsx` 顶部 `lazy` 注册页面 + `<Routes>` 加 `<Route path=... element=...>`；文案 key（`layout.nav.<x>.title` / `.description`）必须 zh / zh-Hant / en 三语同时补齐（`UiTextKey` 由 uiText-zh.ts 推导，缺任一即类型报错）。若需像「选股」那样受开关控制显隐，再在 `navItems` 过滤逻辑处理。
- **组件文档页约定**：组件演示/文档页统一放在 `apps/hrs-web/src/pages/DocsPage/Components/`，文件命名 `Docs_<组件名>.tsx`（首个文档页为 `Docs_checkbox.tsx`，路由 `/docs/component/checkbox`，菜单名「复选框」）；页面用 `<AppPage>` 包裹，演示内容参考 `CodeTestPage.tsx` 的 `HrsCheckbox` 区块风格，从 `../../../components` 与 `../../../contexts/UiLanguageContext` 引入。
- **基础组件目录规范**：`components/basic/` 下的组件统一采用「文件夹 + index.ts」结构（参照 HrsButton）：`<Name>/<Name>.tsx` 放实现，`<Name>/index.ts` 用 `export * from './<Name>'` 再导出（有默认导出的组件如 Chip 额外 `export { default } from './<Name>'`）。将既有平铺 `basic/X.tsx` 迁移为文件夹时，组件内部相对 import 因多一层目录要多加 `../`（`../../utils/cn` → `../../../utils/cn`，同层 `./Separator` → `../Separator`）；`basic/Index.ts` 用目录级导出（`./X` 不带文件名），迁移后无需改动，调用方用 `'../basic/X'` 或 `'../components'` 均无缝解析。
