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
