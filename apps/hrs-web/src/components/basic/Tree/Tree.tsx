/**
 * 基于 HeroUI Pro FileTree 的数据驱动树。
 * 节点由 items 递归渲染，选择与展开支持受控/非受控模式，拖放结果通过 onItemsChange 回传。
 * 组件不修改输入数据，也不持久化业务状态。
 */
import { useMemo, useRef } from 'react';
import type { Key } from 'react-aria-components';
import { Collection, composeRenderProps, useDragAndDrop } from 'react-aria-components';
import { FileTree } from '@heroui-pro/react/file-tree';
import '@heroui-pro/react/css/components/file-tree.css';
import { cn } from '../../../utils/cn';
import { TreeItemMenu } from './TreeItemMenu';
import { treeIconComponentsData } from './treeIcons';
import { queryTreeIndexFn, updateTreeMoveFn } from './treeDataFactory';
import type { TreeMoveDef, TreeNodeDef, TreeProps } from './types';

/** 树内移动专用类型；外部数据和其他树实例均不触发本树的数据更新。 */
const TREE_DRAG_TYPE_CODE = 'application/x-hermesx-tree-node';

/** 按尺寸统一节点自身的行高、上下内边距与字号，避免层级动画容器或操作按钮造成间距差异。 */
const treeItemSizeClassesData = {
  sm: 'min-h-8 !py-1 !text-xs',
  md: 'min-h-9 !py-1 !text-sm',
  lg: 'min-h-10 !py-1.5 !text-md',
};

/**
 * 渲染嵌套节点；选择与展开支持原生受控/非受控模式，拖放通过 onItemsChange 回传完整新数组。
 * 核心交互参数显式配置，通用辅助属性按 TreeProps 声明透传，并沿用原生组件默认值。
 * @returns 带键盘、焦点、checkbox 及菜单交互的树
 */
