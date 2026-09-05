/**
 * csscover.ts
 * ------------------------------------------------------------
 * LiveCalendar（FullCalendar v6 二次封装）的**样式覆盖层**：从 `LiveCalendar.tsx`
 * 的容器 `cn(...)` 中独立出来的 Tailwind 类名清单。
 *
 * 为什么单独成文件：这一层是「一段一条注释」的契约式样式配置（约 300 条类名 +
 * 每条对应的 v6 默认值与踩坑说明），与组件的渲染/交互逻辑正交。放在组件文件里会
 * 让 LiveCalendar.tsx 的视觉细节淹没数据流与事件处理逻辑，故按语义拆到本文件，
 * 组件侧只保留一次引用：`cn(LIVE_CALENDAR_CSS_COVER, className)`。
 *
 * 为什么不新建 CSS/SCSS：仓库规范（AGENTS.md + docs/Live-calendar.md §9.6）要求
 * 日历样式以「Tailwind 令牌 + FullCalendar 的 `--fc-*` 变量层」为唯一来源，不落
 * 任何自定义样式文件，主题取色全部经变量继承完成。
 *
 * ⚠ 维护约定（改这个文件前必读）：
 * 1. **顺序即优先级**。`cn()` = `twMerge(clsx(...))`，同类目冲突时**后写的赢**。
 *    因此分节顺序与节内条目顺序都不可随意调整，也不要在组件侧把本常量放到
 *    `className` 之后（那会让外部覆盖失效）。
 * 2. **每条必须是完整字面量**。Tailwind v4 按静态文本扫描 `content` 声明的路径
 *    （本项目为 tailwind.config.js 里 `./src` 下的全部 .js/.ts/.jsx/.tsx 文件），
 *    运行时拼接的类名片段（如 `` `[&_.fc-` + x + `]:p-0` ``）不会被生成，
 *    表现是「类名在 DOM 上但样式没生效」。
 * 3. **末尾 `!` 不能省**。FullCalendar v6 运行时把 `<style data-fullcalendar>`
 *    以 unlayered 方式插到 `<head>` 最前，而 Tailwind utilities 在 `@layer` 内；
 *    CSS 层叠层优先级高于特异性，普通声明会被无条件压过，必须用 `!important` 兜住。
 *    唯独 `[--fc-*]` 变量例外——变量沿 DOM 继承、不参与层叠竞争，故可不带 `!`。
 * 4. 注释里写的「v6 默认值」是对照 `@fullcalendar/*` 源码得到的，改样式时请连同
 *    默认值一起更新，避免注释与实现漂移。
 */

// ── 容器基础 ──────────────────────────────────────────────────────────────
// 高度策略：不使用 h-full / height="100%"。调用方（LiveCalendarPage）给的是
// `min-h-[480px] flex-1` 的 flex item，其高度是 flex 布局算出的 auto 语义，
// 子元素任何 `height: 100%` 都解析不出确定值，会把 wrapper 与整个日历压成 0。
// 因此高度交给 FullCalendar 的 aspectRatio 自撑开（见组件内配置）。
const BASE = [
    // 容器：占满可用宽度，字号继承页面。
    'hrs-calendar-Live w-full [&_.fc]:text-sm!',
];

