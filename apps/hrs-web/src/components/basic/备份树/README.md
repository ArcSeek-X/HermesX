# 基础 Tree

用于字典分组等层级选择场景，基于项目已安装的 `react-aria-components`，采用本项目主题。当前 HeroUI 未导出独立 Tree，因此直接复用 React Aria 的集合、选择、展开、键盘导航及可访问性。

节点默认文字与基础Table单元格一致，使用`text-xs`字号和`text-foreground-dim`颜色；选中、悬停、禁用及焦点反馈仍按树的交互状态显示。

TreeItemMenu的“…”按钮、下拉菜单及普通菜单项也采用相同的默认字号和颜色；`isDangerState=true`的删除项保留危险色，字号仍为text-xs。图标继承所在按钮或菜单项的颜色。

```tsx
import { Tree, TreeItem, TreeItemContent } from '@components/basic/Tree';

<Tree aria-label="字典分组" selectionMode="single" defaultExpandedKeys={[1]}>
  <TreeItem id={1} textValue="系统字典">
    <TreeItemContent>系统字典</TreeItemContent>
    <TreeItem id={2} textValue="组织相关">
      <TreeItemContent>组织相关</TreeItemContent>
    </TreeItem>
  </TreeItem>
</Tree>
```

| 组件 | 职责 |
| --- | --- |
| Tree | 根集合与交互，完整继承原生 TreeProps 和 ref |
| TreeItem | 节点身份、textValue、样式、禁用及嵌套节点 |
| TreeItemContent | 级别缩进、展开按钮、名称、图标和右侧操作 |
| TreeItemMenu | 节点“…”操作菜单，复用HrsButton及React Aria菜单/弹层，供操作插槽使用 |
| TreeCollection | 原生 Collection 别名，递归渲染动态 children |
| TreeSection / TreeHeader / TreeLoadMoreItem | 原生扩展出口；高级用法遵循 React Aria 契约 |

原生属性名保持不变：

| 属性 | 约定 |
| --- | --- |
| aria-label / aria-labelledby | 必须提供一种可访问名称 |
| items / children | 使用原生动态集合或静态嵌套，不强制业务节点字段 |
| selectedKeys / onSelectionChange | 受控选择；不传时可使用 defaultSelectedKeys |
| expandedKeys / onExpandedChange | 受控展开；不传时可使用 defaultExpandedKeys；组件不自动展开首行 |
| disabledKeys / isDisabled | 原生禁用语义，不模拟业务状态权限 |
| textValue | 每个 TreeItem 必填，供文字定位；不应拼入操作按钮文案 |
| className / ref | 根和节点完整透传，className 支持原生渲染函数；外部样式最后合并 |
| renderEmptyState | 调用方提供空态，不把加载失败伪装为空集合 |

TreeItemContent 新增插槽均为可选：

- `treeIconData`：名称前图标；装饰图标使用 `aria-hidden`。
- `treeActionsData`：名称后操作，使用具备可访问名称的按钮；选择与按钮操作由原生组件隔离。
- `className`：内容行附加样式。原生 children 仍支持渲染函数及 ref。

需要收拢节点操作时，在`treeActionsData`中传入`TreeItemMenu`：

```tsx
<TreeItemContent treeActionsData={
  <TreeItemMenu
    treeMenuLabelMsg="系统字典操作"
    isTreeMenuDisabledState={isDictWritingState}
    treeActionsData={[
      { actionCode: 'add-child', actionMsg: '新增下级', actionFn: openDictChildEditorFn },
      { actionCode: 'edit', actionMsg: '编辑', actionFn: openDictEditorFn },
      { actionCode: 'delete', actionMsg: '删除', actionFn: openDictDeletionFn, isDangerState: true },
    ]}
  />
}>系统字典</TreeItemContent>
```

入口仅占一个按钮宽度，鼠标移入该内容行或键盘聚焦节点/入口时显示，弹层打开时保持显示；无悬停能力的触屏设备常显。菜单通过Portal展示，避免被树的滚动容器裁切；支持键盘打开、上下移动、Esc关闭，遵循React Aria树的原生规则将焦点返回所属节点。选菜单不改变树选中节点。`actionCode`在同一菜单唯一，`actionMsg`为操作名称，`iconData`可选，`actionFn`只回调业务层，危险操作仍由业务层提供确认弹窗。

键盘交互遵循原生树：上下移动焦点、左右展开/折叠或进入子节点、Home/End移动、文字定位与选择。支持何种选择操作取决于 selectionMode/selectionBehavior；默认值保持原生定义，不擅自强制单选或多选。

基础树不请求接口、不存业务状态、不弹删除确认。字典页面由 API → Hook → 分组业务组件适配数据；只有业务组件认识 dictCategoryName、children 等字段。完整分组数据一次获取，展开不请求。原生提供高级能力不等于字典页已经实现拖拽或懒加载。

新增变量/方法遵循 `.conventions/common/PARAM_NAMING.md`，注释遵循 `CODE_ANNOTATION.md`；原生属性名称为兼容契约保留。文档暂为中文，无对应英文版本。

参考：[React Aria 官方 Tree 文档](https://react-spectrum.adobe.com/react-aria/Tree.html)。
