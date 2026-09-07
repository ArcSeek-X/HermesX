# 长期记忆（MEMORY.md）

## 用户偏好
- **代码注释风格**：偏好精简。删除「修改过程产物」类注释（如"已移除 XX""已移到 XX 文件""原先的 XX 联动已移除"）、与代码自明/彼此重复的冗余说明；保留有价值的 why（设计取舍、踩坑原因）与简短步骤标记（如 `// 1) 收集...`）。
- 注释语言：中英文混合项目中，中文注释做概述级补充，原有英文 docstring 原样保留。

## 项目约定（hrs-web）
- **抽屉组件**：统一用 `components/basic/Drawer.tsx`（HrsDrawer，HeroUI 底座）；`components/common/Drawer.tsx` 为旧版，新代码不用。
- **消息日历点击语义**：点消息 = 打开 `LiveCalendarEventDrawer` 详情抽屉（不切视图）；点日期格空白 / 日期标题 = 切到日视图看当天全部。两条路径刻意分开。
- **i18n 命名空间**：日历相关文案为 `component.LiveCalendar.*`（非 `liveCalendar.*`）；新增 key 需 zh / zh-Hant / en 三语同时补齐（`UiTextKey` 由 uiText-zh.ts 推导）。
- **日期时间格式化**：一律复用 `utils/format.ts` 的 `formatDate` / `formatDateTime` / `formatTime`（接受秒级时间戳，内部自动 ×1000，输出固定 zh-CN 数字格式），**不要**在组件里手写 `new Date(ts*1000)` + `Intl.DateTimeFormat`。需要随 UI 语言本地化的（星期 / 月份长格式）用 `toIntlLocale(language)`——全站唯一的 locale 映射，勿在各组件重复写 zh-CN / zh-TW / en-US 三元判断。