// ── FullCalendar 主题变量层 ───────────────────────────────────────────────
// 整层用 FullCalendar 自带的 `--fc-*` CSS 变量接管取色（变量值经 DOM 继承，
// 不受上面层叠层问题影响）。其余 Tailwind 规则只负责「形状/间距/字号」，
// 取色全部委托给这里。每个变量都对照 v6 源码默认值说明。
const THEME_VARS = [
    // 网格线色：v6 默认 `--fc-border-color` 偏深且无透明；换成设计令牌
    // `--border`（217 28% 84%）再压到 0.6 透明，白底上呈浅蓝灰、清晰又不抢眼。
    // 切忌用 `--border-dim-raw`（= foreground / 0.05–0.08），那种深色低透明在浅底上
    // 几乎隐形，会让人误以为整张日历没渲染（踩过坑）。
    '[--fc-border-color:hsl(var(--border)_/_0.6)]',
    // 页面整体背景：v6 默认白色；设透明，交给卡片 bg-elevated。
    '[--fc-page-bg-color:transparent]',
    // 中性背景（hover/禁用等态）：v6 默认灰；设 muted 40% 透明，弱对比。
    '[--fc-neutral-bg-color:hsl(var(--muted)_/_0.4)]',
    // 中性文字色：v6 默认中灰；对齐 muted-foreground。
    '[--fc-neutral-text-color:hsl(var(--muted-foreground))]',
    // 今日整格底色：v6 默认浅黄 `--fc-today-bg-color`；设透明，「今日」语义改由
    // dayCellContent 画的主题色 pill 表达，整格不铺色更干净。
    '[--fc-today-bg-color:transparent]',
    // 事件锚点的底色/边框：v6 默认跟随 --fc-event-bg-color（主题色实色）；
    // 全部透明，视觉交给 CalendarEventContent 自定义渲染。
    '[--fc-event-bg-color:transparent]',
    '[--fc-event-border-color:transparent]',
    // 事件文字色：v6 默认浅色（在主题色底上）；设 foreground，配合透明底由我们控制对比。
    '[--fc-event-text-color:hsl(var(--foreground))]',
    // 事件被点选时的遮罩色：v6 默认淡主题色；设 primary 12% 透明。
    '[--fc-event-selected-overlay-color:hsl(var(--primary)_/_0.12)]',
    // 小字号（事件时间/周次等用）：覆盖 v6 默认的 .85em，当前设为 text-lg。
    '[--fc-small-font-size:text-lg!]',
    // 月视图事件左侧圆点宽度：v6 默认 8px；设 6px。
    // 注：色点目前用 `·` 字符渲染（见 CalendarEventContent），该变量仅作兜底。
    '[--fc-daygrid-event-dot-width:6px]',
];

// ── 工具栏按钮变量 ─────────────────────────────────────────────────────────
// v6 按钮默认「描边实心」风（--fc-button-bg-color 主题色实色）。先在这里用变量
// 把按钮取色调成「白底描边 + 选中浅灰」，下面的 Tailwind 规则再补形状/字号。
const BUTTON_VARS = [
    // 按钮文字色：v6 默认白（在实色底上）；设 foreground，配合白底。
    '[--fc-button-text-color:hsl(var(--foreground))]',
    // 按钮底色：v6 默认主题色实色；设 background（白底），改成描边风。
    '[--fc-button-bg-color:hsl(var(--background))]',
    // 按钮边框色：v6 默认主题色；设 border-dim-raw 12% 透明，弱描边。
    '[--fc-button-border-color:hsl(var(--border-dim-raw)_/_0.12)]',
    // 按钮 hover 底色：v6 默认加深主题色；设 hover 令牌（浅灰）。
    '[--fc-button-hover-bg-color:hsl(var(--hover))]',
    // 按钮 hover 边框：同边框色。
    '[--fc-button-hover-border-color:hsl(var(--border-dim-raw)_/_0.12)]',
    // 按钮选中态底色：v6 默认主题色实色；设 muted（浅灰）。
    // 注：--muted = 214 30% 94%，与白底差异仅 6%，对比很弱、几乎看不见；
    // 若要更明显，可换 var(--primary)/0.12（浅青）或 var(--hover)/var(--border)。
    '[--fc-button-active-bg-color:hsl(var(--muted))]',
    // 按钮选中态边框：同边框色。
    '[--fc-button-active-border-color:hsl(var(--border-dim-raw)_/_0.12)]',
];

// ── 网格框架 ───────────────────────────────────────────────────────────────
// FullCalendar 的滚动容器是 `.fc-scrollgrid`（包着表头 + body 两张表）。
// v6 默认给它 `border: 1px solid var(--fc-border-color)` 的外框，会让最外圈
// 出现一圈双边框。这里去掉外框，只保留单元格之间的网格线。
// ⚠ 切勿覆盖 `border-collapse`/`border-spacing`：v6 scrollgrid 依赖
// `border-collapse: separate` + `border-spacing` 来计算 body 行高，改 collapse
// 会让行高算成 0、整张日历塌成空白（踩过坑）。
const SCROLLGRID = [
    // 去掉滚动容器外框（v6 默认 1px solid var(--fc-border-color)）。
    '[&_.fc-scrollgrid]:border-0!',
    // 单元格边框：v6 默认 `.fc-theme-standard td/th { border: 1px solid var(--fc-border-color) }`
    // 四周都画。这里保留——它正是单元格之间的网格线；颜色走上面的 --fc-border-color 变量。
    // 用 `border-(--fc-border-color)` 直接引用变量，确保与变量层改过的颜色一致。
    '[&_.fc-theme-standard_td]:border-(--fc-border-color)!',
    '[&_.fc-theme-standard_th]:border-(--fc-border-color)!',
];

