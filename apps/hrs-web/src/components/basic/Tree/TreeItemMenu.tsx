/**
 * 树节点的紧凑操作菜单：悬停/聚焦时显示“…”，用 HeroUI Dropdown 承载键盘与焦点管理。
 * 菜单只描述操作，不含业务请求或删除确认。
 */
import type { ReactNode } from 'react';
import type * as React from 'react';
import { cn } from '../../../utils/cn';
import { Dropdown, Header, Separator } from '@heroui/react';
import { Ellipsis } from 'lucide-react';
import { HrsButton } from '../HrsButton';

/** 菜单只描述操作，不包含业务请求或删除确认。 */
export interface TreeMenuActionDef {
  /** 当前菜单内唯一的操作标识。 */
  actionCode: string;
  /** 展示及可访问名称。 */
  actionLabel: string;
  /** 分组标题；有值时在所属分组顶部渲染 Header，无值则不渲染。 */
  title?: string;
  /** 可选装饰图标，由调用方标注aria-hidden。 */
  iconData?: ReactNode;
  /** 操作配色，由 HeroUI MenuItem variant 决定，默认 default。 */
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger';
  /** 选择后回调，由业务方打开表单或确认弹窗。 */
  actionFn: () => void;
  /** 单独禁用一个操作，默认false。 */
  isDisabledState?: boolean;
}

/** TreeItemContent操作插槽的菜单属性。 */
export interface TreeItemMenuProps {
  /** 与树节点一致的尺寸，默认sm。 */
  size?: 'sm' | 'md' | 'lg';
  /** 触发按钮名称，须包含节点名称以区分不同行。 */
  treeMenuLabelMsg: string;
  /** 按展示顺序排列的操作分组；每个子数组渲染为一块，块之间用分隔线隔开。 */
  treeActionsData: TreeMenuActionDef[][];
  /** 写入期间禁用所有菜单操作，默认false。 */
  isTreeMenuDisabledState?: boolean;
}

/** 悬停或聚焦节点时展示“…”；触屏常显，菜单打开后保持入口可见。 */
export function TreeItemMenu({
  size = 'sm',
  treeMenuLabelMsg,
  treeActionsData,
  isTreeMenuDisabledState = false,
}: TreeItemMenuProps) {
  // md/lg触发器均不超过28px，保证lg节点40px行高内还能保留上下各6px内边距。
  const treeMenuSizeClassMsg = size === 'lg' ? 'text-md leading-6' : size === 'md' ? 'text-sm' : 'text-xs';
  // 展平用于计算禁用键；分组仍按二维结构逐块渲染。
  const treeFlatActionsData = treeActionsData.flat();
  // HeroUI Dropdown.Item 的 variant 只支持 default/danger；5 种语义色统一用 class 上色。
  const treeMenuVariantClassData = {
    default: 'text-foreground-dim',
    primary: 'text-primary',
    success: 'text-success',
    warning: 'text-warning',
    danger: 'text-danger',
  } as const;
  return (
    <Dropdown>
      <Dropdown.Trigger>
        <HrsButton
          aria-label={treeMenuLabelMsg}
          size="xs"
          variant="ghost"
          isDisabled={isTreeMenuDisabledState}
          className={cn('shrink-0 rounded-full p-0 text-foreground-dim opacity-0 group-hover/tree-row:opacity-100 group-focus-within/tree-row:opacity-100 group-data-[focus-visible]/tree-row:opacity-100 focus-visible:opacity-100 aria-expanded:opacity-100 [@media(hover:none)]:opacity-100', size === 'sm' ? 'size-6' : 'size-7')}
        >
          <Ellipsis size={size === 'lg' ? 20 : size === 'md' ? 18 : 16} aria-hidden="true" className="outline-none" />
        </HrsButton>
      </Dropdown.Trigger>
      <Dropdown.Popover placement="bottom end" offset={4} className="z-[110] min-w-36 rounded-md border border-subtle bg-elevated p-1 shadow-lg outline-none">
        <Dropdown.Menu
          aria-label={treeMenuLabelMsg}
          disabledKeys={treeFlatActionsData.filter(treeActionData => isTreeMenuDisabledState || treeActionData.isDisabledState).map(treeActionData => treeActionData.actionCode)}
          className={cn(treeMenuSizeClassMsg, 'text-foreground-dim outline-none')}
        >
          {treeActionsData.map((treeActionsGroupData, treeGroupIndexCode) => (
            <Dropdown.Section key={`section-${treeGroupIndexCode}`}>
              {treeActionsGroupData[0]?.title && (
                <Header className="px-3 py-1.5 text-xs font-medium text-foreground-dim">
                  {treeActionsGroupData[0].title}
                </Header>
              )}
              {treeActionsGroupData.map(treeActionData => (
                <Dropdown.Item
                  id={treeActionData.actionCode}
                  textValue={treeActionData.actionLabel}
                  onAction={treeActionData.actionFn}
                  variant={treeActionData.variant === 'danger' ? 'danger' : 'default'}
                  className={cn('flex cursor-pointer items-center gap-2 rounded-md px-3 py-2 outline-none data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50', treeMenuSizeClassMsg, treeMenuVariantClassData[treeActionData.variant ?? 'default'])}
                >
                  {treeActionData.iconData}
                  {treeActionData.actionLabel}
                </Dropdown.Item>
              ))}
            </Dropdown.Section>
          )).reduce<React.ReactNode[]>((treeChildrenData, treeSectionData, treeGroupIndexCode) => {
            if (treeGroupIndexCode > 0) treeChildrenData.push(<Separator key={`separator-${treeGroupIndexCode}`} className="my-1" />);
            treeChildrenData.push(treeSectionData);
            return treeChildrenData;
          }, [])}
        </Dropdown.Menu>
      </Dropdown.Popover>
    </Dropdown>
  );
}
