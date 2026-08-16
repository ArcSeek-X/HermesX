/**
 * TabNav - 通用标签页导航组件
 *
 * 基于 HeroUI 的 Tabs 封装，用于页面内的分段切换（如主区/ETF 云图等）。
 *
 * 特性：
 * - 受控组件：通过 `value` / `onChange` 控制选中态。
 * - 支持 `primary` 与 `secondary` 两种视觉变体。
 * - 内部样式统一通过 HeroUI 的 `data-[slot]` 选择器控制，避免被组件主题类覆盖；
 *   选中指示条（secondary 变体）跟随项目主题色（--primary）。
 * - 支持 `rightSlot` 在标签栏右侧放置自定义内容（如操作按钮）。
 * - 文案不换行，Tab 项使用小/中圆角。
 *
 * 用法示例：
 *   <TabNav
 *     items={[{ value: 'a', label: '概览' }, { value: 'b', label: 'ETF云图' }]}
 *     value={active}
 *     onChange={setActive}
 *     variant="secondary"
 *     ariaLabel="板块切换"
 *   />
 */
import type { Key, ReactNode } from 'react';
import { Tabs } from '@heroui/react';
import { cn } from '../../utils/cn';

export interface TabNavItem<T extends string = string> {
  /** 该 Tab 对应的唯一值（同时作为选中态 key）。 */
  value: T;
  /** Tab 显示文案。 */
  label: string;
  /** 可选的前置图标。 */
  icon?: ReactNode;
  /** 是否禁用该 Tab。 */
  disabled?: boolean;
  /** 单个 Tab 项的自定义 className。 */
  className?: string;
}

export interface TabNavProps<T extends string = string> {
  /** Tab 列表数据。 */
  items: TabNavItem<T>[];
  /** 当前选中的 Tab 值。 */
  value: T;
  /** 选中态变化回调。 */
  onChange: (value: T) => void;
  /** 位于 Tab 右侧的自定义插槽（如操作按钮）。 */
  rightSlot?: ReactNode;
  /** HeroUI Tabs 视觉变体。 */
  variant?: 'primary' | 'secondary';
  /** 容器 className。 */
  className?: string;
  /** 无障碍标签，用于 Tabs.List 的 aria-label。 */
  ariaLabel?: string;
}

export function TabNav<T extends string = string>({
  items,
  value,
  onChange,
  rightSlot,
  variant = 'primary',
  className,
  ariaLabel,
}: TabNavProps<T>) {
  // 收集所有被禁用的 Tab 值，传给 HeroUI 的 disabledKeys
  const disabledKeys = items.filter((item) => item.disabled).map((item) => item.value);

  // 通过 HeroUI 的 data-[slot] 选择器统一控制 Tab 内部样式，
  // 避免直接给 Tabs.Tab 传 className 被组件主题类覆盖。
  const listClassName = cn(
    'gap-2',
    // Tab 项：中等圆角、内边距、文字不换行、颜色过渡
    '**:data-[slot=tabs-tab]:rounded-md',
    '**:data-[slot=tabs-tab]:px-3',
    '**:data-[slot=tabs-tab]:whitespace-nowrap',
    '**:data-[slot=tabs-tab]:transition-colors',

    // 选中指示条：小圆角
    '**:data-[slot=tabs-indicator]:rounded-sm',
    // secondary 变体的指示条跟随项目主题色（青色），覆盖 HeroUI 默认蓝色
    variant === 'secondary' && '**:data-[slot=tabs-indicator]:!bg-[hsl(var(--primary))]',

    // 去掉 Tab 项默认阴影
    '**:data-[slot=tabs-tab]:shadow-none',
    className,
  );

  return (
    <div className={cn('hrs-tab flex items-end justify-between gap-4')}>
      <Tabs
        variant={variant}
        selectedKey={value}
        onSelectionChange={(key: Key) => onChange(key as T)}
        disabledKeys={disabledKeys}
        className="hrs-tab-container"
      >
        <Tabs.ListContainer className="rounded-md">
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
      {rightSlot && <div className="hrs-tab-slot flex shrink-0 items-center pb-1">{rightSlot}</div>}
    </div>
  );
}
