/**
 * @file Tree.test.tsx
 * @description 使用真实React Aria验证树的展开、选择、禁用、键盘及操作按钮，避免只验证静态外观。
 * @author Lensgcx (GaoCangxiong)
 */
import { createRef, useState } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Button } from 'react-aria-components';
import type { Selection } from 'react-aria-components';
import { describe, expect, it, vi } from 'vitest';
import { Tree, TreeCollection, TreeItem, TreeItemContent } from '..';

/** 验证非受控展开及嵌套节点，展开按钮不能误触发节点选择。 */
it('expands children without selecting the parent and preserves refs', async () => {
  /** 选择事件观察器及根DOM引用。 */
  const changeTreeSelectionFn = vi.fn();
  const treeElementRefData = createRef<HTMLDivElement>();
  render(
    <Tree aria-label="分组" selectionMode="single" onSelectionChange={changeTreeSelectionFn} ref={treeElementRefData}>
      <TreeItem id={1} textValue="系统">
        <TreeItemContent>系统</TreeItemContent>
        <TreeItem id={2} textValue="组织"><TreeItemContent>组织</TreeItemContent></TreeItem>
      </TreeItem>
    </Tree>,
  );
  expect(treeElementRefData.current).toHaveAttribute('role', 'treegrid');
  expect(screen.queryByText('组织')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button'));
  expect(await screen.findByText('组织')).toBeInTheDocument();
  expect(changeTreeSelectionFn).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText('组织'));
  await waitFor(() => expect(changeTreeSelectionFn).toHaveBeenCalledOnce());
  // 原生Selection附带范围选择元数据，这里只校验实际选中主键。
  expect([...changeTreeSelectionFn.mock.calls[0][0]]).toEqual([2]);
});

/** 受控选择必须经回调更新；操作按钮与禁用节点不改变选中值。 */
it('keeps controlled selection isolated from row actions and disabled nodes', async () => {
  /** 编辑动作观察器。 */
  const editTreeNodeFn = vi.fn();
  /** 演示业务方按原生选择契约维护受控状态。 */
  function ControlledTree() {
    /** 当前选中节点集合，不使用基础组件内部的业务状态。 */
    const [treeSelectedKeysData, setTreeSelectedKeysFn] = useState<Selection>(new Set([1]));
    return (
      <Tree aria-label="受控分组" selectionMode="single" selectedKeys={treeSelectedKeysData}
        onSelectionChange={setTreeSelectedKeysFn} disabledKeys={[3]}>
        <TreeItem id={1} textValue="系统"><TreeItemContent>系统</TreeItemContent></TreeItem>
        <TreeItem id={2} textValue="组织">
          <TreeItemContent treeActionsData={<Button onPress={editTreeNodeFn}>编辑组织</Button>}>组织</TreeItemContent>
        </TreeItem>
        <TreeItem id={3} textValue="停用"><TreeItemContent>停用</TreeItemContent></TreeItem>
      </Tree>
    );
  }
  render(<ControlledTree />);
  fireEvent.click(screen.getByRole('button', { name: '编辑组织' }));
  expect(editTreeNodeFn).toHaveBeenCalledOnce();
  expect(screen.getByText('系统').closest('[role="row"]')).toHaveAttribute('aria-selected', 'true');
  fireEvent.click(screen.getByText('停用'));
  expect(screen.getByText('系统').closest('[role="row"]')).toHaveAttribute('aria-selected', 'true');
  fireEvent.click(screen.getByText('组织'));
  await waitFor(() => expect(screen.getByText('组织').closest('[role="row"]')).toHaveAttribute('aria-selected', 'true'));
});

/** 验证动态集合、展开受控回调、渲染函数及键盘向右展开能力。 */
it('supports dynamic collections, render props and keyboard expansion', async () => {
  /** 动态节点集合及展开回调观察器。 */
  const treeNodesData = [{ id: 'system', label: '系统' }];
  const changeTreeExpandedFn = vi.fn();
  const { rerender } = render(
    <Tree aria-label="动态分组" items={treeNodesData} expandedKeys={[]} onExpandedChange={changeTreeExpandedFn}>
      {treeNodeData => (
        <TreeItem id={treeNodeData.id} textValue={treeNodeData.label}>
          <TreeItemContent>{treeItemRenderData => `${treeNodeData.label}${treeItemRenderData.isExpanded ? '已展开' : ''}`}</TreeItemContent>
          <TreeCollection items={[{ id: 'org', label: '组织' }]}>
            {treeChildData => <TreeItem id={treeChildData.id} textValue={treeChildData.label}><TreeItemContent>{treeChildData.label}</TreeItemContent></TreeItem>}
          </TreeCollection>
        </TreeItem>
      )}
    </Tree>,
  );
  /** 根节点行由原生组件管理键盘焦点。 */
  const treeRootRowData = screen.getByText('系统').closest('[role="row"]') as HTMLElement;
  treeRootRowData.focus();
  fireEvent.keyDown(treeRootRowData, { key: 'ArrowRight', code: 'ArrowRight' });
  await waitFor(() => expect(changeTreeExpandedFn).toHaveBeenCalledWith(new Set(['system'])));
  expect(screen.queryByText('组织')).not.toBeInTheDocument();
  rerender(<Tree aria-label="空分组" renderEmptyState={() => '没有分组'}>{[]}</Tree>);
  expect(await screen.findByText('没有分组')).toBeInTheDocument();
});

/** 验证外部样式渲染函数仍有效，不被默认主题覆盖。 */
describe('Tree theme overrides', () => {
  it('preserves className functions on root and item', () => {
    render(<Tree aria-label="样式分组" className={() => 'p-8'}>
      <TreeItem id="one" textValue="分组一" className={() => 'rounded-none'}><TreeItemContent>分组一</TreeItemContent></TreeItem>
    </Tree>);
    expect(screen.getByRole('treegrid')).toHaveClass('p-8');
    expect(screen.getByText('分组一').closest('[role="row"]')).toHaveClass('rounded-none');
  });
});
