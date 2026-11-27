# Tree 基础树组件

基于本机完整的 **HeroUI Pro React 1.0.1 FileTree**，将递归数组转换为原生FileTree/Collection节点。展开、选择、checkbox、焦点与键盘行为交给底层组件；菜单复用HrsButton及React Aria Menu/Popover；拖放使用FileTree同源的React Aria拖放能力，并增加不可变数据移动和防环规则。

[官方FileTree文档](https://heroui.pro/docs/react/components/file-tree)。只导入FileTree专用CSS，尺寸与层级沿用Pro，文字颜色通过组件内Tailwind对齐项目主题；未启用整包Pro样式，未新增global.scss规则。

前置条件：开发机和CI需要完整Pro 1.0.1实现，公开npm安装器本身不包含FileTree。重新执行npm ci后须按[组件包与缓存说明](../../../../../../documents/components/heroui_pro_1_0_1_components.md)恢复完整包或完成授权下载；未配置新的CI授权流程。

## 文件清单与职责

下表路径均相对于`apps/hrs-web/src/components/basic/Tree/`，点击文件名可打开对应文件。当前数据工具的实际文件名为`treeDataFactory.ts`；对应测试文件仍叫`treeData.test.ts`。

| 文件名称 | 目录内路径 | 职责 | 具体内容与使用场景 |
| --- | --- | --- | --- |
| [Tree.tsx](./Tree.tsx) | `Tree.tsx` | 树组件主体 | 接收嵌套数组并递归渲染HeroUI Pro FileTree，组合展开、选择、禁用、图标、菜单与拖放。业务页面主要使用此组件。 |
| [types.ts](./types.ts) | `types.ts` | 公开类型与参数约定 | TreeNodeDef定义节点字段；TreeProps声明全部支持参数；TreeMoveDef描述拖放结果；TreeIconComponents定义图标注册格式。用于开发时的类型检查。 |
| [TreeItemMenu.tsx](./TreeItemMenu.tsx) | `TreeItemMenu.tsx` | 节点“…”操作菜单 | 渲染操作入口、下拉菜单、危险色与禁用状态，并执行传入的actionFn，例如打开编辑表单或删除确认框。 |
| [treeDataFactory.ts](./treeDataFactory.ts) | `treeDataFactory.ts` | 树索引与数据移动工具 | queryTreeIndexFn建立索引并检查重复ID；updateTreeMoveFn返回移动后的新数组，保留完整子树，处理排序、禁用、防环与无效移动。 |
| [treeIcons.ts](./treeIcons.ts) | `treeIcons.ts` | 具名图标注册表 | 将Folder、Database等名称映射到图标组件，供节点icon/expandedIcon使用；业务可通过iconComponentsData扩展。 |
| [index.ts](./index.ts) | `index.ts` | 统一对外出口 | 集中导出Tree、TreeItemMenu及公开类型。页面从@components/basic/Tree导入；数据工具与内部图标表由组件内部使用。 |
| [README.md](./README.md) | `README.md` | 组件使用说明 | 记录本目录文件职责、参数、数据格式、图标、菜单、拖放、Demo和验证边界。 |
| [Tree.test.tsx](./__tests__/Tree.test.tsx) | `__tests__/Tree.test.tsx` | 基础交互测试 | 使用真实FileTree验证递归渲染、展开、单选/多选、禁用、图标、ref及数据更新。 |
| [TreeItemMenu.test.tsx](./__tests__/TreeItemMenu.test.tsx) | `__tests__/TreeItemMenu.test.tsx` | 菜单交互测试 | 验证操作回调、选择隔离、键盘关闭、禁用，以及节点数组未变时菜单闭包的更新。 |
| [treeData.test.ts](./__tests__/treeData.test.ts) | `__tests__/treeData.test.ts` | 数据处理测试 | 测试treeDataFactory.ts的同级排序、跨父级移动、整棵子树移动、防环、禁用、重复ID及原数组不被修改。 |

日常使用建议先看README.md和types.ts，了解数据及参数，再看Tree.tsx，最后按需要查看菜单、数据处理或图标文件。

## 文件协作关系与业务边界

| 关系 | 分工 |
| --- | --- |
| 页面 → index.ts → Tree.tsx | 页面通过公共出口导入Tree，传入items、状态与回调；Tree组织整个树的展示和交互。 |
| Tree.tsx → TreeItemMenu.tsx | Tree按节点生成操作配置，菜单组件负责展示操作项和触发回调。 |
| Tree.tsx → treeDataFactory.ts | Tree在拖放时计算新数组并校验层级关系，再通过onItemsChange回传页面。 |
| Tree.tsx → treeIcons.ts | Tree按节点配置的名称查找并渲染图标。 |
| types.ts → 组件与调用页面 | 提供一致的数据和参数类型，供开发时检查与查阅。 |
| __tests__/ → 对应实现 | 测试通过真实组件交互或数据断言验证行为，不参与页面渲染。 |
| 页面/业务Hook → API | 新增、编辑、删除和拖放持久化由业务层处理；基础树负责展示与操作回调。 |

## Demo与原组件备份

以下路径相对于仓库根目录：

| 名称 | 路径/入口 | 用途 |
| --- | --- | --- |
| [组件Demo源码](../../../pages/DocsPage/Components/Docs_tree.tsx) | `apps/hrs-web/src/pages/DocsPage/Components/Docs_tree.tsx` | 演示嵌套数据、图标、尺寸、操作菜单、checkbox选择、拖放与重置。 |
| Demo路由 | `/docs/component/tree` | 组件文档 → 数据展示 → 树形组件。 |
| [原组件备份](../备份树/Tree.tsx) | `apps/hrs-web/src/components/basic/备份树/` | 保留旧组件、说明和测试，作为恢复或对照材料，未接入当前公共出口。 |

备份目录的测试不加入当前Vitest扫描，避免把旧组合接口误认为新契约。新Tree不再导出TreeItem/TreeItemContent/TreeCollection等拼装接口，业务只传嵌套数组。数据字典页面已同步改用新接口；其操作仍走原业务Hook，未开启分组拖放写库。

## 数据结构

```tsx
import { Tree, type TreeNodeDef } from '@components/basic/Tree';

const treeNodesData: TreeNodeDef[] = [
  {
    id: 'system',
    label: '系统管理',
    icon: 'Folder',
    expandedIcon: 'FolderOpen',
    children: [{ id: 'organization', label: '组织人事', icon: 'Users' }],
  },
];

<Tree aria-label="系统分组" items={treeNodesData}
  defaultExpandedKeys={['system']} selectionMode="single" />
```

| 节点字段 | 类型 | 约定 |
| --- | --- | --- |
| id | string / number | 全树唯一；重复id立即报错；数字1与字符串'1'不同 |
| label | string | 名称和键盘文字定位文案，必填 |
| children | TreeNodeDef[] | 递归下级，省略或空数组表示叶节点 |
| icon | string | 内置或自定义注册表的图标名称，区分大小写；省略/未知名称不显示 |
| expandedIcon | string | 展开时替换图标，省略则沿用icon |
| data | 泛型T | 可选原始业务记录，操作回调可直接读取 |
| isDisabled | boolean | 默认false；禁用祖先下的节点也不可操作或移动 |

内置图标名称：Archive、Building2、Database、File、FileCode、FileText、Folder、FolderOpen、Globe、Home、Layers、Package、Settings、Shield、Tag、Users。通过`iconComponentsData={{ MyIcon: MyIconComponent }}`注册其他图标，再传`icon: 'MyIcon'`，无需修改组件内部。采用显式注册避免全量引入图标库。

节点行背景沿用`rounded-sm`小圆角，悬停与选中时保持一致。

纵向间距统一由每个节点自身的上下内边距和最小行高控制，父子节点、同级节点、带/不带操作菜单的节点遵循相同规则；不在根树或展开动画容器额外叠加gap/margin，以免层级之间产生不一致的间隔。

| size | 最小行高 | 上/下内边距（各） | 字体大小 | 字号样式 | 适用规则 |
| --- | --- | --- | --- | --- | --- |
| sm（默认） | 32px | 4px | 12px | `text-xs` | 所有层级统一 |
| md | 36px | 4px | 14px | `text-sm` | 所有层级统一 |
| lg | 40px | 6px | 16px | `text-md` | 所有层级统一 |

项目tailwind.config.js已定义text-md为1rem（默认16px），树节点与操作下拉菜单统一使用上表字号。lg菜单保留24px文字行高，避免从text-base切换为自定义字号后改变菜单布局。

默认内容下，同一size的节点行高一致；展开/收起动画结束后，连续节点之间也保持相同节奏。

选择框统一采用3px小圆角方形，选中态背景也使用相同圆角；single/multiple都保留checkbox外观，不跟随主题的大圆角变成圆形。

## 树属性

支持的参数逐项定义在types.ts的TreeProps中，使用时仍可查看完整的类型、注释及本表。Tree.tsx采用“核心参数显式配置、通用辅助属性透传”：

| 处理方式 | 参数 |
| --- | --- |
| 显式配置 | items、size、selectionMode、showCheckboxes、选中/展开集合与回调、disabledKeys、isDisabled、isDraggable、onItemsChange、nodeActionsFn、nodeActionsLabelFn、iconComponentsData、showGuideLines、renderEmptyState、className、dependencies |
| {...treePropsData}透传 | id、ref、style、aria-label、aria-labelledby、aria-describedby、aria-busy、autoFocus、onAction、reduceMotion、disallowEmptySelection |

透传放在内部显式配置之前，不能覆盖组件生成的拖放、菜单和缓存规则。不自动开放FileTree的全部参数；后续增加参数须同步TreeProps注释和本表，再按用途决定是否显式处理。onItemsChange仅在开启拖放时必填。

| 属性 | 默认值 | 作用 |
| --- | --- | --- |
| items | 必填 | 完整嵌套数组；替换数组即更新，不保留内部数据副本 |
| size | sm | sm/md/lg，分别使用12/14/16px节点文字，缩放行距、缩进、图标及菜单 |
| selectionMode | none | none/single/multiple；single最多一项，multiple支持多项 |
| showCheckboxes | true | 有选择能力时显示checkbox；false改为行选择 |
| selectedKeys | 非受控 | Iterable<Key>或'all'，受控选中集合 |
| defaultSelectedKeys | 无 | 非受控初始选中集合或'all'，只在初始化使用 |
| onSelectionChange | 无 | 接收选中集合或'all'，由调用方更新受控值 |
| disallowEmptySelection | false | 禁止取消最后一个选中项，不自动选择初始节点 |
| expandedKeys | 非受控 | 受控展开集合 |
| defaultExpandedKeys | 全部折叠 | 非受控初始展开集合，只在初始化使用 |
| onExpandedChange | 无 | 接收当前展开的Set<Key> |
| disabledKeys | 无 | 禁用指定节点及其后代 |
| isDisabled | false | 禁用整树，包括节点菜单与拖放 |
| nodeActionsFn | 无 | 接收节点，返回按顺序展示的菜单动作；空数组隐藏入口 |
| nodeActionsLabelFn | 节点名称 · 操作 | 自定义操作按钮的可访问名称，可用于国际化 |
| iconComponentsData | 无 | 扩展/覆盖具名图标，作用于当前树实例 |
| isDraggable | false | 开启当前树内部的拖放 |
| onItemsChange | 开启拖放时必填 | 接收新完整数组和TreeMoveDef，调用方更新items并决定是否请求业务接口 |
| showGuideLines | true | true/false/'hover'，来自FileTree |
| reduceMotion | false | 关闭展开动画，同时尊重系统减少动态效果偏好 |
| id | 无 | 根DOM元素标识 |
| className | 无附加类 | 样式类或接收树状态的类名函数 |
| style | 无附加样式 | 内联样式或接收树状态的样式函数 |
| ref | 无 | 根HTMLDivElement引用 |
| renderEmptyState | 底层行为 | 空树内容的渲染函数 |
| dependencies | 无 | 额外的节点渲染缓存依赖 |
| autoFocus | false | 自动聚焦，支持true/false/first/last |
| onAction | 无 | 节点激活回调，接收节点标识，触发规则沿用底层组件 |
| aria-label / aria-labelledby | 必须提供一种 | 为树提供可访问名称 |
| aria-describedby | 无 | 提供补充说明的元素id |
| aria-busy | 无 | 标记数据更新中，不隐式禁用树 |

选择不级联父子，不自动显示祖先半选。点展开按钮或菜单不会改变选择。节点在当前树内移动时id保持不变，已有选择和展开状态继续按id匹配；业务删除节点时，应在业务层同步清理失效选择。

## 自定义操作菜单

```tsx
<Tree aria-label="组织分组" items={treeNodesData} selectionMode="single"
  showCheckboxes={false}
  nodeActionsFn={treeNodeData => [
    { actionCode: 'add', actionLabel: '新增下级', actionFn: () => openChildEditorFn(treeNodeData.id) },
    { actionCode: 'edit', actionLabel: '编辑', actionFn: () => openNodeEditorFn(treeNodeData.id) },
    { actionCode: 'delete', actionLabel: '删除', variant: 'danger',
      actionFn: () => openNodeDeletionFn(treeNodeData.id) },
  ]} />
```

示例中的open方法由业务方提供。每条动作包含唯一`actionCode`、可访问的`actionLabel`、`actionFn`；可选`title`（有值时渲染分组 Header）、`iconData`、`variant`（default/primary/success/warning/danger）、`isDisabledState`。菜单只触发动作，不内置新增请求、删除确认或权限判断。鼠标悬停/键盘聚焦节点时显示“…”；菜单打开后保持入口可见，触屏常显。

## 拖放与数据归属

```tsx
const [treeNodesData, setTreeNodesFn] = useState<TreeNodeDef[]>(initialTreeNodesData);

<Tree aria-label="可移动分组" items={treeNodesData} isDraggable
  onItemsChange={(treeNextData, treeMoveData) => {
    setTreeNodesFn(treeNextData);
    // 若要持久化，在业务Hook中校验权限并调用接口；失败恢复原树。
    // treeMoveData包含nodeIdsData、targetIdCode与positionCode。
  }} />
```

| 规则 | 行为 |
| --- | --- |
| before / after | 在目标节点前/后按同级插入，可跨父级 |
| on | 移入目标的最后一个子位置；原叶节点可以接收下级 |
| 多选拖放 | 依源树顺序移动，父子同时选中时只移动完整父子树 |
| 防环 | 禁止放到自身或自身后代上/前/后 |
| 禁用 | 禁止移动禁用节点，禁止以禁用节点为目标；继承祖先禁用 |
| 无效或未变位置 | 不回调，不产生数据副本 |
| 外部拖入 | 不接收外部文件或其他Tree实例的数据 |
| 数据写入 | 不修改原数组，不发请求；仅回传完整新数组和实际移动的顶层id |
| 键盘 | 聚焦拖动手柄，Enter/Space开始，Tab切换放置区域、方向键选择位置，Enter放置，Esc取消；遵循底层本地化提示 |
| 鼠标 | 从行左侧的拖动手柄位置拖到目标行或行间；手柄的指针事件由底层透传到可拖动行 |

基础组件不负责业务的最大层级、同级排序字段、授权和数据库事务。数据字典当前仅用树做分组筛选，仍通过编辑表单调整上级，不能因为基础组件支持拖放就直接写入字典表。

## 独立拖拽Demo

`/docs/component/tree`新增“拖拽示例：同级排序与调整上级”区域，手柄常显；使用独立的树数据、最近移动结果和JSON预览，可直接重置。可依次尝试：把“用户管理”拖到“组织管理”后方行间，再把“数据字典”拖到“投研平台”节点上。原多选拖放示例继续保留；两个区域互不影响，均不写入业务接口。

## 验证

2026-11-27验证结果：

| 检查 | 结果 |
| --- | --- |
| 定向Vitest | 5个文件24项通过，覆盖真实FileTree、菜单缓存更新、数据移动、字典Hook及路由清单 |
| 定向ESLint | 本次新增/修改的组件、Demo、字典调用、导航及测试配置检查通过 |
| npm run build | TypeScript与生产构建通过，保留现有分块警告 |
| Chromium交互 | 图标、12/14/16px尺寸、方形checkbox及菜单隔离通过；鼠标多选跨父级移动、键盘移动通过，独立拖拽示例的常显手柄、同级排序、调整上级及重置通过，无页面运行错误 |
| 数据字典回归 | 真实本机system接口下，分组菜单、字体与表格一致性、分类表、字典值抽屉及分页/新增弹窗检查通过 |
| 范围外 | 未执行全量测试/全量lint、CI、新设备完整包安装及正式认证；未验证移动设备实机触控拖放 |

截图保存在仓库外，不合入产品源码；本说明暂无独立英文对应文档。