// ── 表头（星期行）──────────────────────────────────────────────────────────
// v6 表头结构：`.fc-col-header`（表）→ `.fc-col-header-cell`（每个 th）→
// 内层 `.fc-scrollgrid-sync-inner` → `a.fc-col-header-cell-cushion`（文字）。
const COL_HEADER = [
    // 表头整体背景透明（卡片已铺底色，不重复）。
    '[&_.fc-col-header]:bg-transparent!',
    // 每个 th 去掉左右/上边框：v6 默认 th 四周有 border（来自 .fc-theme-standard th），
    // 保留下边框即可（见网格框架段），左右/上边框去掉避免重复线。
    '[&_.fc-col-header-cell]:border-x-0!',
    '[&_.fc-col-header-cell]:border-t-0!',
    // th 背景透明，上下内距给到 py-2（v6 默认靠 cushion 的 padding 撑开，这里统一由 th 控制）。
    '[&_.fc-col-header-cell]:bg-transparent!',
    '[&_.fc-col-header-cell]:px-0!',
    '[&_.fc-col-header-cell]:py-2!',
    // 星期文字垂直居中（v6 默认 baseline）、加 medium 字重。
    '[&_.fc-col-header-cell]:align-middle!',
    '[&_.fc-col-header-cell]:font-medium!',
    // cushion 是 v6 包裹星期文字的内联元素：默认 `display:inline-block; padding:2px 4px`。
    // 改成 block + p-0，padding 交给上层 th 控制；文字居中。
    '[&_.fc-col-header-cell_cushion]:block!',
    '[&_.fc-col-header-cell_cushion]:p-0!',
    '[&_.fc-col-header-cell_cushion]:text-center!',
    // 同步层内层容器：去 padding（v6 默认也有内距），让 th 的 py-2 统一生效。
    '[&_.fc-scrollgrid-sync-inner]:p-0!',
];

// ── 日期格 ─────────────────────────────────────────────────────────────────
// 每个日期格结构：`.fc-daygrid-day`（td）→ `.fc-daygrid-day-frame`（撑高）→
// `.fc-daygrid-day-top`（日期数字行）→ `a.fc-daygrid-day-number`（数字）→
// `.fc-daygrid-day-events`（事件区）→ `.fc-daygrid-day-bottom`（「+N」更多）。
const DAY_CELL = [
    // td 内距清零（v6 默认 padding 由主题给），统一交由内部元素控制。
    // ⚠ frame 的 `min-height:100%` 保留 v6 默认（占满 td），不要设为 0，否则整格塌缩。
    '[&_.fc-daygrid-day]:p-0!',
    // 日期数字行：v6 默认 `.fc-daygrid-day-top { display:flex; flex-direction:row-reverse;
    // padding:... }`——即日期数字**靠右**。改为靠左（row 正向）、垂直居中、左对齐，
    // 与 dayCellContent 画的圆点在同一行。内距归零后由 ps-1/pt-1.5 单独给左上间距。
    '[&_.fc-daygrid-day-top]:m-0!',
    '[&_.fc-daygrid-day-top]:flex-row!',
    '[&_.fc-daygrid-day-top]:items-center!',
    '[&_.fc-daygrid-day-top]:justify-start!',
    '[&_.fc-daygrid-day-top]:p-0!',
    '[&_.fc-daygrid-day-top]:ps-1!',
    '[&_.fc-daygrid-day-top]:py-1.5!',
    // 日期数字本身：v6 默认 `a.fc-daygrid-day-number { padding:4px }` 且带下划线样式。
    // 去 padding、去掉下划线。
    '[&_.fc-daygrid-day-number]:p-1!',
    // 月视图下所有日期数字统一：弱化前景色 + semibold + 斜体。
    // 范围只命中 dayGridMonth（`.fc-daygrid-day-number`），不影响周/日视图。
    '[&_.fc-daygrid-day-number]:text-foreground-soft!',
    '[&_.fc-daygrid-day-number]:font‑semibold!',
    '[&_.fc-daygrid-day-number]:italic!',
    '[&_.fc-daygrid-day-number]:no-underline!',
    // 今日日期数字：主题色 + 加粗 + 不斜体（更醒目，区别于其他日期）。
    // 选择器 specificity 高于上面的单类规则，覆盖 text/italic。
    '[&_.fc-day-today_.fc-daygrid-day-number]:text-primary!',
    '[&_.fc-day-today_.fc-daygrid-day-number]:font-bold!',
     '[&_.fc-day-today_.fc-daygrid-day-number]:text-md!',
    // 非本月日期：v6 默认 `.fc-day-other .fc-daygrid-day-top { opacity:.3 }` 把整行
    // （含日期数字）压暗。这里改 opacity-100，由日期数字自身色表达非本月概念，
    // 整格仍保持正常亮度。
    '[&_.fc-day-other_.fc-daygrid-day-top]:opacity-100!',
    // 事件区：v6 默认 `margin-top:1px` 等。去外边距、加左上内距，让事件块与日期数字、
    // 底部「+N」有呼吸感，且左右与日期圆点对齐（px-1）。
    '[&_.fc-daygrid-day-events]:my-1!',
    '[&_.fc-daygrid-day-events]:ml-1!',
    '[&_.fc-daygrid-day-events]:mr-2!',
];

