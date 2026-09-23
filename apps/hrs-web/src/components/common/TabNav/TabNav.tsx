/**
 * @file TabNav.tsx
 * @description 通用标签页（Tab）导航组件：基于 HeroUI Tabs 二次封装，用于页面内的分段切换
 *   （如板块分析、行情看板、直播资讯等页面的主区 / 子区切换）。作为受控组件，通过
 *   `value` / `onChange` 管理选中态，并支持 `rightSlot` 在标签栏右侧挂载操作按钮。
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-23
 *
 * 使用场景：
 * - 被各业务页面以 `import { TabNav } from '@components'` 引用，作为分段切换控件。
 * - 依赖：@heroui/react（Tabs 底座）、@/utils/cn（类名合并）。
 *
 * 特性：
 * - 支持 `primary` / `secondary` 两种视觉变体：primary 为填充选中态（带容器圆角），
 *   secondary 为下划线指示条（直角），其指示条跟随项目主题色（--primary）。
 * - 支持 `size` 尺寸档位（xs/sm/md/lg/xl，默认 sm），高度 / 圆角 / 内边距 / 字号 / 字重对齐 HrsButton。
 * - 内部样式统一经 HeroUI 的 `data-[slot]` 选择器控制，避免被组件主题类覆盖；
 *   文案不换行，Tab 项使用小 / 中圆角，容器背景覆盖 HeroUI 默认偏灰底改为项目淡背景。
 *
 * 用法示例：
 *   <TabNav
 *     items={[{ value: 'a', label: '概览' }, { value: 'b', label: 'ETF云图' }]}
 *     value={active}
 *     onChange={setActive}
 *     variant="secondary"
 *     size="sm"
 *     ariaLabel="板块切换"
 *   />
 */
import type { Key, ReactNode } from 'react';
import { Tabs } from '@heroui/react';
import { cn } from '../../../utils/cn';

/**
 * 各尺寸档位对应的 Tab 项 Tailwind 类名（高度、圆角、内边距、字号、字重）。
 * 档位定义与 @/components/basic/HrsButton 保持一致（xs/sm/md/lg/xl），
 * 圆角按档位变化：xs=rounded-full、sm=rounded-xs、md/lg=rounded-sm、xl=rounded-xl；
 * Tab 项与选中指示条（tabs-indicator）圆角均随档位同步，并加 ! 以压过 HeroUI 默认 border-radius（与字号的 ! 同理）。
 * 外层容器（tabs-list-container）的圆角同样随档位同步（用无 `**` 前缀的 data-[slot] 选择器命中元素自身，
 * 仅作用于 primary 变体，secondary 容器保持直角），与 Tab 项作用在不同元素、互不冲突。
 * 注：字号使用 !text-xs / !text-sm，! 用于对抗 index.css 中
 * 未分层的 `button { font: inherit }` 规则，确保字号稳定生效。
 */
const TAB_NAV_SIZE_STYLES = {
  xs: '**:data-[slot=tabs-tab]:!text-[10px] **:data-[slot=tabs-tab]:h-5 **:data-[slot=tabs-indicator]:!rounded-xs data-[slot=tabs-list-container]:!rounded-sm **:data-[slot=tabs-tab]:px-2',
  sm: '**:data-[slot=tabs-tab]:!text-xs **:data-[slot=tabs-tab]:h-6 **:data-[slot=tabs-indicator]:!rounded-xs data-[slot=tabs-list-container]:!rounded-sm **:data-[slot=tabs-tab]:px-3',
  md: '**:data-[slot=tabs-tab]:!text-xs **:data-[slot=tabs-tab]:h-7 **:data-[slot=tabs-indicator]:!rounded-sm data-[slot=tabs-list-container]:!rounded-sm **:data-[slot=tabs-tab]:px-4',
  lg: '**:data-[slot=tabs-tab]:!text-sm **:data-[slot=tabs-tab]:h-8 **:data-[slot=tabs-indicator]:!rounded-sm data-[slot=tabs-list-container]:!rounded-sm **:data-[slot=tabs-tab]:px-5',
  xl: '**:data-[slot=tabs-tab]:!text-sm **:data-[slot=tabs-tab]:h-10 **:data-[slot=tabs-indicator]:!rounded-sm data-[slot=tabs-list-container]:!rounded-md **:data-[slot=tabs-tab]:px-6',
} as const;

