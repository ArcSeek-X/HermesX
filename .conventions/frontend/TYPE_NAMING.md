---
name: type-naming-skill
description: 前端类型规范，含两部分：(1) 命名基准——对外导出类型何时用 Def（数据/契约）何时用 Props（组件入参）；(2) 定义位置——src/types/ 目录定位、何时把类型定义到 types/、依赖方向（types 为最底层、禁止反向依赖）与单真源原则。
---

# 类型命名基准：Def vs Props

本规范用于统一项目内对外导出类型的命名，明确何时使用 `Def` 后缀、何时使用 `Props` 后缀。

## 核心判断

> **描述数据 → `Def`；描述组件怎么用 → `Props`。**

唯一的分水岭：这个类型描述的是「一份数据结构 / 数据契约」，还是「一个 React 组件的入参接口」。

| 维度 | `Def`（定义） | `Props`（属性） |
|---|---|---|
| 描述对象 | 一份数据结构 / 数据契约 | 一个 React 组件接收的入参 |
| 是否会渲染 | 不会，是纯数据 | 会，挂载到 DOM 的组件 |
| 典型成员 | `key / label / title / options / variant` 等业务字段 | `className / style / onClick / onChange / children / ref` 等交互/渲染字段 |
| 消费方 | 被组件内部解析、转换成 UI | 直接由组件主题/样式/行为使用 |
| 生命周期 | 随「数据」走，与组件实现无关 | 随「组件实现」绑定，组件变更可能改 Props |

## 三条判定规则

**规则 1：这东西能脱离组件独立存在吗？**
- 能（如「一条 toast 的内容」「一个下拉选项」「一列的配置」）→ `Def`
- 不能（它就是组件本身长什么样、怎么响应点击）→ `Props`

**规则 2：看有没有 React 专属字段**
- 含 `className / style / onClick / ref / children / render` 函数 / `aria-*` → 通常是 `Props`
- 全是业务数据字段，无 React 概念 → `Def`

**规则 3：它会被多个组件共用同一份定义吗？**
- 会（同一份 `HrsSelectOptionDef` 既给 Select 用、也给别处当数据）→ `Def`
- 只服务于那一个组件 → `Props`（字段再多也别拆成 Def）

## 边界情况

**`render?: (row: T) => ReactNode` 出现在 `Def` 里，仍归 `Def`。**
因为它整体是「列的数据定义」，`render` 只是该定义中的一个可选「自定义渲染钩子字段」，属于数据契约的一部分，并非组件对外接口。判定时看**整体语义**，不盯单个字段。

## 项目内已落地的示例

| 类型 | 命名 | 理由 |
|---|---|---|
| `TableColumnDef<T>` | Def | 描述「一列的数据结构」，含 `key/title/render`，被 Table 解析渲染，可脱离 Table 独立定义 |
| `PaginationDef` | Def | 描述「分页配置数据」（pageSize/page 等），是数据契约 |
| `ToastDef` | Def | 描述「一条通知的内容」（title/description/variant），命令式 API 的入参数据 |
| `HrsSelectOptionDef` / `HrsSelectSectionDef` / `HrsSelectDataSourceDef` | Def | 选项数据，可被任意组件消费 |
| `HrsSelectProps` / `InputProps` / `ModalProps` / `TableProps` | Props | 含 `className / onChange / value / size` 等，是组件挂载接口 |

## 一句话总结

拿不准时，问自己：**「它是不是一份能单独传给组件去解析的数据？」**
- 是 → `Def`
- 否 → `Props`

---

# 类型定义位置：types/ 目录定位与归属规则

> 命名（Def/Props）解决「叫什么」，本章解决「放哪里」。两者正交：一个类型既可能叫 `XxxDef`、又可能定义在 `types/` 里。

## 1. types/ 的定位

- `src/types/` 是**跨模块 / 跨层共享的 TS 类型契约集中地**，是项目类型系统的「单一真源层」。
- 它承载两类契约：
  1. **后端 API 数据契约（DTO）/ 领域模型**：如 `systemConfig.ts`、`portfolio.ts`、`market.ts`。
  2. **UI 偏好与客户端配置类型**：如 `theme.ts` 的 `ThemeMode`（主题模式）。UI 配置类类型同样归属 `types/`，不因为「不是后端数据」就塞进组件或 utils。