// ── 事件锚点（月视图）──────────────────────────────────────────────────────
// v6 月视图事件是一个 `<a class="fc-daygrid-event fc-h-event">`，内部由
// `.fc-event-main` → `.fc-event-main-frame` → `.fc-event-title-container` /
// `.fc-event-time` 组成。全部视觉（色块、圆点、文字）由 CalendarEventContent
// 渲染，所以这里把 v6 自带的锚点样式全部清空，只留一个透明占位。
const EVENT_ANCHOR = [
    // 锚点整体：v6 默认 `margin-top:1px; border-radius:3px; font-size:...; white-space:nowrap`
    // 且 `.fc-h-event { background-color:var(--fc-event-bg-color); border:1px solid... }`。
    // 清掉外边距（改由 mb-px/ms-me 微调）、边框、背景、padding、阴影。
    '[&_.fc-daygrid-event]:m-0!',
    '[&_.fc-daygrid-event]:mb-px!',
    '[&_.fc-daygrid-event]:ms-0.5!',
    '[&_.fc-daygrid-event]:me-0.5!',
    '[&_.fc-daygrid-event]:border-0!',
    '[&_.fc-daygrid-event]:bg-transparent!',
    '[&_.fc-daygrid-event]:p-0!',
    '[&_.fc-daygrid-event]:shadow-none!',
    // v6 默认给 `.fc-daygrid-event { white-space:nowrap }`，会继承给自定义 eventContent。
    // 必须显式覆盖为 normal，否则标题里的换行类无法生效，长标题仍会被截成单行省略。
    '[&_.fc-daygrid-event]:whitespace-normal!',
    // hover：v6 给 `.fc-daygrid-dot-event:hover { background:... }`（仅 dot 事件）；
    // 月视图是 block 事件无 hover 背景。这里显式 bg-transparent 兜底，避免任何残留底色。
    '[&_.fc-daygrid-event:hover]:bg-transparent!',
    // 键盘聚焦：去掉 v6 默认 outline，改由我们渲染的色块表达选中。
    '[&_.fc-daygrid-event]:focus-visible:outline-none!',
    // 内部容器：`.fc-event-main` / `.fc-event-main-frame` v6 默认带 position/z-index 但无
    // padding；`.fc-h-event .fc-event-title-container { flex-grow:1 }`。全部 p-0 透明。
    '[&_.fc-event-main]:p-0!',
    '[&_.fc-event-main]:bg-transparent!',
    '[&_.fc-event-main]:whitespace-normal!',
    '[&_.fc-event-main-frame]:p-0!',
    // 隐藏 v6 自带的标题/时间容器：我们已在 CalendarEventContent 里自定义渲染，留着会重复显示。
    '[&_.fc-event-title-container]:hidden!',
    '[&_.fc-event-time]:hidden!',
];

