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
 * 1. 倒计时自治：自动刷新倒计时（间隔 refreshInterval，默认 30s）由组件内部管理，
 *    实时模式下按秒递减、归零自动重置并触发 onCountdownEnd 回调；调用方无需关心倒计时 state。
 * 2. 刷新入口分离：onRefresh（手动点击）与 onCountdownEnd（倒计时归零）是两个独立回调，
 *    调用方按需挂载各自的业务刷新逻辑。
 * 3. 三种提示态（左侧均带 Chip 模式徽章：实时=success 绿 / 快照=blue 青蓝）：
 *    - 实时模式（snapshotTime 为空）：显示「实时」徽章 + 「更新于 HH:MM:SS · Ns 后自动刷新」
 *    - 快照模式（snapshotTime 非空）：显示「快照」徽章 + 「更新于 HH:MM:SS · 快照模式：<时间>」
 *      （快照为历史定点，不启动自动刷新倒计时）
 *    - 无更新记录（lastUpdate 为空）：仅显示徽章 + 倒计时 / 快照模式文案
 * 3. 按钮态：loading 时禁用并旋转图标、文案变为「刷新中...」；点击时有 200ms 的 active 缩放动画。
 *
 * 【使用方式】
 *   <DataRefreshBar
 *     lastUpdate={lastUpdate}
 *     snapshotTime={selectedTime}
 *     loading={loading}
 *     onRefresh={handleManualRefresh}
 *     onCountdownEnd={handleAutoRefresh}
 *     refreshInterval={30}
 *   />
 */

import type React from 'react';
import { useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { cn } from '../../utils/cn';
import { HrsButton } from '../basic/HrsButton';
import { Chip } from '../basic/Chip';

/** DataRefreshBar 组件的 Props 定义 */
interface DataRefreshBarProps {
  /** 最后一次数据更新时间；为空时不展示「更新于」 */
  lastUpdate?: Date | null;
  /** 快照时间；非空字符串表示当前处于快照模式，展示「快照模式：<时间>」 */
  snapshotTime?: string;
  /** 是否正在加载，控制按钮禁用与图标旋转 */
  loading?: boolean;
  /** 点击手动刷新按钮时触发的回调（由调用方实现真实的数据刷新） */
  onRefresh: () => void;
  /** 倒计时归零（自动刷新）时触发的回调；可选，未传则仅内部重置倒计时 */
  onCountdownEnd?: () => void;
  /** 自动刷新间隔（秒），仅实时模式有效；默认 30 秒，可通过该参数自定义 */
  refreshInterval?: number;
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
 * @param props.snapshotTime - 快照时间（空串表示实时模式）
 * @param props.loading - 是否加载中
 * @param props.onRefresh - 手动刷新按钮点击回调
 * @param props.onCountdownEnd - 倒计时归零自动刷新回调，可选
 * @param props.refreshInterval - 自动刷新间隔秒数（默认 30，仅实时模式生效）
 * @param props.className - 可选自定义样式
 * @returns 更新时间提示 + 手动刷新按钮的组合控件
 */
export const DataRefreshBar: React.FC<DataRefreshBarProps> = ({
  lastUpdate,
  snapshotTime = '',
  loading = false,
  onRefresh,
  onCountdownEnd,
  refreshInterval = 60,
  className = '',
}) => {
  // 是否处于【快照模式】（snapshotTime 非空）；快照为历史定点，不启动自动刷新倒计时
  const isSnapshot = Boolean(snapshotTime);

  // 按钮点击态：点击后 200ms 触发一次缩放动画，纯 UI 反馈
  const [btnActive, setBtnActive] = useState(false);
  // 内部自管的自动刷新倒计时（秒）；快照模式下为 null（UI 不展示自动刷新）
  const [countdown, setCountdown] = useState<number | null>(
    isSnapshot ? null : refreshInterval,
  );

  /**
   * 实时模式自动刷新：按 refreshInterval 每秒递减倒计时；快照模式不启动定时器。
   * 归零的「重置 + 回调」逻辑放独立 effect（见下方），避免在 state updater 中执行副作用。
   */
  useEffect(() => {
    if (isSnapshot) {
      setCountdown(null);
      return;
    }
    setCountdown(refreshInterval);
    const timer = setInterval(() => {
      setCountdown((prev) => (prev == null ? refreshInterval : prev <= 1 ? 0 : prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [isSnapshot, refreshInterval]);

  /**
   * 倒计时归零监听：countdown 变为 0 时重置为间隔值，并触发外部 onCountdownEnd 回调。
   * 与递减定时器解耦，符合 React 在 effect 中执行副作用的规范。
   */
  useEffect(() => {
    if (countdown === 0) {
      setCountdown(refreshInterval);
      onCountdownEnd?.();
    }
  }, [countdown, refreshInterval, onCountdownEnd]);

  // 手动刷新：触发业务刷新回调并立即重置倒计时
  const handleClick = () => {
    setBtnActive(true);
    setTimeout(() => setBtnActive(false), 200);
    if (!isSnapshot) setCountdown(refreshInterval);
    onRefresh();
  };

  return (
    <div className={cn('flex items-center gap-3', className)}>
      {/* 模式状态徽章：实时（success 绿）/ 快照（blue 青蓝），先于更新时间展示，明确当前数据模式 */}
      <Chip
        size="xs"
        variant="soft"
        color={isSnapshot ? 'blue' : 'success'}
      >
        {isSnapshot ? '快照' : '实时'}
      </Chip>
      {/* 更新时间提示：实时模式显示倒计时，快照模式不显示倒计时（仅展示快照时间） */}
      <span className="text-xs text-muted-text">
        {lastUpdate && `更新于 ${formatTime(lastUpdate)}`}
        {/* 快照模式下不展示「Ns 后自动刷新」，因为快照是历史定点、不会自动轮询 */}
        {!isSnapshot && countdown != null && ` · ${countdown}s 后自动刷新`}
        {isSnapshot && <span className="text-cyan"> · 快照模式：{snapshotTime}</span>}
      </span>
      {/* 手动刷新按钮：触发外部传入的刷新逻辑（onRefresh）。
          采用项目统一按钮 HrsButton（outline / sm），其内置 isLoading 态
          （旋转图标 + loadingText「刷新中...」），无需手写 loading 文案与动画。 */}
      <HrsButton
        size="sm"
        isLoading={loading}
        loadingText="刷新中..."
        onClick={handleClick}
        className={cn('gap-1.5', btnActive && 'scale-95')}
      >
        <RefreshCw className="h-3.5 w-3.5" />
        手动刷新
      </HrsButton>
    </div>
  );
};
