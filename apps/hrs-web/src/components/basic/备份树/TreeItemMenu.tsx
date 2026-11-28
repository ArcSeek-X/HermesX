/**
 * @file TreeItemMenu.tsx
 * @description 树节点的紧凑操作菜单，复用项目按钮和React Aria的弹层、键盘与焦点管理。
 * @author Lensgcx (GaoCangxiong)
 */
import type { ReactNode } from 'react';
import { Menu, MenuItem, MenuTrigger, Popover } from 'react-aria-components';
import { Ellipsis } from 'lucide-react';
import { HrsButton } from '../HrsButton';

/** 菜单只描述操作，不包含业务请求或删除确认。 */
export interface TreeMenuActionDef {
  /** 当前菜单内唯一的操作标识。 */
  actionCode: string;
  /** 展示及可访问名称。 */
  actionMsg: string;
  /** 可选装饰图标，由调用方标注aria-hidden。 */
  iconData?: ReactNode;
  /** 危险操作采用删除语义颜色，默认false。 */
  isDangerState?: boolean;
  /** 选择后回调，由业务方打开表单或确认弹窗。 */
  actionFn: () => void;
}

/** TreeItemContent操作插槽的菜单属性。 */
export interface TreeItemMenuProps {
  /** 触发按钮名称，须包含节点名称以区分不同行。 */
  treeMenuLabelMsg: string;
  /** 按展示顺序排列的操作。 */
  treeActionsData: TreeMenuActionDef[];
  /** 写入期间禁用所有菜单操作，默认false。 */
  isTreeMenuDisabledState?: boolean;
}

/** 悬停或聚焦节点时展示“…”；触屏常显，菜单打开后保持入口可见。 */
export function TreeItemMenu({
  treeMenuLabelMsg,
  treeActionsData,
  isTreeMenuDisabledState = false,
}: TreeItemMenuProps) {
  return (
    <MenuTrigger>
      <HrsButton
        aria-label={treeMenuLabelMsg}
        size="xs"
        variant="ghost"
        isDisabled={isTreeMenuDisabledState}
        className="size-7 rounded-full p-0 text-foreground-dim opacity-0 group-hover/tree-row:opacity-100 group-focus-within/tree-row:opacity-100 group-data-[focus-visible]/tree-item:opacity-100 focus-visible:opacity-100 aria-expanded:opacity-100 [@media(hover:none)]:opacity-100"
      >
        <Ellipsis size={16} aria-hidden="true" />
      </HrsButton>
      <Popover
        placement="bottom end"
        offset={4}
        className="z-[110] min-w-36 rounded-xl border border-subtle bg-elevated p-1 shadow-lg outline-none"
      >
        <Menu
          aria-label={treeMenuLabelMsg}
          items={treeActionsData}
          disabledKeys={isTreeMenuDisabledState ? treeActionsData.map(treeActionData => treeActionData.actionCode) : []}
          className="text-xs text-foreground-dim outline-none"
        >
          {treeActionData => (
            <MenuItem
              id={treeActionData.actionCode}
              textValue={treeActionData.actionMsg}
              onAction={treeActionData.actionFn}
              className={`flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-xs outline-none data-[focused]:bg-muted data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50 ${treeActionData.isDangerState ? 'text-danger' : 'text-foreground-dim'}`}
            >
              {treeActionData.iconData}
              {treeActionData.actionMsg}
            </MenuItem>
          )}
        </Menu>
      </Popover>
    </MenuTrigger>
  );
}