export function Tree<T = unknown>({
  /** 嵌套节点数组，必填；替换数组即可更新树，组件不修改入参。 */
  items: treeNodesData,
  /** 节点尺寸，默认 sm，与 Table 单元格字号一致。 */
  size = 'sm',
  /** 选择模式：none 不选择、single 单选、multiple 多选，默认 none。 */
  selectionMode = 'none',
  /** 选择模式非 none 时显示 checkbox，默认 true；false 改为点击行选择。 */
  showCheckboxes = true,
  /** 禁用整棵树，含操作菜单与拖放，默认 false。 */
  isDisabled = false,
  /** 是否允许树内拖放，默认 false；不接受外部树或文件拖入。 */
  isDraggable = false,
  /** 拖放后回传完整新节点数组与移动位置；开启拖放时必填。 */
  onItemsChange: changeTreeItemsFn,
  /** 按节点生成操作菜单，返回空数组时不显示“…”入口。 */
  nodeActionsFn,
  /** 操作菜单按钮的可访问名称，默认“节点名称 · 操作”。 */
  nodeActionsLabelFn,
  /** 按名称扩展或覆盖内置图标，不影响其他树实例。 */
  iconComponentsData = treeIconComponentsData,
  /** 禁用节点标识，后代同时禁用，默认无。 */
  disabledKeys: treeDisabledKeysData,
  /** 根元素样式类，也可按树的原生状态返回类名，默认无附加类。 */
  className: treeClassNameData,
  /** 受控选中标识集合，'all' 表示全选，默认非受控。 */
  selectedKeys: treeSelectedIdsData,
  /** 非受控模式的初始选择，仅初始化使用，默认无选中项。 */
  defaultSelectedKeys: treeDefaultSelectedIdsData,
  /** 选择变化回调，接收选中集合或 'all'，默认不处理。 */
  onSelectionChange: changeTreeSelectionFn,
  /** 受控展开标识集合，默认非受控。 */
  expandedKeys: treeExpandedIdsData,
  /** 非受控模式的初始展开集合，仅初始化使用，默认全部折叠。 */
  defaultExpandedKeys: treeDefaultExpandedIdsData,
  /** 展开变化回调，接收当前展开节点集合，默认不处理。 */
  onExpandedChange: changeTreeExpandedFn,
  /** 层级引导线：true 常显、false 隐藏、'hover' 悬停显示，默认 true。 */
  showGuideLines = true,
  /** 空树内容的渲染函数，默认使用底层组件行为。 */
  renderEmptyState: renderTreeEmptyStateFn,
  /** 额外的节点渲染依赖；原数组未变但外部展示数据变化时用于更新缓存。 */
  dependencies: treeExtraDependenciesData,
  /** 通用辅助属性：id/ref/style、aria-*、autoFocus、onAction、reduceMotion、disallowEmptySelection；完整定义见TreeProps。 */
  ...treePropsData
}: TreeProps<T>) {
  /** 数据索引复用于图标/操作及禁用处理，不维护items的第二份状态。 */
  const treeIndexData = useMemo(() => queryTreeIndexFn(treeNodesData), [treeNodesData]);
  const treeDraggedIdsRefData = useRef<Key[]>([]);
  const treeDisabledIdsData = new Set(treeDisabledKeysData);
  for (const [treeIdCode, treeLocationData] of treeIndexData) {
    if (isDisabled || treeLocationData.isDisabledState || treeLocationData.ancestorsData.some(treeAncestorCode => treeDisabledIdsData.has(treeAncestorCode))) treeDisabledIdsData.add(treeIdCode);
  }
  /** 集合按数据对象缓存节点；显式依赖保证数据未变时菜单闭包、语言、尺寸与禁用仍更新。 */
  const treeContentDependenciesData = [treeNodesData, size, isDisabled, treeDisabledKeysData, nodeActionsFn, nodeActionsLabelFn,
    iconComponentsData, ...(treeExtraDependenciesData ?? [])];
  /** 原生拖放提供鼠标、触屏与键盘入口；业务校验在生成新数组前再次执行。 */
  const { dragAndDropHooks: treeDragHooksData } = useDragAndDrop({
    isDisabled: isDisabled || !isDraggable,
    getItems: treeIdsData => [...treeIdsData].map(treeIdCode => ({ [TREE_DRAG_TYPE_CODE]: String(treeIdCode), 'text/plain': treeIndexData.get(treeIdCode)?.nodeData.label ?? String(treeIdCode) })),
    acceptedDragTypes: [TREE_DRAG_TYPE_CODE],
    getAllowedDropOperations: () => ['move'],
    onDragStart: treeEventData => { treeDraggedIdsRefData.current = [...treeEventData.keys]; },
    onDragEnd: () => { treeDraggedIdsRefData.current = []; },
    getDropOperation: treeTargetData => {
      if (treeTargetData.type !== 'item' || treeDraggedIdsRefData.current.length === 0
        || treeDisabledIdsData.has(treeTargetData.key) || treeDraggedIdsRefData.current.some(treeIdCode => treeDisabledIdsData.has(treeIdCode))) return 'cancel';
      const treeNextData = updateTreeMoveFn(treeNodesData, { nodeIdsData: treeDraggedIdsRefData.current, targetIdCode: treeTargetData.key, positionCode: treeTargetData.dropPosition });
      return treeNextData === treeNodesData ? 'cancel' : 'move';
    },
    onMove: treeEventData => {
      if (isDisabled || !isDraggable || treeDisabledIdsData.has(treeEventData.target.key) || [...treeEventData.keys].some(treeIdCode => treeDisabledIdsData.has(treeIdCode))) return;
      const treeMoveData: TreeMoveDef = { nodeIdsData: [...treeEventData.keys], targetIdCode: treeEventData.target.key, positionCode: treeEventData.target.dropPosition };
      const treeNextData = updateTreeMoveFn(treeNodesData, treeMoveData);
      if (treeNextData !== treeNodesData) {
        // 回调只包含实际移动的顶层节点，保持源树顺序。
        treeMoveData.nodeIdsData = [...treeIndexData.values()].filter(treeLocationData => treeEventData.keys.has(treeLocationData.nodeData.id)
          && !treeLocationData.ancestorsData.some(treeIdCode => treeEventData.keys.has(treeIdCode))).map(treeLocationData => treeLocationData.nodeData.id);
        changeTreeItemsFn?.(treeNextData, treeMoveData);
      }
    },
  });

  /** 将每一层数组交给Collection，FileTree负责节点内容和可访问的展开按钮。 */
  function renderTreeNodeFn(treeNodeData: TreeNodeDef<T>): React.ReactElement {
    const treeActionsData = nodeActionsFn?.(treeNodeData) ?? [];
    const hasTreeActionsState = treeActionsData.some(treeActionsGroupData => treeActionsGroupData.length > 0);
    const isNodeDisabledState = treeDisabledIdsData.has(treeNodeData.id);
    return (
      <FileTree.Item
        id={treeNodeData.id}
        value={treeNodeData}
        textValue={treeNodeData.label}
        className={cn(
          'group/tree-row min-w-0 !rounded-sm !text-foreground-dim data-[selected]:!bg-primary/10 data-[focus-visible]:!ring-primary',
          treeItemSizeClassesData[size],
        )}
        icon={treeRenderData => {
          const treeIconNameCode = treeRenderData.isExpanded ? treeNodeData.expandedIcon ?? treeNodeData.icon : treeNodeData.icon;
          const TreeNodeIcon = treeIconNameCode ? iconComponentsData[treeIconNameCode] ?? treeIconComponentsData[treeIconNameCode] : undefined;
          return TreeNodeIcon ? <TreeNodeIcon aria-hidden className="shrink-0 text-foreground-dim" /> : null;
        }}
        title={
          <span className="flex min-w-0 items-center gap-1">
            <span className="min-w-0 flex-1 truncate">{treeNodeData.label}</span>
            {hasTreeActionsState && <TreeItemMenu
              size={size}
              treeMenuLabelMsg={nodeActionsLabelFn?.(treeNodeData) ?? `${treeNodeData.label} · 操作`}
              treeActionsData={treeActionsData}
              isTreeMenuDisabledState={isNodeDisabledState}
            />}
          </span>
        }
      >
        <Collection items={treeNodeData.children ?? []} dependencies={treeContentDependenciesData}>{renderTreeNodeFn}</Collection>
      </FileTree.Item>
    );
  }

  return (
    <FileTree
      {...treePropsData}
      items={treeNodesData}
      dependencies={treeContentDependenciesData}
      size={size}
      selectionMode={selectionMode}
      selectedKeys={treeSelectedIdsData}
      defaultSelectedKeys={treeDefaultSelectedIdsData}
      onSelectionChange={changeTreeSelectionFn}
      expandedKeys={treeExpandedIdsData}
      defaultExpandedKeys={treeDefaultExpandedIdsData}
      onExpandedChange={changeTreeExpandedFn}
      showGuideLines={showGuideLines}
      renderEmptyState={renderTreeEmptyStateFn}
      selectionBehavior={showCheckboxes ? 'toggle' : 'replace'}
      disabledKeys={treeDisabledIdsData}
      disabledBehavior="all"
      dragAndDropHooks={isDraggable ? treeDragHooksData : undefined}
      className={composeRenderProps(treeClassNameData, treeClassNameMsg => cn(
        'hrs-tree min-w-0 text-foreground-dim [&_[data-slot=file-tree-label]]:!text-foreground-dim',
        '[&_[data-slot=file-tree-item-content]]:min-w-0 [&_[data-slot=file-tree-label]]:min-w-0',
        // 固定小圆角，避免全局主题的大圆角把checkbox渲染为圆形。
        '[&_[data-slot=checkbox-control]]:!rounded-[3px] [&_[data-slot=checkbox-control]]:before:!rounded-[3px]',
        '[&_[data-slot=file-tree-drag-handle]]:focus-visible:!opacity-100 [@media(hover:none)]:[&_[data-slot=file-tree-drag-handle]]:!opacity-60',
        treeClassNameMsg,
      ))}
    >
      {renderTreeNodeFn}
    </FileTree>
  );
}
