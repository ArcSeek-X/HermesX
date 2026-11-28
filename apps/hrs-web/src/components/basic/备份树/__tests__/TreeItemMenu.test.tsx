/**
 * @file TreeItemMenu.test.tsx
 * @description 验证真实树与菜单组合时的选择隔离、键盘返回及禁用行为。
 * @author Lensgcx (GaoCangxiong)
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { Tree, TreeItem, TreeItemContent, TreeItemMenu } from '..';

/** 菜单操作不能选择其所属行，也不能触发其他动作。 */
it('runs the chosen action without changing tree selection', async () => {
  const changeTreeSelectionFn = vi.fn();
  const editTreeGroupFn = vi.fn();
  const deleteTreeGroupFn = vi.fn();
  render(
    <Tree aria-label="分组" selectionMode="single" selectedKeys={[1]} onSelectionChange={changeTreeSelectionFn}>
      <TreeItem id={1} textValue="系统"><TreeItemContent>系统</TreeItemContent></TreeItem>
      <TreeItem id={2} textValue="投研">
        <TreeItemContent treeActionsData={
          <TreeItemMenu treeMenuLabelMsg="投研操作" treeActionsData={[
            { actionCode: 'edit', actionMsg: '编辑', actionFn: editTreeGroupFn },
            { actionCode: 'delete', actionMsg: '删除', actionFn: deleteTreeGroupFn, isDangerState: true },
          ]} />
        }>投研</TreeItemContent>
      </TreeItem>
    </Tree>,
  );
  fireEvent.click(screen.getByRole('button', { name: '投研操作' }));
  fireEvent.click(await screen.findByRole('menuitem', { name: '编辑' }));
  expect(editTreeGroupFn).toHaveBeenCalledOnce();
  expect(deleteTreeGroupFn).not.toHaveBeenCalled();
  expect(changeTreeSelectionFn).not.toHaveBeenCalled();
  expect(screen.getByText('系统').closest('[role="row"]')).toHaveAttribute('aria-selected', 'true');
  await waitFor(() => expect(screen.queryByRole('menu')).not.toBeInTheDocument());
});

/** Esc关闭弹层后遵循树的原生焦点规则返回所属节点。 */
it('closes with Escape and restores focus within the originating tree node', async () => {
  render(<Tree aria-label="分组" selectionMode="single">
    <TreeItem id={1} textValue="系统">
      <TreeItemContent treeActionsData={<TreeItemMenu treeMenuLabelMsg="系统操作" treeActionsData={[
        { actionCode: 'edit', actionMsg: '编辑', actionFn: vi.fn() },
      ]} />}>系统</TreeItemContent>
    </TreeItem>
  </Tree>);
  const treeMenuTriggerData = screen.getByRole('button', { name: '系统操作' });
  treeMenuTriggerData.focus();
  fireEvent.keyDown(treeMenuTriggerData, { key: 'Enter', code: 'Enter' });
  fireEvent.keyUp(treeMenuTriggerData, { key: 'Enter', code: 'Enter' });
  const treeMenuData = await screen.findByRole('menu');
  fireEvent.keyDown(treeMenuData, { key: 'Escape', code: 'Escape' });
  await waitFor(() => expect(screen.queryByRole('menu')).not.toBeInTheDocument());
  await waitFor(() => expect(screen.getByRole('row', { name: '系统' })).toHaveFocus());
});

/** 写入期间禁用入口，避免并行进入另一个增删改流程。 */
it('does not open while disabled', () => {
  render(<TreeItemMenu treeMenuLabelMsg="系统操作" isTreeMenuDisabledState treeActionsData={[
    { actionCode: 'edit', actionMsg: '编辑', actionFn: vi.fn() },
  ]} />);
  const treeMenuTriggerData = screen.getByRole('button', { name: '系统操作' });
  expect(treeMenuTriggerData).toBeDisabled();
  fireEvent.click(treeMenuTriggerData);
  expect(screen.queryByRole('menu')).not.toBeInTheDocument();
});
