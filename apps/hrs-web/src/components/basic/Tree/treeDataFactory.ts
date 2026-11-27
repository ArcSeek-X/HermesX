/**
 * 树的只读索引与不可变移动规则，供拖放和边界测试使用。
 */
import type { Key } from 'react-aria-components';
import type { TreeMoveDef, TreeNodeDef } from './types';

/** 节点在源树中的定位信息，ancestorsData只用于当前计算，不写回业务数据。 */
interface TreeLocation<T> {
  nodeData: TreeNodeDef<T>;
  ancestorsData: Key[];
  isDisabledState: boolean;
}

/** 索引整树并验证id唯一；非法数据立即报错，避免选择与拖放定位歧义。 */
export function queryTreeIndexFn<T>(treeNodesData: TreeNodeDef<T>[]) {
  const treeIndexData = new Map<Key, TreeLocation<T>>();
  /** 遍历节点并继承祖先的禁用状态。 */
  function queryTreeLevelFn(treeLevelData: TreeNodeDef<T>[], treeAncestorsData: Key[], isParentDisabledState: boolean) {
    for (const treeNodeData of treeLevelData) {
      if (treeIndexData.has(treeNodeData.id)) throw new Error(`Tree节点id重复：${treeNodeData.id}`);
      const isNodeDisabledState = isParentDisabledState || !!treeNodeData.isDisabled;
      treeIndexData.set(treeNodeData.id, { nodeData: treeNodeData, ancestorsData: treeAncestorsData, isDisabledState: isNodeDisabledState });
      queryTreeLevelFn(treeNodeData.children ?? [], [...treeAncestorsData, treeNodeData.id], isNodeDisabledState);
    }
  }
  queryTreeLevelFn(treeNodesData, [], false);
  return treeIndexData;
}

/**
 * 在源树内移动节点，保留子树及业务数据；移动顺序使用源树顺序，不使用选择顺序。
 * @param treeNodesData 原始嵌套数组，不会被修改。
 * @param treeMoveData 移动节点、目标与相对位置。
 * @returns 新数组；非法移动（环、禁用、未知id）或位置未变化时返回原数组。
 */
export function updateTreeMoveFn<T>(treeNodesData: TreeNodeDef<T>[], treeMoveData: TreeMoveDef): TreeNodeDef<T>[] {
  const treeIndexData = queryTreeIndexFn(treeNodesData);
  const treeTargetData = treeIndexData.get(treeMoveData.targetIdCode);
  const treeSelectedIdsData = new Set(treeMoveData.nodeIdsData);
  if (!treeTargetData || treeTargetData.isDisabledState || treeSelectedIdsData.size === 0) return treeNodesData;
  if ([...treeSelectedIdsData].some(treeIdCode => !treeIndexData.has(treeIdCode) || treeIndexData.get(treeIdCode)?.isDisabledState)) return treeNodesData;
  // 父子同时被选中时保留整棵子树，防止把子节点拆走或重复插入。
  const treeMovingData = [...treeIndexData.values()].filter(treeLocationData => treeSelectedIdsData.has(treeLocationData.nodeData.id)
    && !treeLocationData.ancestorsData.some(treeIdCode => treeSelectedIdsData.has(treeIdCode)));
  const treeMovingIdsData = new Set(treeMovingData.map(treeLocationData => treeLocationData.nodeData.id));
  if (treeMovingIdsData.has(treeMoveData.targetIdCode) || treeTargetData.ancestorsData.some(treeIdCode => treeMovingIdsData.has(treeIdCode))) return treeNodesData;
  /** 删除原位置后再插入，使同父节点重排不受删除前的下标影响。 */
  function deleteTreeSourcesFn(treeLevelData: TreeNodeDef<T>[]): TreeNodeDef<T>[] {
    return treeLevelData.filter(treeNodeData => !treeMovingIdsData.has(treeNodeData.id)).map(treeNodeData => treeNodeData.children
      ? { ...treeNodeData, children: deleteTreeSourcesFn(treeNodeData.children) } : treeNodeData);
  }
  const treeMovedNodesData = treeMovingData.map(treeLocationData => treeLocationData.nodeData);
  /** 递归插入目标层级，允许原叶节点接收下级。 */
  function createTreeDestinationFn(treeLevelData: TreeNodeDef<T>[]): TreeNodeDef<T>[] {
    return treeLevelData.flatMap(treeNodeData => {
      if (treeNodeData.id === treeMoveData.targetIdCode) {
        if (treeMoveData.positionCode === 'on') return [{ ...treeNodeData, children: [...(treeNodeData.children ?? []), ...treeMovedNodesData] }];
        return treeMoveData.positionCode === 'before' ? [...treeMovedNodesData, treeNodeData] : [treeNodeData, ...treeMovedNodesData];
      }
      return [treeNodeData.children ? { ...treeNodeData, children: createTreeDestinationFn(treeNodeData.children) } : treeNodeData];
    });
  }
  const treeNextData = createTreeDestinationFn(deleteTreeSourcesFn(treeNodesData));
  const treeNextIndexData = queryTreeIndexFn(treeNextData);
  // 前序顺序与直接父级均未改变时，保留原引用，避免无效回传。
  const treeBeforeEntriesData = [...treeIndexData];
  const treeAfterEntriesData = [...treeNextIndexData];
  const isTreeChangedState = treeBeforeEntriesData.some(([treeIdCode, treeLocationData], treeIndexCode) => {
    const [treeNextIdCode, treeNextLocationData] = treeAfterEntriesData[treeIndexCode];
    return treeIdCode !== treeNextIdCode || treeLocationData.ancestorsData.at(-1) !== treeNextLocationData.ancestorsData.at(-1);
  });
  return isTreeChangedState ? treeNextData : treeNodesData;
}