// ── 时间网格事件（周 / 日视图）─────────────────────────────────────────────
// 范围只命中 fc-timegrid-*，对月视图（fc-daygrid-*）零影响。
// 解决两件事：
// 1) 允许事件块内容换行（v6 默认 .fc-timegrid-event 继承 white-space:nowrap，
//    导致自定义 eventContent 里加的 break-words/whitespace-normal 形同失效）；
// 2) 给短事件一个最小高度，并让 event harness 跟着撑开，
//    避免 duration < 1 槽的事件被 FC 按内联高度截断成一截。
const TIMEGRID_EVENT = [
    '[&_.fc-timegrid-event]:whitespace-normal!',
    '[&_.fc-timegrid-event]:min-h-9!',
    '[&_.fc-timegrid-event-harness]:min-h-9!',
    '[&_.fc-timegrid-event-main]:whitespace-normal!',
    '[&_.fc-timegrid-event-main-frame]:whitespace-normal!',
];

// ── 周次标签（showWeekNumbers 开启时生效）──────────────────────────────────
const WEEK_NUMBER = [
    // v6 默认 `.fc-daygrid-week-number` 是 `position:absolute; top:0; left:0;
    // background:var(--fc-neutral-bg-color); color:var(--fc-neutral-text-color);
    // min-width:1.5em; padding:2px; text-align:center; border-radius:0 0 3px 0`——
    // 即绝对定位在每格左上角的小角标，每格都有、并不好看。
    // 这里改造成「左侧固定一列」的周次栏：用 inline-flex 让它占据布局流、纵向居中、
    // 内容居中、右下圆角；右侧/下边框与网格线衔接；背景 muted 40% 弱区分。
    '[&_.fc-daygrid-week-number]:inline-flex!',
    '[&_.fc-daygrid-week-number]:min-w-[34px]!',
    '[&_.fc-daygrid-week-number]:items-center!',
    '[&_.fc-daygrid-week-number]:justify-center!',
    // 右下圆角（v6 默认只圆右下），与格子衔接更自然。
    '[&_.fc-daygrid-week-number]:rounded-ee-md!',
    // 右/下边框：与网格线呼应（颜色走 --fc-border-color 变量）。
    '[&_.fc-daygrid-week-number]:border-e!',
    '[&_.fc-daygrid-week-number]:border-b!',
    '[&_.fc-daygrid-week-number]:border-(--fc-border-color)!',
    // 背景 muted 40% 透明（弱区分）；文字 muted-foreground。
    '[&_.fc-daygrid-week-number]:bg-muted/40!',
    '[&_.fc-daygrid-week-number]:px-1.5!',
    '[&_.fc-daygrid-week-number]:py-0.5!',
    // 字号 11px（比正文小一号），medium 字重。
    '[&_.fc-daygrid-week-number]:text-[11px]!',
    '[&_.fc-daygrid-week-number]:font-medium!',
    '[&_.fc-daygrid-week-number]:text-muted-foreground!',
    // 去掉 v6 默认的下划线样式。
    '[&_.fc-daygrid-week-number]:no-underline!',
];

