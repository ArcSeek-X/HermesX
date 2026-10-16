# <a id="vibe-universe"></a>UniverseBackground 星空背景组件方案

> 📝 **方案简述**：本方案将本地模板 `vibe-template/earth-migration`（「BEYOND THE WANDERING EARTH」，Three.js）封装为 `apps/hrs-web/src/components/universe` 下的 React 可复用背景组件，界定其定位、架构、Engine 封装接缝、对外 API 与使用规范；核心立场为「整包 vendor 移植（非 iframe / 非裁剪）、控件沿用原版 HUD、静态资源全量置于 `public/universe` 不参与打包、引擎以 vendored `.js` + `allowJs` 保留」。
>
> 👤 **方案作者**：Lensgcx (GaoCangxiong) - ArcSeek-X
>
> 🕒 **更新时间**：2026-10-16

## 目录

- [一、组件定位与适用范围](#sec-1)
- [二、整体架构](#sec-2)
- [三、关键设计决策](#sec-3)
  - [3.1 整包 vendor 移植（否决 iframe / 裁剪）](#sec-3-1)
  - [3.2 控件沿用原版 HUD，不硬套仓库规范](#sec-3-2)
  - [3.3 静态资源全量进 public，不参与打包](#sec-3-3)
  - [3.4 引擎以 vendored `.js` + `allowJs`](#sec-3-4)
  - [3.5 默认银心外 halo 视角 + 星系慢转](#sec-3-5)
- [四、Engine 封装与接缝](#sec-4)
  - [4.1 `createUniverse(opts)` 工厂](#sec-4-1)
  - [4.2 资源基址与 URL 修饰器（关键护栏）](#sec-4-2)
  - [4.3 命令式 API 与 `dispose`](#sec-4-3)
  - [4.4 上游同步](#sec-4-4)
- [五、React 组件 API](#sec-5)
  - [5.1 Props](#sec-5-1)
  - [5.2 命令式 API（ref）](#sec-5-2)
  - [5.3 用法示例](#sec-5-3)
- [六、UI 外壳与 HUD](#sec-6)
- [七、使用规范](#sec-7)
- [八、工程与依赖](#sec-8)
- [九、验证与质量](#sec-9)

---

<a id="sec-1"></a>

## 一、组件定位与适用范围

**规定**：`UniverseBackground` 是 hrs-web 内一个**可复用的炫酷背景组件**，源自「BEYOND THE WANDERING EARTH」Three.js 体验的整包 vendor 移植；它不是一个通用 3D 引擎，也不承担业务交互。

**Why**：项目需要一个具备「地球行星发动机 → 太阳系 → 银河系 → 河外星系」连续尺度梯子、带后期辉光、剧情/自由相机与原版 HUD 的视觉背景，作为页面/区块的氛围层。整包移植可在不重写上游逻辑的前提下完整保留上述能力。

**How to apply**：以下场景适用——首页/落地页/大屏的氛围背景；需要 VOYAGE 时间轴、ORBITS 时间倍率、尺度缩放、星系自转等可调控件的演示页。**不适用**——需要脱离原版视觉语言的高度定制 3D 场景；对包体与加载耗时零容忍的移动端首屏（见 [§8](#sec-8) 体量说明）。

| 维度 | 说明 |
| --- | --- |
| 来源 | `vibe-template/earth-migration`（MIT © 2026 玛卡巴卡，未被 git 跟踪） |
| 代码位置 | `apps/hrs-web/src/components/universe/` |
| 静态资源 | `apps/hrs-web/public/universe/`（`assets/` 31M + `draco/gltf/` 752K），不参与打包 |
| 依赖 | `three@^0.160.1`（与 vendored r160 对齐） |
| 复用方式 | `import UniverseBackground from '@components/universe/UniverseBackground'` |

---

<a id="sec-2"></a>

## 二、整体架构

组件分三层：**React 封装层 → Engine 工厂层（vendored Three.js）→ 静态资源层**。UI 外壳（DOM + CSS）与渲染（canvas）解耦，由 React 统一调度生命周期。

```
universe/
├── UniverseBackground.tsx   # React 封装：容器/生命周期/props→engine 同步/暂停策略/字体注入/降级
├── types.ts                # props / ref API / engine 入参类型契约（engine 无 .d.ts，在此声明）
├── index.ts                # 叶子导出（不走 @components 裸桶）
├── ui/
│   ├── BeyondShell.tsx     # beyond.html 的 JSX 移植：loader/标题屏/HUD/片尾屏（canvas 不在此）
│   └── beyond.css          # beyond.css 作用域化版本（全部收敛到 .universe-bg 内）
├── engine/                 # vendored 引擎（beyond/ + fx/，MIT，接缝清单见 engine/README.md）
└── __tests__/              # jsdom 冒烟（无 WebGL 降级路径）
```

**关键约束**：`engine/` 为 vendored `.js`（无类型声明），由 `tsconfig.app.json` 的 `allowJs` 编译；`@components` 裸桶仅聚合 `basic/common`，`universe` 走叶子路径或目录 `index.ts`。

---

<a id="sec-3"></a>

## 三、关键设计决策

下列决策在需求评审时定案，采用「规定 + Why + How to apply」三段式记录，后续改动须先回归这些立场。

<a id="sec-3-1"></a>

### 3.1 整包 vendor 移植（否决 iframe / 裁剪）

**规定**：采用方案 A——将 `js/beyond/*` 与 `js/fx/*` 原样 vendor 进 `engine/`，最小改造 `main.js` 为工厂函数；**否决** iframe 嵌入与「只移植 galaxy.js」的裁剪方案。

**Why**：
- `vibe-template/` 在根 `.gitignore` 中（上游未被 git 跟踪），iframe / 外链在 CI 与生产环境直接不可用，代码必须入库；
- 裁剪 galaxy 层会丢失 VOYAGE 时间轴、ORBITS 时间倍率与地球/太阳系层，无法满足「从星系放大到太阳系」的诉求；
- 上游已存在无 UI 驱动的 `js/wallpaper/` 控制器，证明该体验可脱离页面 UI 运行，背景化应走此路而非重写。

**How to apply**：任何「只取其中一段」的诉求，优先评估是否可用 `zoomTo` / `anchor` / `mode` 等 props 在整包内满足，而非裁剪源码。

<a id="sec-3-2"></a>

### 3.2 控件沿用原版 HUD，不硬套仓库规范

**规定**：VOYAGE / ORBITS / 缩放 / 转速等控件**直接使用组件内 vendor 的原版 HUD**（滑条、seg3 分段、标尺、热点、DESTINATIONS），不强行替换为仓库 `HrsButton` 等规范组件。

**Why**：封装成独立组件后，控件归属不再受仓库组件库约束；原版 HUD 与 engine 的 `id` 查询强耦合（见 [§6](#sec-6)），替换成本高且易破坏联动。

**How to apply**：如确需统一视觉，应在 `ui/beyond.css` 作用域内覆盖样式，而非替换 DOM 结构或 `id`。

<a id="sec-3-3"></a>

### 3.3 静态资源全量进 public，不参与打包

**规定**：31M 资源与 Draco decoder 落在 `apps/hrs-web/public/universe/`，由 Vite 原样复制进产物，**不进入 JS bundle、不被哈希/minify**。

**Why**：资源为预优化的二进制（jpg/bin/wasm/glb），Vite 不该在构建期重新处理；且它们按 `assetsBase`（`${BASE_URL}universe/`）运行时寻址，放 `public/` 是标准且正确的「不参与打包」做法。

**How to apply**：切换 CDN 时仅改 `assetsBase` prop，无需移动资源；若担忧仓库体积/构建扫描耗时，正确手段是 git-lfs 或对象存储，而非把资源搬进 `src/`。

<a id="sec-3-4"></a>

### 3.4 引擎以 vendored `.js` + `allowJs`

**规定**：engine 保留为 ES module `.js` 原样入库，仅给 `tsconfig.app.json` 开 `allowJs`；**不**逐步 TS 化。

**Why**：680K JS 全量类型化工作量巨大且易引入行为差异；`.js` 与上游 diff 最小，便于人工同步（上游不在 git 内）。

**How to apply**：engine 的对外契约（props/ref/入参）在 `types.ts` 显式声明，避免 `any` 泄漏到调用方；engine 内部改动须同步更新 `types.ts` 与 `engine/README.md` 的接缝清单。

<a id="sec-3-5"></a>

### 3.5 默认银心外 halo 视角 + 星系慢转

**规定**：组件默认以自由相机 `anchor='gc'`、距离 90000 ly 进入，并持续缓慢自转（即目标「银心视角 + 星系慢转」截图状态）。

**Why**：该状态最省 CPU/GPU、最像背景，且无需用户交互即具动感；戏剧性更强的 `mode='film'`（146s 剧情电影）作为可选项保留。

**How to apply**：纯装饰背景用 `interactive={false}`；如需剧情播放，显式传 `mode='film'`。

---

<a id="sec-4"></a>

## 四、Engine 封装与接缝

<a id="sec-4-1"></a>

### 4.1 `createUniverse(opts)` 工厂

原 `import` 即执行的单页入口被改造为工厂函数，`export function createUniverse(opts)`，返回原 `window.__beyond` 同形 API。核心入参：

| 入参 | 类型 | 说明 |
| --- | --- | --- |
| `canvas` | `HTMLCanvasElement` | 渲染目标，由 React 创建并挂到 `root` 下 |
| `root` | `HTMLElement` | UI 外壳元素；原 `$('id')` 全部限定其内，无 root 时走 DOM 哑对象垫片 |
| `tier` / `mode` / `anchor` / `distance` / `entry` / `flyIn` | 见 [§5.1](#sec-5-1) | 初始化参数（多数仅首次挂载生效） |
| `voyage` / `orbitSpeed` / `rotationSpeed` / `interactive` / `audio` | 见 [§5.1](#sec-5-1) | 初始化参数 |
| `assetsBase` | `string` | 静态资源基址，默认 `${BASE_URL}universe/` |
| `onProgress` / `onReady` / `onError` | 回调 | 加载进度 / 就绪 / 失败 |

<a id="sec-4-2"></a>

### 4.2 资源基址与 URL 修饰器（关键护栏）

资源寻址经 `THREE.DefaultLoadingManager.setURLModifier` 注入 `assetsBase` 前缀，覆盖约 30 处 `tex()` / `loadModel()` / `fetch()` 调用点，实现零侵入改写。

**【强制】** 修饰器必须对**已根绝对**的 URL（如 Draco decoder 的 `/universe/draco/gltf/...`）直接放过，**不得**再加 `assetsBase` 前缀。曾因漏掉该分支导致路径双重前缀（`/universe/universe/...`），GLTF 解析挂死、loader 卡在 4%。该分支在 `main.js` 内有注释标记，改动 `main.js` 资源寻址逻辑时**必须保留**。

<a id="sec-4-3"></a>

### 4.3 命令式 API 与 `dispose`

在原型 API 之外新增：`setVoyage` / `setOrbitSpeed` / `setRotationSpeed` / `setPaused` / `zoomTo` / `zoomBy` / `resize` / `dispose`；星系自转速率新增 `S.galRotK` 倍率（free 相机与 story 两处均乘此值）。`dispose()` 负责停帧、解绑全部监听、释放 GPU 资源，且对 React StrictMode 双挂载安全。

<a id="sec-4-4"></a>

### 4.4 上游同步

上游 `vibe-template/` 未被 git 跟踪，同步方式为人工比对：

```bash
diff -u vibe-template/earth-migration/js/beyond/main.js \
        apps/hrs-web/src/components/universe/engine/beyond/main.js
```

合并时**必须保留** `main.js` 的工厂包装（文件头注释 + `host integration` 段 + 尾部 `api` 块）与 `engine/README.md` 记录的全部接缝；`dash.js` / `story.js` / `fx/models.js` 的接缝补丁随版本复核。

---

<a id="sec-5"></a>

## 五、React 组件 API

<a id="sec-5-1"></a>

### 5.1 Props

| Prop | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `className` / `style` | — | — | 容器类名/样式；默认 `absolute inset 0`，可作任意区块背景 |
| `tier` | `'low' \| 'medium' \| 'high' \| 'ultra'` | 按设备（桌面 high / 移动 low） | 画质分级，只改成本不改观感；运行中变更不重建场景 |
| `mode` | `'free' \| 'film'` | `'free'` | **仅首次挂载生效**；`film` = 146s 剧情电影 |
| `anchor` / `distance` | `string` / `number` | `'gc'` / 90000 | **仅首次挂载生效**；自由相机锚点与距离（art-AU） |
| `entry` | `'galaxy' \| 'title'` | `'galaxy'` | `'title'` 保留原版标题屏 |
| `flyIn` | `boolean` | `true` | 是否以飞行动画进入入口视角 |
| `voyage` | `number` | `0` | 剧情时间（秒，0–146）；运行中变更等价于拖 VOYAGE 滑条 |
| `orbitSpeed` | `0 \| 0.04 \| 0.35 \| 3` | `0` | ORBITS 时间倍率（实时 / 1年25秒 / 1年3秒 / TIME-LAPSE） |
| `rotationSpeed` | `number` | `1` | 星系自转倍率（1 = 原速 0.012 rad/s，0 = 静止） |
| `interactive` | `boolean` | `true` | 滚轮/拖拽/键盘/HUD 点击；`false` 时容器 `pointer-events: none`，作纯装饰背景 |
| `audio` | `boolean` | `false` | 声音（浏览器需用户手势） |
| `paused` | `boolean` | `false` | 手动暂停；页面隐藏 / 滚出视口会自动暂停 |
| `assetsBase` | `string` | `${BASE_URL}universe/` | 静态资源基址（可指 CDN） |
| `onReady` / `onProgress` / `onError` | 回调 | — | 就绪 / 加载进度(0–1, 文案) / 启动失败（如 WebGL 不可用） |
| `ref` | `React.Ref<UniverseImperativeApi>` | — | React 19 ref prop，拿命令式 API |

<a id="sec-5-2"></a>

### 5.2 命令式 API（ref）

`ref` 暴露的 `UniverseImperativeApi` = 引擎句柄 + `raw`：

| 方法 | 说明 |
| --- | --- |
| `zoomTo(target)` | 语义化缩放飞行：`'galaxy'`（本星系群外）/ `'milkyway'` / `'sol'` / `'acen'` / `'orrery'`（太阳系俯视）/ `'sun'` / `'earth'` |
| `zoomBy(factor)` | 对数缩放，>1 拉远、<1 靠近（等价滚轮） |
| `focus(key)` | 聚焦热点/天体，key 见 `engine/beyond/main.js` 的 `HOT`（如 `'gc'` / `'solGal'` / `'sun'` / `'engines'` / `'ring'`） |
| `setVoyage(t)` / `seek(t)` | 设置 / 跳转剧情时间（`seek` 额外吸附相机与曝光） |
| `setOrbitSpeed(v)` / `setRotationSpeed(k)` / `setTier(t)` / `setPaused(p)` / `resize(w, h)` | 同 props；`resize` 由组件 `ResizeObserver` 自动调用 |
| `dispose()` | 销毁（组件卸载自动调用） |
| `raw` | 原始引擎对象（高级用法，随 vendor 版本演进） |

<a id="sec-5-3"></a>

### 5.3 用法示例

```tsx
import UniverseBackground from '@components/universe/UniverseBackground'
import type { UniverseImperativeApi } from '@components/universe'

// 1) 最简：整页背景（默认银心外 halo 视角 + 星系慢转，纯装饰）
<UniverseBackground interactive={false} />

// 2) 编程控制：拿 ref
const api = useRef<UniverseImperativeApi>(null)
<UniverseBackground ref={api} tier="medium" rotationSpeed={0.5} />
api.current?.zoomTo('solar')   // 飞到太阳系俯视
api.current?.setVoyage(96)     // 剧情时间跳到 96s（远航段）
api.current?.setOrbitSpeed(3)  // ORBITS 时间倍率 → TIME-LAPSE
```

入口方式二选一，不要同时用：`import UniverseBackground from '@components/universe/UniverseBackground'` 或 `import { UniverseBackground } from '@components/universe'`。

---

<a id="sec-6"></a>

## 六、UI 外壳与 HUD

`ui/BeyondShell.tsx` 是 `beyond.html` 的 JSX 移植，元素 `id` 与原页一一对应——engine 按 `id` 查询并直接操作这些节点。**canvas 不在此处渲染**，由 `UniverseBackground` 动态创建并挂载到根节点下（对应 `ui/beyond.css` 的 `> canvas` 规则）。

**【强制】** 增删元素或改 `id` 前，必须先确认 `engine/beyond/main.js` 中的 `$('...')` 调用点；否则 engine 找不到节点会导致 HUD 失联或运行异常。

保留的原版 HUD 与屏：loader、标题屏（`#start`，含 Begin / Free camera 双 CTA）、NAVIGATION TELEMETRY 仪表盘（`#data`）、热点层（`#hotspots`）、信息卡（`#info`）、模式/声音/全屏工具条（`#modes`）、DESTINATIONS 面板（`#dest`）、尺度梯子（`#ladder`）、剧情 dock（`#dock` 章节时间轴 + 播放）、VOYAGE 滑条 + ORBITS 分段 + 尺度标尺（`#xdock`）、片尾屏（`#end`）。

`ui/beyond.css` 经 PostCSS 作用域化：全部选择器收敛到 `.universe-bg` 内、`:root` 变量收敛到根元素、媒体查询全覆盖、`@keyframes` 原样保留；`position: fixed` 改为 `absolute` 以避免越界盖住宿主侧栏/页头。

---

<a id="sec-7"></a>

## 七、使用规范

**【强制】** 作为页面背景接入时，背景层须用 `position: fixed; inset: 0; zIndex: -1`，并依赖主滚动容器的 `[contain:layout_paint]` 使其相对主内容区固定（与既有 `LightBloom` 同机制）；页面内容须自带 `relative z-10` 类层级，才能稳定浮于背景之上。

```tsx
<AppPage className="flex flex-col">
  {/* fixed + Main 的 [contain:layout_paint] → 相对主滚动容器固定、不随内容滚动，
      也不越界盖到侧栏/页头；zIndex -1 沉在内容之下 */}
  <UniverseBackground style={{ position: 'fixed', inset: 0, zIndex: -1 }} />
  <div className="relative z-10 ...">{/* 页面内容 */}</div>
</AppPage>
```

**【强制】** 同一页面只挂一个实例。WebGL context 上限约 16；HUD 为 `id` 级 DOM，多实例会互相查询到对方的节点。

**【推荐】** 嵌入有滚动条的页面时，优先 `interactive={false}`（容器 `pointer-events: none`，不劫持滚轮/键盘）；需要用户操控 VOYAGE/缩放时再开 `interactive={true}`。

**【推荐】** 暗色主题下 `Main` 仍会渲染 `LightBloom`，但会被不透明星空画布完全遮盖（视觉无影响）；若想去掉该开销，将 `/home` 从 `Main.tsx` 的 `BACKGROUND_ROUTES` 中移除即可。

**【推荐】** 组件默认即目标「银心视角 + 星系慢转」状态，无需额外配置；纯装饰用 `interactive={false}`。

---

<a id="sec-8"></a>

## 八、工程与依赖

- **依赖**：`three@^0.160.1`（与 vendored r160 对齐）；`tsconfig.app.json` 开 `allowJs`（engine 为 `.js`、无 `.d.ts`，`tsc -b` 需要）。
- **lint 边界**：eslint 只查 `*.ts/*.tsx`，engine 的 `.js` 不参与 lint，类型契约由 `types.ts` 兜底。
- **资源体量**：`public/universe/` 约 32M 进入仓库与构建产物；Vite 的 `sourceFingerprint` 会全量读取 `src+public`，构建耗时增加数秒（与「打包与否」无关，是 public 资源固有开销）。
- **多实例**：见 [§7](#sec-7) 强制项。
- **降级**：无 WebGL 时 loader 显示 `SYSTEM FAULT · WEBGL UNAVAILABLE` 并回调 `onError`，不白屏崩溃（jsdom 冒烟测试覆盖）。
- **上游同步**：见 [§4.4](#sec-4-4)。

---

<a id="sec-9"></a>

## 九、验证与质量

**【推荐】** 改动后依次执行下列命令，确保 universe 相关零报错：

```bash
npx eslint src/components/universe --ext .ts,.tsx   # 0 错误
npx tsc -b                                          # universe 0 类型错误（仓库 HEAD 另有既有错误，与本次无关）
npx vitest run src/components/universe              # 3 条 jsdom 冒烟（UI 外壳渲染 / 无 WebGL 降级 / 卸载清理）
npx vite build                                      # 引擎与 universe/ 资源（含 draco wasm）正确进产物
```

浏览器实机：dev server 挂载后 loader 约 5s 内 READY，HUD 遥测 / 热点 / 章节正常、0 页面错误（截图见 PR）。`mode='film'` 入口与移动端真机为未实机验证项，上线前建议补验。
