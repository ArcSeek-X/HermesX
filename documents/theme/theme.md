# 主题与配色系统设计方案

> 文档版本：v1.0
> 创作者：Lensgcx（GaoCangxiong）
> 创建日期：2026-09-19
> 适用范围：`apps/hrs-web`（HermesX 前端）
> 关联代码：见文末[涉及文件清单](#6-涉及文件清单)

---

## 目录

- [1. 背景与目标](#1-背景与目标)
- [2. 整体设计规划](#2-整体设计规划)
- [3. 功能说明](#3-功能说明)
- [4. 数据链路与作用路径](#4-数据链路与作用路径)
  - [4.1 主题模式 themeMode](#41-主题模式-thememode)
  - [4.2 主色 themeColor](#42-主色-themecolor)
  - [4.3 侧栏视觉主题 sidebarTheme](#43-侧栏视觉主题-sidebartheme)
- [5. 实现路径与关键代码](#5-实现路径与关键代码)
- [6. 涉及文件清单](#6-涉及文件清单)
- [7. 附录：存储键与格式约定](#7-附录存储键与格式约定)

---

## 1. 背景与目标

前端主题系统需要同时管理三件相互独立的事：**明暗模式**、**品牌主色**、**侧栏视觉风格**。它们都要满足「刷新/切换后保持」且「首屏不闪烁（FOUC）」。

早期实现采用**双键并存**：应用自身的 `hrs-pref-theme.themeMode`（经 `utils/storage` 以 JSON 引号串落盘）与 next-themes 默认的裸键 `theme`（原始字符串）。两套格式互相不一致，需要 `syncNextThemesTheme` 桥接函数反复镜像，既冗余又有双写竞态风险。

**本次方案目标**：

1. **单键真值**：合并为唯一键 `hrs-pref-theme.themeMode`，由 next-themes 以原始字符串独占写盘，应用 store 只读取用于初始化。
2. **职责清晰**：明暗模式「内存真值在 store、磁盘真值在 next-themes」；主色/侧栏主题「由 store 直接落盘」。
3. **体验一致**：首屏防闪烁、弹层内「操作即预览、保存才提交」、切换瞬间无过渡时间差。

---

## 2. 整体设计规划

### 2.1 三维主题模型

| 维度 | 类型 | 取值 | 落盘方 | 作用对象 |
| --- | --- | --- | --- | --- |
| 主题模式 `themeMode` | 用户意图 | `light` / `dark` / `system` | next-themes（原始串） | `<html>` 的 `light`/`dark` class |
| 主色 `themeColor` | HEX | 预设 10 色 + 自定义 | store（JSON） | CSS 变量 `--primary` |
| 侧栏视觉主题 `sidebarTheme` | 外观偏好 | `pill` / `square` | store（JSON） | `SidebarNavNew` 外观 |

三者**正交**：明暗模式决定全局底色，主色决定强调色，侧栏风格决定导航容器形状，互不影响。

### 2.2 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│  使用层 UI：ThemeSetting（弹层，draft + 保存）                 │
└───────────────┬─────────────────────────────────────────────┘
                │  setThemeMode / setThemeColor / setSidebarTheme
                ▼
┌─────────────────────────────────────────────────────────────┐
│  状态层：useThemeStore（Zustand）  —— 内存真值                  │
└───┬───────────────────────┬───────────────────┬─────────────┘
    │ 订阅 themeMode         │ 订阅 themeColor    │ sidebarTheme（Shell 订阅）
    ▼                        ▼                  ▼
┌──────────┐         ┌──────────────┐    ┌──────────────────┐
│ThemeSync │         │applyPrimary  │    │ Shell → Sidebar- │
│ setTheme │         │Color(--primary)    │ NavNew(theme)    │
└────┬─────┘         └──────┬───────┘    └──────────────────┘
     │                      │
     ▼                      ▼
 next-themes           <html> style --primary
 （写 hrs-pref-         （内联样式覆盖样式表）
  theme.themeMode）
```

### 2.3 持久化分工（关键设计）

- `themeMode` → `hrs-pref-theme.themeMode`：**next-themes 以原始字符串写盘**，store 仅用 `readStoredMode()` 读取初始化；落盘发生在 `ThemeSync` 订阅到变化后调用 `next-themes.setTheme` 时（同时切 `<html>` class）。
- `themeColor` → `hrs-pref-theme.themeColor`：**store 经 `utils/storage.setStorageItem` 写盘**（JSON）。
- `sidebarTheme` → `hrs-pref-theme.sidebarTheme`：同上，由 store 写盘，再由 `Shell` 作为 prop 透传 `SidebarNavNew` 消费（非全局 CSS 变量）。

> **为什么 mode 必须是原始串、不能走 `setStorageItem`**：`utils/storage` 内部 `JSON.stringify('dark')` 会存成带引号的 `"\"dark\""`，而 next-themes 与 `index.html` 首屏脚本写/读的是原始串 `dark`。若 mode 键也用 `setStorageItem` 写，会与 next-themes 的原始串互相覆盖、且 `JSON.parse('dark')` 会抛错导致永远回退 `system`。故 mode 键严格保持「原始串 + next-themes 独占写」。

---

## 3. 功能说明

### 3.1 主题模式（浅色 / 深色 / 跟随系统）

- 提供 `light`、`dark`、`system` 三选项（`THEME_MODES`）。
- `system` 不固定明暗，运行时按 `prefers-color-scheme` 动态解析为实际 `light`/`dark`，切换系统外观时自动联动。
- 选择后通过 next-themes 切 `<html>` 的 class，全站明暗随 CSS 变量联动。

### 3.2 主色配置

- 提供 10 个预设色板（`PRIMARY_PRESETS`，覆盖中性色、语义色与项目主青蓝系）+ 自定义取色（`ColorPicker`）。
- 主色对外以 **HEX** 暴露（取色器使用 HEX），内部转 **HSL 三元组**（`"193 100% 43%"`）写入 CSS 变量 `--primary`，实现全站强调色联动。
- 默认值 `DEFAULT_PRIMARY_COLOR = '#19B5C4'`（与 `index.css :root` 的 `--primary` 一致，保证首屏一致）。

### 3.3 侧栏视觉主题（胶囊 / 方角）

- 提供 `pill`（大圆角胶囊感：容器带面板圆角 + 边框 + 阴影）与 `square`（方角：仅右侧分隔线 `border-r`，无圆角/阴影，默认）两选项（`SIDEBAR_THEMES`）。
- 与明暗模式正交，仅改变导航容器外观，由 `SidebarNavNew` 通过 `theme` prop 消费。

### 3.4 设置交互（操作即预览，保存才提交）

- 入口：顶栏 `ShellHeader` 的调色板按钮 `ThemeSetting`。
- 弹层通过 `createPortal` 渲染到 `document.body` + `fixed` 定位（`z-[130]`），脱离父级 stacking context 与 `overflow` 限制，始终置顶。
- 内部维护 **draft 草稿态**：调整即所见（即时写 DOM 预览），仅点「保存」才提交到 store 落库；「重置」丢弃草稿并还原。
- **过渡抑制机关**：预览路径 `applyModePreview / applyPrimaryColor` 绕过 next-themes，使 `disableTransitionOnChange` 失效；故在切换前注入 `transition:none` 的全局 `<style>`、切换后下一帧移除（保留 TabNav 指示条滑动），消除预览与正式切换的视觉时间差。

---

## 4. 数据链路与作用路径

### 4.1 主题模式 themeMode

```
用户选模式
  → ThemeSetting 保存 → setThemeMode(mode)        [themeStore：仅 set({themeMode})，不写盘]
      → Zustand 状态变化
      → ThemeSync 订阅到变化 → next-themes.setTheme(mode)
          → 写 localStorage["hrs-pref-theme.themeMode"] = "dark"（原始串）
          → 切 <html> class（.light/.dark）
  ── 首屏（React 挂载前）──
  index.html 内联脚本读 ["hrs-pref-theme.themeMode"]
      → 写入 <html> class（system/缺失时 matchMedia 跟随系统）  → 防 FOUC
  ── 刷新 ──
  themeStore.readStoredMode() 读同一键 → 初始化 themeMode（原始串，白名单校验）
```

### 4.2 主色 themeColor

```
用户选色
  → ThemeSetting 保存 → setThemeColor(hex)        [themeStore：setStorageItem + set]
      → 写 localStorage["hrs-pref-theme.themeColor"]（JSON）
      → Zustand 状态变化
      → ThemeSync 订阅到变化 → applyPrimaryColor(hex)
          → <html> 内联 style 设 --primary = HSL三元组（优先级高于样式表）
          → 全站强调色联动
  ── 刷新 ──
  readStoredPrimaryColor() 读同一键 → 初始化
```

### 4.3 侧栏视觉主题 sidebarTheme

```
用户选侧栏风格
  → ThemeSetting 保存 → setSidebarTheme(theme)    [themeStore：setStorageItem + set]
      → 写 localStorage["hrs-pref-theme.sidebarTheme"]（JSON）
      → Zustand 状态变化
      → Shell 订阅 sidebarTheme → <SidebarNavNew theme={sidebarTheme} />
          → 导航容器外观（pill/square）
  ── 刷新 ──
  readStoredSidebarTheme() 读同一键 → 初始化
```

---

## 5. 实现路径与关键代码

### 5.1 Provider：让应用键成为唯一真值

`storageKey` 把 next-themes 的存储重定向到应用键，裸 `theme` 键退役：

```tsx
// src/components/theme/ThemeProvider.tsx
<NextThemesProvider
  attribute="class"
  storageKey="hrs-pref-theme.themeMode"   // 应用主题键 = 唯一真值
  defaultTheme="system"
  enableSystem
  disableTransitionOnChange
>
  <ThemeSync />
  {children}
</NextThemesProvider>
```

### 5.2 桥接：store ↔ DOM

`ThemeSync` 把内存真值同步到实际渲染，是「store 只改内存、next-themes 负责落盘」闭环的关键：

```tsx
// src/components/theme/ThemeSync.tsx
const { setTheme } = useTheme();
const themeMode = useThemeStore((s) => s.themeMode);
const themeColor = useThemeStore((s) => s.themeColor);

useEffect(() => { setTheme(themeMode); }, [themeMode, setTheme]); // → 写 hrs-pref-theme.themeMode + 切 <html> class
useEffect(() => { applyPrimaryColor(themeColor); }, [themeColor]); // → 设 --primary
```

### 5.3 Store：读取原始串、mode 不写盘

```ts
// src/stores/themeStore.ts
const readStoredMode = (): ThemeMode => {
  try {
    // 原始串读取（next-themes 写盘），绝不经 JSON.parse
    const stored = window.localStorage.getItem(LOCAL_STORAGE_PREFIX + THEME_MODE_STORAGE_KEY);
    if (stored && (VALID_MODES as readonly string[]).includes(stored)) return stored as ThemeMode;
  } catch { /* 忽略 */ }
  return 'system';
};

setThemeMode: (mode) => {
  set({ themeMode: mode }); // 仅更新内存，落盘交给 ThemeSync → next-themes
},
setThemeColor: (hex) => {
  setStorageItem(THEME_COLOR_STORAGE_KEY, hex, 'local'); // 由 store 直接落盘（JSON）
  set({ themeColor: hex });
},
```

### 5.4 主色：HEX ↔ HSL 与 DOM 应用

```ts
// src/utils/themeColor.ts
export function applyPrimaryColor(hex: string): void {
  if (typeof document === 'undefined') return;
  const hsl = hexToHslTriple(hex);                 // HEX → "H S% L%" 三元组
  document.documentElement.style.setProperty('--primary', hsl); // 内联样式覆盖样式表
  document.documentElement.dataset.themePrimary = hex.toUpperCase();
}

// 预览阶段直接切 <html> class（绕过 next-themes，避免重渲染打断 TabNav 指示条）
export function applyModePreview(mode: ThemeMode): void {
  const root = document.documentElement;
  if (mode === 'system') {
    const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    root.classList.toggle('dark', isDark);
    root.classList.toggle('light', !isDark);
  } else {
    root.classList.remove('light', 'dark');
    root.classList.add(mode);
  }
}
```

### 5.5 首屏防闪烁（FOUC）

```html
<!-- index.html -->
<script>
  (() => {
    const storageKey = 'hrs-pref-theme.themeMode';
    const root = document.documentElement;
    const storedTheme = localStorage.getItem(storageKey);
    // 存储值为 light/dark 时直接采用；system/缺失时跟随系统偏好
    const theme = storedTheme === 'light' || storedTheme === 'dark'
      ? storedTheme
      : (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
    root.style.colorScheme = theme;
  })();
</script>
```

### 5.6 设置弹层：草稿 + 保存 + 过渡抑制

```tsx
// src/components/layout/HeaderComponents/ThemeSetting.tsx
// 保存：提交所有草稿到 store（正式落库）
<Button onClick={() => {
  setThemeMode(draftMode);
  setThemeColor(draftColor);
  setSidebarTheme(draftSidebarTheme);
  setOpen(false);
}}>{t('theme.save')}</Button>

// 预览：仅写 DOM，不落库
const applyPreview = (m, c) => {
  suppressThemeTransition();   // 注入 transition:none，消除时间差
  applyModePreview(m);
  applyPrimaryColor(c);
  requestAnimationFrame(restoreThemeTransition);
};
```

### 5.7 扩展指引（新增一个主题维度）

1. `types/theme.ts` 新增类型；`themeStore.ts` 新增 state 字段 + 读取函数（白名单校验）+ action（`setStorageItem` 落盘，除非是「mode 类」需走 next-themes）。
2. 若是影响全局外观的：在 `ThemeSync` 增加对应 `useEffect` 应用 DOM；若是组件级外观（如侧栏）：在 `Shell` 订阅后透传 prop。
3. UI 在 `ThemeSetting` 增加 `draft` + 保存分支；i18n 补充对应 `labelKey`。

---

## 6. 涉及文件清单

| 文件 | 职责 |
| --- | --- |
| `src/stores/themeStore.ts` | Zustand 状态：themeMode/themeColor/sidebarTheme 的读取、action、持久化分工 |
| `src/types/theme.ts` | `ThemeMode`、`SidebarTheme` 类型定义 |
| `src/components/theme/ThemeProvider.tsx` | 包裹 next-themes，设 `storageKey` 使应用键成为唯一真值 |
| `src/components/theme/ThemeSync.tsx` | store ↔ DOM 桥接（themeMode→setTheme；themeColor→--primary） |
| `src/utils/themeColor.ts` | HEX↔HSL 转换、`applyPrimaryColor`、`applyModePreview` |
| `src/components/layout/HeaderComponents/ThemeSetting.tsx` | 主题设置弹层（模式/主色/侧栏风格 + draft 预览 + 过渡抑制） |
| `src/components/layout/ShellHeader.tsx` | 顶栏挂载 `ThemeSetting` 入口 |
| `src/components/layout/Shell.tsx` | 订阅 `sidebarTheme` 透传 `SidebarNavNew` |
| `src/components/layout/SideBar/SidebarNav-new.tsx` | 消费 `sidebarTheme` 渲染导航外观 |
| `src/components/basic/ColorPicker.tsx` | 主色取色器（HEX 输入 + 预设色板） |
| `src/components/common/TabNav/TabNav.tsx` | 模式/侧栏风格的 Tab 切换控件 |
| `index.html` | 首屏内联脚本：挂载前读应用键防 FOUC |
| `src/style/palette.css` / `hrs-global.css` | 主题/语义 token 与 `--primary` 兜底定义 |

---

## 7. 附录：存储键与格式约定

| 存储键（localStorage） | 写入方 | 格式 | 说明 |
| --- | --- | --- | --- |
| `hrs-pref-theme.themeMode` | next-themes（经 `storageKey`） | **原始字符串** `light`/`dark`/`system` | 单键真值，store 仅读 |
| `hrs-pref-theme.themeColor` | `themeStore.setThemeColor` | JSON 字符串（HEX） | 由 `utils/storage` 写 |
| `hrs-pref-theme.sidebarTheme` | `themeStore.setSidebarTheme` | JSON 字符串 `pill`/`square` | 由 `utils/storage` 写 |

**回归红线**：`readStoredMode` 不可用 `getStorageItem`（JSON.parse 会抛错→永远回退 `system`）；`setThemeMode` 不可用 `setStorageItem` 写 mode 键。保持 mode 键「原始串 + next-themes 独占写」是合并后架构不可破坏的前提。