- 它是**依赖图最底层**：自身只允许 `import type` 同目录其它类型，绝不依赖 `stores` / `utils` / `components`。
- 编码依据：「跨项目通用语义集中此处统一管理，避免各模块自行定义多套互不兼容表示法」。

## 2. 何时定义到 types/（判定矩阵）

满足**任一**条件 → 放 `types/`（按主题/领域新建或并入对应文件）：

| 条件 | 示例 |
|---|---|
| 被 ≥3 个独立模块/层级引用（store + utils + 组件跨目录共用） | `ThemeMode`：themeStore / themeColor / ThemeSetting / ThemeSync / ThemeToggle 共用 → `types/theme.ts` |
| 后端 API 响应/请求数据契约（DTO）或跨业务通用的领域模型 | `systemConfig.ts`、`portfolio.ts`、`market.ts`、`backtest.ts` 等 |
| 易在各处被重复定义、导致语义错位的通用标识 | `Market` / `AssetType`（市场/资产标识） |
| UI 偏好 / 客户端配置，且被多处订阅 | `ThemeMode`（主题模式） |

## 3. 何时就近定义（不放 types/）

满足**全部**条件 → 留在定义它的文件内（组件、store 或 utils 中）：

- 仅**单文件 / 单个组件内部**使用（私有 helper 类型、组件内联派生类型、store 内部且仅本 store 消费的中间类型）；
- 不会被其它模块引用；
- 可用 `ReturnType<typeof fn>` / 类型推断得到的内部类型。

> 约定：`Zustand` store 的 `State` 接口若只被该 store 及其直接消费方使用、**且没有 utils 反向引用其中的类型**，可就近定义在 store 内（常见做法）；一旦有 `utils/components/pages/hooks 等` 反向 `import type` 了其中的某个类型，说明该类型应下沉到 `types/`（见 §4）。

## 4. 依赖方向原则（强约束）

- **types/ 是叶子底层**：只允许 `import type` 同目录其它类型，禁止 `import` stores / utils / components/ hooks 等（否则制造循环 / 倒置依赖）。
- **utils/ 是叶子层**：`utils/` 下的纯函数模块**禁止反向 `import type` stores**。若某类型被 `utils` 与 `store` 共用，必须下沉 `types/`，让双方都从 `types/` 取——而不是让 `utils` 上溯引用 `store`。


## 5. 单真源：禁止重复定义等价类型

- 同一语义的联合 / 接口类型**只允许存在一份**。某模块如需使用，从 `types/` 导入，不得就地重定义
- 危害：重复定义会在重构时语义分叉（一处改、一处没改）；TS 结构类型下表面兼容，实则失去单一约束、无法靠编译器拦截不一致。

## 6. 文件组织约定

- 按**领域 / 主题**分文件（`theme.ts` / `market.ts` / `systemConfig.ts` / `portfolio.ts` / `backtest.ts` ...），**不要堆成一个大 `index.ts`**。
- 当前 `types/` **无 barrel `index.ts`**，外部按精确路径导入：`import type { ThemeMode } from '../types/theme'`。保持此约定（避免 barrel 带来的耦合与循环风险）。
- 每个类型文件顶部用块注释说明其**语义边界**（参考 `market.ts` 头部：说明这些类型属于跨项目通用语义、为何集中于此、防止各模块重复定义）。

## 7. 与 CODE_ANNOTATION.md 的关系

落到 `types/` 的类型同样遵守注释规范：

- 枚举 / 联合类型**逐一注释每个取值含义**（如 `ThemeMode` 的 `light`/`dark`/`system` 各写一句）；
- `interface` / `type` 的**每个字段一句话说明业务含义**；
- 文件头含 `@file` + `@description`（作用 + 使用场景 / 被谁引用）+ `@author`。

## 8. 决策速查

```
这个类型会被多少个模块/层引用？
├─ ≥3 个独立模块（尤其跨 store / utils / components）？        ──► 放 types/<domain>.ts
├─ 是后端 DTO / 领域模型 / 易重复定义的通用标识？              ──► 放 types/<domain>.ts
└─ 仅本文件 / 本组件内部使用（且不会被外部引用）？            ──► 就近定义（不放 types/）

且始终遵守：
  · types/ 不依赖上层；utils/ 不反向 import type stores
  · 等价类型全局唯一，禁止就地重定义
```
