/**
 * ===================================
 * 通用刷新工具条组件（DataRefreshBar）
 * ===================================
 *
 * 【功能介绍】
 * 统一的「更新时间提示 + 手动刷新按钮」组合控件，提炼自板块分析页头部。
 * 适用于任何需要展示「最近更新时间 / 自动刷新倒计时 / 快照模式」并对外提供手动刷新入口的页面。
 *
 * 【设计要点】
 * 1. 展示与行为分离：组件本身只负责 UI 与点击动画，具体的数据刷新逻辑通过 onRefresh 回调交给调用方，
 *    因此不耦合任何业务状态（如倒计时、快照时间、加载逻辑），可被任意页面复用。
 * 2. 三种提示态：
 *    - 实时模式（snapshotTime 为空）：显示「更新于 HH:MM:SS · Ns 后自动刷新」
 *    - 快照模式（snapshotTime 非空）：显示「更新于 HH:MM:SS · 快照模式：<时间>」
 *    - 无更新记录（lastUpdate 为空）：仅显示倒计时 / 快照模式文案
 * 3. 按钮态：loading 时禁用并旋转图标、文案变为「刷新中...」；点击时有 200ms 的 active 缩放动画。
 *
 * 【使用方式】
 *   <DataRefreshBar
 *     lastUpdate={lastUpdate}
 *     countdown={countdown}
 *     snapshotTime={selectedTime}
 *     loading={loading}
 *     onRefresh={handleRefreshAll}
 *     onCountdownEnd={handleCountdownEnd}
 *   />
 */

import type React from 'react';
import { useEffect, useRef, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { cn } from '../../utils/cn';
import { Button } from '../basic/Button';

/** DataRefreshBar 组件的 Props 定义 */
interface DataRefreshBarProps {
  /** 最后一次数据更新时间；为空时不展示「更新于」 */
  lastUpdate?: Date | null;
  /** 自动刷新倒计时（秒）；实时模式下展示「Ns 后自动刷新」。当值从正数变为 0 时触发 onCountdownEnd */
  countdown?: number;
  /** 快照时间；非空字符串表示当前处于快照模式，展示「快照模式：<时间>」 */
  snapshotTime?: string;
  /** 是否正在加载，控制按钮禁用与图标旋转 */
  loading?: boolean;
  /** 点击手动刷新按钮时触发的回调（由调用方实现真实的数据刷新） */
  onRefresh: () => void;
  /** 倒计时结束（countdown 从正数递减到 0）时触发的回调；可选，未传则不触发 */
  onCountdownEnd?: () => void;
  /** 自定义 CSS 类名，用于覆盖默认布局（如对齐、外边距） */
  className?: string;
}

/**
 * 将 Date 格式化为 HH:MM:SS（24 小时制）
 * 组件内部默认实现，调用方无需自行传入格式化函数。
 */
const formatTime = (date: Date): string => {
  return date.toLocaleTimeString('zh-CN', { hour12: false });
};

/**
 * 通用刷新工具条组件
 *
 * @param props - 组件属性
 * @param props.lastUpdate - 最后更新时间
 * @param props.countdown - 倒计时秒数
 * @param props.snapshotTime - 快照时间（空串表示实时模式）
 * @param props.loading - 是否加载中
 * @param props.onRefresh - 手动刷新回调
 * @param props.onCountdownEnd - 倒计时结束（countdown 递减到 0）回调，可选
 * @param props.className - 可选自定义样式
 * @returns 更新时间提示 + 手动刷新按钮的组合控件
 */
export const DataRefreshBar: React.FC<DataRefreshBarProps> = ({
  lastUpdate,
  countdown,
  snapshotTime = '',
  loading = false,
  onRefresh,
  onCountdownEnd,
  className = '',
}) => {
  // 按钮点击态：点击后 200ms 触发一次缩放动画，纯 UI 反馈
  const [btnActive, setBtnActive] = useState(false);
  // 记录上一次的 countdown，用于检测「从正数递减到 0」的跳变
  const prevCountdownRef = useRef<number | undefined>(undefined);

  /**
   * 倒计时结束监听：当 countdown 从正数（>0）变为 0 时，触发 onCountdownEnd 回调。
   * 调用方需在倒计时归零时把 countdown 置为 0（而非立即重置）以触发该回调。
   */
  useEffect(() => {
    const prev = prevCountdownRef.current;
    if (onCountdownEnd && prev != null && prev > 0 && countdown === 0) {
      onCountdownEnd();
    }
    prevCountdownRef.current = countdown;
  }, [countdown, onCountdownEnd]);

  const handleClick = () => {
    setBtnActive(true);
    setTimeout(() => setBtnActive(false), 200);
    onRefresh();
  };

  // 是否处于快照模式（selectedTime 非空）
  const isSnapshot = Boolean(snapshotTime);

  return (
    <div className={cn('flex items-center gap-3', className)}>
      {/* 更新时间提示：实时模式显示倒计时，快照模式显示快照时间 */}
      <span className="text-xs text-muted-text">
        {lastUpdate && `更新于 ${formatTime(lastUpdate)}`}
        {!isSnapshot && countdown != null && ` · ${countdown}s 后自动刷新`}
        {isSnapshot && <span className="text-cyan"> · 快照模式：{snapshotTime}</span>}
      </span>
      {/* 手动刷新按钮：触发外部传入的刷新逻辑
          注意：不把页面级 loading 透传给 Button 的 isLoading，否则 loading 期间按钮被
          disabled 会吞掉点击（isLoading -> disabled + pointer-events-none）。
          这里 loading 仅用于图标旋转与文案提示，点击始终可达，保证手动刷新一定触发。 */}
      <Button
        variant="outline"
        size="sm"
        onClick={handleClick}
        className={cn(
          'inline-flex items-center gap-1.5 transition-all duration-150',
          btnActive
            ? 'border-cyan/60 bg-cyan/15 text-cyan scale-95'
            : 'hover:text-foreground hover:border-cyan/50',
          loading && 'opacity-70',
        )}
      >
        <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
        {loading ? '刷新中...' : '手动刷新'}
      </Button>
    </div>
  );
};