export interface TabNavItem<T extends string = string> {
  /** Tab 对应的唯一值（同时作为选中态 key），必填。 */
  value: T;
  /** Tab 显示文案，必填。 */
  label: string;
  /** 可选的前置图标，渲染在文案左侧。 */
  icon?: ReactNode;
  /** 是否禁用该 Tab，默认 false。 */
  disabled?: boolean;
  /** 单个 Tab 项的自定义 className（追加而非覆盖）。 */
  className?: string;
}

export interface TabNavProps<T extends string = string> {
  /** Tab 列表数据，必填；至少包含一个 Tab。 */
  items: TabNavItem<T>[];
  /** 当前选中的 Tab 值，必填；须与 items 中某一项的 value 一致。 */
  value: T;
  /** 选中态变化回调，必填；接收切换后的新 value。 */
  onChange: (value: T) => void;
  /** 位于 Tab 右侧的自定义插槽（如操作按钮），可选；为空时不渲染右侧容器。 */
  rightSlot?: ReactNode;
  /** HeroUI Tabs 视觉变体，默认 'primary'（填充选中态）；可选 'secondary'（下划线指示条）。 */
  variant?: 'primary' | 'secondary';
  /** Tab 尺寸档位，对齐 HrsButton（xs/sm/md/lg/xl），默认 'sm'；控制高度、Tab 项/指示条/外层容器（primary）圆角、内边距、字号、字重。 */
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  /** 外层容器 className，可选。 */
  className?: string;
  /** Tabs 根元素 className，可选。 */
  tabsClassName?: string;
  /** Tabs.List 容器 className，可选（追加到内部统一样式之后）。 */
  tabClassName?: string;
  /** 无障碍标签，用于 Tabs.List 的 aria-label，可选。 */
  ariaLabel?: string;
}

/**
 * 渲染受控标签页导航。
 * 根据 `items` 生成 HeroUI Tabs.Tab 列表，选中态由 `value` 决定，切换时通过 `onChange` 回传新 value；
 * `rightSlot` 不为空时在标签栏右侧挂载自定义内容。组件本身不持有选中态，状态由父组件维护。
 *
 * @returns 包含 Tabs 与可选 rightSlot 的 React 元素
 */
export function TabNav<T extends string = string>({
  items,
  value,
  onChange,
  rightSlot,
  variant = 'primary',
  size = 'sm',
  className,
  tabsClassName,
  tabClassName,
  ariaLabel,
}: TabNavProps<T>) {
  // 收集所有被禁用的 Tab 值，传给 HeroUI 的 disabledKeys
  const disabledKeys = items.filter((item) => item.disabled).map((item) => item.value);

  // 通过 HeroUI 的 data-[slot] 选择器统一控制 Tab 内部样式，
  // 避免直接给 Tabs.Tab 传 className 被组件主题类覆盖。
  const listClassName = cn(
    'gap-2',
    // Tab 项：文字不换行、颜色过渡；圆角由 size 档位统一为 rounded-sm，高度/内边距/字号/字重也由 size 接管
    '**:data-[slot=tabs-tab]:whitespace-nowrap',
    '**:data-[slot=tabs-tab]:transition-colors',

    // 去掉 Tab 项默认阴影
    '**:data-[slot=tabs-tab]:shadow-none',

    // secondary 变体的指示条跟随项目主题色（青色），覆盖 HeroUI 默认蓝色
    variant === 'secondary' && '**:data-[slot=tabs-indicator]:!bg-[hsl(var(--primary))]',
    variant === 'secondary' && '**:data-[slot=tabs-tab]:border-none',

    // 尺寸档位：控制 Tab 项高度/内边距/字号/字重（对齐 HrsButton）
    TAB_NAV_SIZE_STYLES[size],

    tabClassName,
  );

  return (
    <div className={cn('hrs-tab flex items-center justify-between gap-4', className)}>
      <Tabs
        variant={variant}
        selectedKey={value}
        onSelectionChange={(key: Key) => onChange(key as T)}
        disabledKeys={disabledKeys}
        className={cn('hrs-tab-container', tabsClassName)}
      >
        <Tabs.ListContainer className={variant === 'primary' ? TAB_NAV_SIZE_STYLES[size] : undefined}>
          <Tabs.List aria-label={ariaLabel} className={listClassName}>
            {items.map((item) => (
              <Tabs.Tab
                key={item.value}
                id={item.value}
                className={cn('flex items-center gap-2', item.className)}
              >
                {item.icon}
                <span>{item.label}</span>
                <Tabs.Indicator />
              </Tabs.Tab>
            ))}
          </Tabs.List>
        </Tabs.ListContainer>
      </Tabs>
      {rightSlot && <div className="hrs-tab-slot flex shrink-0 items-center">{rightSlot}</div>}
    </div>
  );
}