// ── 折叠浮层（点「+N」弹出 .fc-more-popover）───────────────────────────────
// v6 浮层结构：`.fc-popover` → `.fc-popover-header`（标题 + 关闭按钮）
// → `.fc-popover-body`（事件列表）。v6 默认浮层是白底圆角但细节较朴素，
// 这里对齐项目令牌（elevated 底 + border-dim 描边 + soft-card 阴影）。
const POPOVER = [
    // 浮层卡片：去默认溢出、圆角、描边、底色、阴影。
    '[&_.fc-popover]:overflow-hidden!',
    '[&_.fc-popover]:rounded-lg!',
    '[&_.fc-popover]:border!',
    '[&_.fc-popover]:border-border-dim!',
    '[&_.fc-popover]:bg-elevated!',
    '[&_.fc-popover]:shadow-soft-card!',
    // 浮层头部：v6 默认无 flex 布局，标题与关闭按钮挤在一起。改为 flex 两端对齐。
    '[&_.fc-popover-header]:flex!',
    '[&_.fc-popover-header]:items-center!',
    '[&_.fc-popover-header]:justify-between!',
    // 头部背景透明（不让 v6 默认浅色条盖住卡片底色），给内距。
    '[&_.fc-popover-header]:bg-transparent!',
    '[&_.fc-popover-header]:px-3!',
    '[&_.fc-popover-header]:py-2!',
    // 标题：xs 字号、semibold、前景色（v6 默认稍大且普通色）。
    '[&_.fc-popover-title]:text-xs!',
    '[&_.fc-popover-title]:font-semibold!',
    '[&_.fc-popover-title]:text-foreground!',
    // 关闭按钮：v6 默认是一个小 ✕，无定宽无居中。改成 6×6 正方形、flex 居中、圆角、
    // muted 文字色、hover 浅灰底。
    '[&_.fc-popover-close]:inline-flex!',
    '[&_.fc-popover-close]:size-6!',
    '[&_.fc-popover-close]:items-center!',
    '[&_.fc-popover-close]:justify-center!',
    '[&_.fc-popover-close]:rounded-md!',
    '[&_.fc-popover-close]:text-muted-foreground!',
    '[&_.fc-popover-close:hover]:bg-hover!',
    // 浮层 body（事件列表容器）：v6 默认 `min-width:220px; padding:10px`。
    // 只调内距（p-2），其余交事件项自身样式。
    '[&_.fc-more-popover_.fc-popover-body]:p-2!',
    // 浮层 body 内的日期数字 pill（dayCellContent 被 popover 复用渲染到
    // .fc-more-popover-misc 里）：隐藏它，只保留 fc-popover-header 的完整日期标题。
    '[&_.fc-more-popover-misc_.hrs-day-number]:hidden!',
];

// ── 工具栏（prev/today/next + title + 视图切换器）──────────────────────────
// v6 工具栏 `.fc-toolbar`（`.fc-header-toolbar`）默认 `display:flex;
// justify-content:space-between; align-items:center`，三栏左/中/右。
// 这里补 padding 与下边距分隔日历主体；导航按钮（前/今天/后）做成「相邻拼接」胶囊，
// 视图切换器（月/周/日）做成三个独立纯文字标签（选中项浅灰/主题色圆角底 + 加粗）。
const TOOLBAR = [
    // 工具栏整体：flex + 允许换行（窄屏不挤）+ 垂直居中 + 两端对齐 + 间距。
    '[&_.fc-toolbar]:flex!',
    '[&_.fc-toolbar]:flex-wrap!',
    '[&_.fc-toolbar]:items-center!',
    '[&_.fc-toolbar]:justify-between!',
    '[&_.fc-toolbar]:gap-3!',
    '[&_.fc-toolbar]:px-4!',
    '[&_.fc-toolbar]:py-3!',
    // 头部工具栏下边距：v6 默认 `margin-bottom:1.5em`，会撑出多余留白；清零。
    '[&_.fc-header-toolbar]:mb-0!',
    // 标题（当前年/月/周）：v6 默认 `font-size:1.75em`（偏大）；改 text-base + semibold + 前景色。
    '[&_.fc-toolbar-title]:text-base!',
    '[&_.fc-toolbar-title]:font-semibold!',
    '[&_.fc-toolbar-title]:text-foreground!',
];

// ── 按钮通用（导航三钮 + 视图切换器共用）───────────────────────────────────
const BUTTON = [
    // v6 默认 `.fc .fc-button { font-size:1em; padding:.4em .65em; line-height:1.5;
    // border-radius:.25em }`，在 14px 基准下偏大。统一收到 text-sm 并压紧内距/行高，
    // 圆角改 md。hover 浅灰底（变量层已设 --fc-button-hover-bg-color，这里兜底透明 hover）。
    '[&_.fc-button]:rounded-sm!',
    '[&_.fc-button]:text-sm!',
    '[&_.fc-button]:px-2!',
    '[&_.fc-button]:h-8!',
    '[&_.fc-button]:leading-tight!',
    '[&_.fc-button:hover]:text-foreground!',
    '[&_.fc-button:hover]:font-semibold!',
    // 选中态（.fc-button-active）阴影：v6 默认给 `.fc-button-primary.fc-button-active`
    // 一层投影；去掉，保持扁平（选中表达交给背景色）。
    '[&_.fc-button-primary.fc-button-active]:shadow-none!',
];

