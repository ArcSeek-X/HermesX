/**
 * @file Tree.tsx
 * @description 基础树组件：基于已安装的React Aria Tree封装主题样式，供字典分组等层级选择场景复用。
 * 选择、展开、键盘导航和可访问性由原生组件管理；本层不请求接口、不转换业务数据。
 * @author Lensgcx (GaoCangxiong)
 */
import type { ComponentProps, ReactNode } from 'react';
import {
  Button as AriaButton,
  Tree as AriaTree,
  TreeItem as AriaTreeItem,
  TreeItemContent as AriaTreeItemContent,
  composeRenderProps,
} from 'react-aria-components';
import { ChevronRight } from 'lucide-react';
import { cn } from '../../../utils/cn';

/** 每级缩进像素，保证同级节点名称与展开占位对齐。 */
const TREE_INDENT_PX = 16;

/** 原生树属性及ref，完整保留集合、受控/非受控选择与展开、事件和空态能力。 */
export type TreeProps<T = object> = ComponentProps<typeof AriaTree<T>>;

/** 原生节点属性及ref；节点id须在整棵树唯一，textValue用于键盘文字定位。 */
export type TreeItemProps<T = object> = ComponentProps<typeof AriaTreeItem<T>>;

/** 节点内容属性：原生children支持静态内容或渲染函数，其余新增插槽均可省略。 */
export type TreeItemContentProps = ComponentProps<typeof AriaTreeItemContent> & {
  /** 内容行附加样式，默认无；合并在内部样式之后。 */
  className?: string;
  /** 名称前的图标插槽，默认不显示；纯装饰图标由调用方标注aria-hidden。 */
  treeIconData?: ReactNode;
  /** 名称后的操作插槽，默认不显示；业务方提供具名按钮，事件不用于选择节点。 */
  treeActionsData?: ReactNode;
};

/**
 * 渲染基础树，保留原生属性与ref，调用方须提供aria-label或aria-labelledby。
 * @param treePropsData 树属性，数据集合及交互模式由调用方决定。
 * @returns 带项目主题样式的原生树，不修改入参或业务状态。
 */
export function Tree<T = object>(treePropsData: TreeProps<T>) {
  return (
    <AriaTree
      {...treePropsData}
      className={composeRenderProps(treePropsData.className, treeClassNameMsg => cn(
        'hrs-tree min-w-0 outline-none text-xs text-foreground-dim',
        treeClassNameMsg,
      ))}
    />
  );
}

/**
 * 渲染树节点；子节点仍按原生TreeItem/Collection组合，不在此复制业务递归逻辑。
 * @param treeItemPropsData 节点属性，id、textValue及children遵循原生契约。
 * @returns 保留选择、禁用和焦点反馈的节点。
 */
export function TreeItem<T = object>(treeItemPropsData: TreeItemProps<T>) {
  return (
    <AriaTreeItem
      {...treeItemPropsData}
      className={composeRenderProps(treeItemPropsData.className, treeItemClassNameMsg => cn(
        'hrs-tree__item group/tree-item my-0.5 rounded-md outline-none',
        'data-[hovered]:bg-muted data-[selected]:bg-primary/10 data-[selected]:text-primary',
        'data-[focus-visible]:ring-2 data-[focus-visible]:ring-primary',
        'data-[disabled]:opacity-50',
        treeItemClassNameMsg,
      ))}
    />
  );
}

/**
 * 渲染带缩进、展开按钮和操作插槽的节点内容。
 * @param treeContentPropsData 内容属性；children函数接收原生节点状态，支持按展开状态绘制图标等内容。
 * @returns 节点内容；折叠与选择事件由React Aria协调，叶节点保留等宽占位。
 */
export function TreeItemContent({
  className: treeContentClassNameMsg,
  treeIconData,
  treeActionsData,
  ...treeContentPropsData
}: TreeItemContentProps) {
  return (
    <AriaTreeItemContent {...treeContentPropsData}>
      {treeItemRenderData => (
        <div
          className={cn('hrs-tree__content group/tree-row flex min-w-0 items-center gap-1 py-1 pr-2', treeContentClassNameMsg)}
          style={{ paddingInlineStart: (treeItemRenderData.level - 1) * TREE_INDENT_PX }}
        >
          {treeItemRenderData.hasChildItems ? (
            /* chevron插槽从原生上下文获得展开行为及本地化可访问名称。 */
            <AriaButton
              slot="chevron"
              className="flex size-6 shrink-0 items-center justify-center rounded outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-primary"
            >
              <ChevronRight
                aria-hidden="true"
                className={cn('size-3.5 transition-transform', treeItemRenderData.isExpanded && 'rotate-90')}
              />
            </AriaButton>
          ) : <span aria-hidden="true" className="size-6 shrink-0" />}
          {treeIconData}
          <span className="min-w-0 flex-1 truncate">
            {typeof treeContentPropsData.children === 'function'
              ? treeContentPropsData.children(treeItemRenderData)
              : treeContentPropsData.children}
          </span>
          {treeActionsData && <span className="flex shrink-0 items-center gap-1">{treeActionsData}</span>}
        </div>
      )}
    </AriaTreeItemContent>
  );
}