// ── 导航按钮（前 ‹ / 今天 / 后 ›）──────────────────────────────────────────
// 目标：三个按钮合并成一个圆角胶囊，中间没有边框分隔，像一个整体按钮。
// 做法：把边框/圆角/阴影全部上移到 .fc-button-group 容器，内部三个按钮只负责
// 背景、文字和图标色，彼此 border-0、rounded-none。
const NAV_BUTTON = [
    '[&_:is(.fc-prev-button,.fc-today-button,.fc-next-button)]:bg-transparent!',
    '[&_:is(.fc-prev-button,.fc-today-button,.fc-next-button)]:border-0!',
    '[&_:is(.fc-prev-button,.fc-today-button,.fc-next-button)]:shadow-none!',
    '[&_:is(.fc-prev-button,.fc-today-button,.fc-next-button)]:font-normal!',
    '[&_:is(.fc-prev-button,.fc-today-button,.fc-next-button)]:text-foreground-soft!',
    // 导航按钮组内三个按钮统一 inline-flex + 垂直/水平居中，保证左右箭头与「今天」文字对齐。
    '[&_:is(.fc-prev-button,.fc-today-button,.fc-next-button)]:inline-flex!',
    '[&_:is(.fc-prev-button,.fc-today-button,.fc-next-button)]:items-center!',
    '[&_:is(.fc-prev-button,.fc-today-button,.fc-next-button)]:justify-center!',
    // 中间「今天」文字作为胶囊的视觉主体：前景色 + medium 字重，区分于两侧箭头。
    '[&_:is(.fc-today-button)]:text-foreground!',
    '[&_:is(.fc-today-button)]:font-medium!',
    // 左右箭头图标：弱化色 + 行高收紧；hover 时变为前景色 + semibold。
    '[&_.fc-prev-button_.fc-icon,&_.fc-next-button_.fc-icon]:text-sm!',
    '[&_.fc-prev-button_.fc-icon,&_.fc-next-button_.fc-icon]:text-foreground-soft!',
    '[&_.fc-prev-button_.fc-icon,&_.fc-next-button_.fc-icon]:leading-none!',
    '[&_.fc-prev-button:hover_.fc-icon,&_.fc-next-button:hover_.fc-icon,.fc-today-button:hover]:text-foreground!',
    '[&_.fc-prev-button:hover_.fc-icon,&_.fc-next-button:hover_.fc-icon,.fc-today-button:hover]:font-semibold!',
    '[&_.fc-prev-button:hover]:font-normal!',
    '[&_.fc-next-button:hover]:font-normal!',
];

// ── 视图切换器（月 / 周 / 日）──────────────────────────────────────────────
// v6 把这三个按钮放同一个 buttonGroup，但我们想做成「独立纯文字标签」，于是去掉
// 边框/底色/阴影，改由 mx-1 自带间距（group 不再负责拼接）。未选中态用弱前景色
// + 常规字重，选中态（见下）用背景色 + 加粗 + 前景色。
const VIEW_SWITCHER = [
    '[&_:is(.fc-dayGridMonth-button,.fc-timeGridWeek-button,.fc-timeGridDay-button)]:border-0!',
    '[&_:is(.fc-dayGridMonth-button,.fc-timeGridWeek-button,.fc-timeGridDay-button)]:bg-transparent!',
    '[&_:is(.fc-dayGridMonth-button,.fc-timeGridWeek-button,.fc-timeGridDay-button)]:shadow-none!',
    '[&_:is(.fc-dayGridMonth-button,.fc-timeGridWeek-button,.fc-timeGridDay-button)]:px-2!',
    '[&_:is(.fc-dayGridMonth-button,.fc-timeGridWeek-button,.fc-timeGridDay-button)]:py-1.5!',
    '[&_:is(.fc-dayGridMonth-button,.fc-timeGridWeek-button,.fc-timeGridDay-button)]:mx-1!',
    // 未选中文字色：前景色弱化版（text-foreground-soft）。
    '[&_:is(.fc-dayGridMonth-button,.fc-timeGridWeek-button,.fc-timeGridDay-button)]:text-foreground-soft!',
    '[&_:is(.fc-dayGridMonth-button,.fc-timeGridWeek-button,.fc-timeGridDay-button)]:font-normal!',
    '[&_:is(.fc-dayGridMonth-button,.fc-timeGridWeek-button,.fc-timeGridDay-button)]:rounded-sm',
    // 选中态（.fc-button-active）：叠加一层更具体的 `.fc-button-active` 选择器。
    // 背景走变量层 --fc-button-active-bg-color（muted 浅灰；若想更明显可换
    // var(--primary)/0.12 或 var(--hover)/var(--border)），文字前景色 + semibold。
    // 注：背景实际由 v6 的 .fc-button-primary.fc-button-active 取 --fc-button-active-bg-color
    // 变量生效（变量走 DOM 继承，不受层叠层影响）；这条 bg-muted! 作兜底。
    '[&_:is(.fc-dayGridMonth-button,.fc-timeGridWeek-button,.fc-timeGridDay-button).fc-button-active]:bg-foreground-faint!',
    '[&_:is(.fc-dayGridMonth-button,.fc-timeGridWeek-button,.fc-timeGridDay-button).fc-button-active]:text-foreground!',
    '[&_:is(.fc-dayGridMonth-button,.fc-timeGridWeek-button,.fc-timeGridDay-button).fc-button-active]:font-semibold!',
];

// ── 导航按钮组（仅剩前/今天/后）────────────────────────────────────────────
// 整个 .fc-button-group 作为 prev/today/next 的公共外框，看起来像单个按钮：
// 浅灰边框 + 圆角 + 无阴影；内部按钮去圆角、去边框、去阴影，靠容器外框统一收口。
const BUTTON_GROUP = [
    '[&_.fc-button-group]:rounded-sm!',
    '[&_.fc-button-group]:border!',
    '[&_.fc-button-group]:border-border!',
    '[&_.fc-button-group]:bg-background!',
    '[&_.fc-button-group]:shadow-none!',
    '[&_.fc-button-group]:overflow-hidden!',
    // 组内按钮：去掉各自的圆角、边框、阴影，避免中间出现分隔线或独立投影。
    '[&_.fc-button-group_.fc-button]:rounded-none!',
    '[&_.fc-button-group_.fc-button]:border-0!',
    '[&_.fc-button-group_.fc-button]:shadow-none!',
    '[&_.fc-button-group_.fc-button]:ml-0!',
    // 悬浮时容器保持原边框，内部按钮单独变 hover 底，视觉仍是一个整体。
    '[&_.fc-button-group_.fc-button:hover]:bg-hover!',
];

// ── 时间网格 Slot 行高（周/日视图左侧时间轴 + 右侧事件区 tr）───────────
// v6 默认每个 slot tr 高度约 30px（contentHeight='auto' 下按 aspectRatio 推算），
// 视觉偏紧凑。这里强制最小行高 48px，让时间标签与事件有更充裕的垂直空间。
// ⚠ 只影响 timeGrid（周/日）视图，dayGrid（月视图）无 .fc-timegrid-slot 不受影响。
const TIMEGRID_SLOT = [
    // 时间 slot 行整体最小高度（含标签列 + 事件列）
    '[&_.fc-timegrid-slot]:min-h-[48px]!',
    // 时间标签列（左侧时间轴）内层容器高度 + 文字垂直居中
    '[&_.fc-timegrid-slot-label-frame]:min-h-[48px]!',
    '[&_.fc-timegrid-slot-label-frame]:flex!',
    '[&_.fc-timegrid-slot-label-frame]:items-center!',
    '[&_.fc-timegrid-slot-label-frame]:justify-end!',
    // 事件列（右侧事件区域）内层容器高度
    '[&_.fc-timegrid-slot-lane-frame]:min-h-[48px]!',
];

/**
 * 容器层完整样式覆盖类名。供 `LiveCalendar` 以
 * `cn(LIVE_CALENDAR_CSS_COVER, className)` 使用（本常量必须在前，`className` 在后，
 * 保证调用方传入的类名优先级最高）。
 */
export const LIVE_CALENDAR_CSS_COVER = [
    ...BASE,
    ...THEME_VARS,
    ...BUTTON_VARS,
    ...SCROLLGRID,
    ...COL_HEADER,
    ...DAY_CELL,
    ...EVENT_ANCHOR,
    ...TIMEGRID_EVENT,
    ...WEEK_NUMBER,
    ...POPOVER,
    ...TOOLBAR,
    ...BUTTON,
    ...NAV_BUTTON,
    ...VIEW_SWITCHER,
    ...BUTTON_GROUP,
    ...TIMEGRID_SLOT,
].join(' ');
