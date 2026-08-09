import type React from 'react';
import { useEffect, useRef, useState, useCallback } from 'react';
import * as echarts from 'echarts';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import type { SectorNode } from '../../api/sectorData';

type SectorTreemapProps = {
  data: SectorNode[];
  onSectorClick?: (sectorCode: string, sectorName: string) => void;
  height?: string;
};

/**
 * 红绿渐变色（参考时到量化风格）
 * 大涨=深红 → 小涨=浅红 → 平盘=灰 → 小跌=浅绿 → 大跌=深绿
 */
function getColor(changePercent: number | undefined | null): string {
  if (changePercent == null || Number.isNaN(changePercent)) return '#555555';
  if (changePercent > 3) return '#8B0000';
  if (changePercent > 1) return '#CC3333';
  if (changePercent > 0) return '#DD6666';
  if (changePercent > -1) return '#66AA66';
  if (changePercent > -3) return '#338833';
  return '#116611';
}

function formatPercent(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return '--';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

/** 递归为每个节点预计算颜色和标签文本 */
function applyColors(nodes: SectorNode[]): SectorNode[] {
  return nodes.map((node) => {
    const percentText = formatPercent(node.changePercent);
    const colored: SectorNode = {
      ...node,
      itemStyle: {
        color: getColor(node.changePercent),
      },
      label: {
        show: true,
        formatter: `${node.name || ''}\n${percentText}`,
      },
    };
    if (node.children) {
      colored.children = applyColors(node.children);
    }
    return colored;
  });
}

/** 判断数据是否为扁平结构（无 children） */
function isFlatData(nodes: SectorNode[]): boolean {
  return nodes.length > 0 && !nodes[0].children;
}

// 离散缩放级别（参考 52etf.site）
const ZOOM_LEVELS = [1, 1.5, 2, 2.5, 3, 3.5, 4];

/** 找到最接近的缩放级别索引 */
function findClosestZoomLevel(scale: number): number {
  let closest = 0;
  let minDiff = Math.abs(ZOOM_LEVELS[0] - scale);
  for (let i = 1; i < ZOOM_LEVELS.length; i++) {
    const diff = Math.abs(ZOOM_LEVELS[i] - scale);
    if (diff < minDiff) {
      minDiff = diff;
      closest = i;
    }
  }
  return closest;
}

export const SectorTreemap: React.FC<SectorTreemapProps> = ({
  data,
  onSectorClick,
  height = '600px',
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const { language } = useUiLanguage();
  const [scale, setScale] = useState(1);
  const [translate, setTranslate] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });

  // 用 ref 存储最新值，避免事件监听器闭包捕获旧值
  const scaleRef = useRef(1);
  const translateRef = useRef({ x: 0, y: 0 });

  // 缩放动画状态（参考 52etf.site 的 100ms 动画）
  const animating = useRef(false);
  const animStart = useRef({ scale: 1, x: 0, y: 0 });
  const animTarget = useRef({ scale: 1, x: 0, y: 0 });
  const animFrame = useRef<number | null>(null);

  // 处理鼠标滚轮缩放（参考 52etf.site 的离散缩放级别 + 鼠标位置基准）
  const lastWheelTime = useRef(0);

  // 钳制偏移量，防止平移超出边界
  const clampTranslate = useCallback((x: number, y: number, currentScale: number) => {
    const container = containerRef.current;
    if (!container) return { x, y };
    const rect = container.getBoundingClientRect();
    const containerWidth = rect.width;
    const containerHeight = rect.height;
    const chartWidth = containerWidth * currentScale;
    const chartHeight = containerHeight * currentScale;
    // 限制偏移范围：不能超出容器边界
    const maxX = 0;
    const minX = containerWidth - chartWidth;
    const maxY = 0;
    const minY = containerHeight - chartHeight;
    return {
      x: Math.min(maxX, Math.max(minX, x)),
      y: Math.min(maxY, Math.max(minY, y)),
    };
  }, []);

  // 执行缩放动画（用 ref 读取最新值，避免依赖 scale/translate 导致频繁重建）
  const animateTo = useCallback((targetScale: number, targetX: number, targetY: number) => {
    // 取消之前的动画
    if (animFrame.current) {
      cancelAnimationFrame(animFrame.current);
    }

    animStart.current = { scale: scaleRef.current, x: translateRef.current.x, y: translateRef.current.y };
    animTarget.current = { scale: targetScale, x: targetX, y: targetY };
    animating.current = true;

    const startTime = Date.now();
    const duration = 100; // 100ms 动画（参考 52etf.site）

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // 使用 cubic ease-out 曲线（参考 52etf.site 的 `1-Math.pow(1-n,3)`）
      const eased = 1 - Math.pow(1 - progress, 3);

      const currentScale = animStart.current.scale + (animTarget.current.scale - animStart.current.scale) * eased;
      const currentX = animStart.current.x + (animTarget.current.x - animStart.current.x) * eased;
      const currentY = animStart.current.y + (animTarget.current.y - animStart.current.y) * eased;

      // 钳制偏移量
      const clamped = clampTranslate(currentX, currentY, currentScale);

      setScale(currentScale);
      setTranslate({ x: clamped.x, y: clamped.y });

      if (progress < 1) {
        animFrame.current = requestAnimationFrame(animate);
      } else {
        animating.current = false;
        animFrame.current = null;
      }
    };

    animFrame.current = requestAnimationFrame(animate);
  }, [clampTranslate]);

  // 同步 ref 与 state（必须在 wheel listener 之前）
  useEffect(() => {
    scaleRef.current = scale;
  }, [scale]);

  useEffect(() => {
    translateRef.current = translate;
  }, [translate]);

  // 用 ref 存储最新的 animateTo（必须在 wheel listener 之前）
  const animateToRef = useRef(animateTo);
  useEffect(() => {
    animateToRef.current = animateTo;
  }, [animateTo]);

  // 用 ref 存储最新的 clampTranslate（必须在 wheel listener 之前）
  const clampTranslateRef = useRef(clampTranslate);
  useEffect(() => {
    clampTranslateRef.current = clampTranslate;
  }, [clampTranslate]);

  // 使用原生事件监听滚轮（passive: false 才能 preventDefault）
  // 空依赖数组，只注册一次，所有值都从 ref 读取
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleWheel = (e: WheelEvent) => {
      // 阻止浏览器默认的缩放行为（必须使用原生事件 + passive: false）
      e.preventDefault();
      e.stopPropagation();

      // 节流：防止滚动过快（参考 52etf.site 的 wheelThrottle: 24ms，这里用 160ms 更平滑）
      const now = Date.now();
      if (now - lastWheelTime.current < 160) return;
      lastWheelTime.current = now;

      // 使用 clientX/Y + 容器的 getBoundingClientRect 获取鼠标在容器中的视觉坐标
      const rect = container.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      // 从 ref 读取最新值
      const currentScale = scaleRef.current;
      const currentTranslate = translateRef.current;
      const currentAnimateTo = animateToRef.current;
      const currentClampTranslate = clampTranslateRef.current;

      // 找到当前缩放级别在数组中的索引（用最近匹配代替精确匹配，避免浮点精度问题）
      const currentIndex = findClosestZoomLevel(currentScale);
      const direction = e.deltaY > 0 ? -1 : 1;
      const newIndex = Math.min(Math.max(0, currentIndex + direction), ZOOM_LEVELS.length - 1);
      const newScale = ZOOM_LEVELS[newIndex];

      if (newScale === currentScale) return;

      if (newScale === 1) {
        // 缩放到 1 时重置平移（带动画）
        currentAnimateTo(1, 0, 0);
      } else {
        // 以鼠标位置为基准点调整平移（参考 52etf.site 的 V 函数）
        // 1. 计算鼠标在图表中的本地坐标（未缩放时的坐标）
        const localX = (mouseX - currentTranslate.x) / currentScale;
        const localY = (mouseY - currentTranslate.y) / currentScale;
        // 2. 计算新的偏移量，使本地坐标保持在鼠标位置
        const newOffsetX = mouseX - localX * newScale;
        const newOffsetY = mouseY - localY * newScale;
        // 3. 钳制偏移量（从 ref 读取最新值）
        const clamped = currentClampTranslate(newOffsetX, newOffsetY, newScale);
        // 4. 执行动画
        currentAnimateTo(newScale, clamped.x, clamped.y);
      }
    };

    container.addEventListener('wheel', handleWheel, { passive: false });
    return () => {
      container.removeEventListener('wheel', handleWheel);
    };
  }, []); // 空依赖，只注册一次

  // 拖拽平移
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (scale <= 1) return;
    setDragging(true);
    dragStart.current = { x: e.clientX - translate.x, y: e.clientY - translate.y };
    e.preventDefault();
  }, [scale, translate]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging) return;
    setTranslate({
      x: e.clientX - dragStart.current.x,
      y: e.clientY - dragStart.current.y,
    });
  }, [dragging]);

  const handleMouseUp = useCallback(() => {
    setDragging(false);
  }, []);

  useEffect(() => {
    if (!chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const chart = chartInstance.current;
    const coloredData = applyColors(data);
    const flat = isFlatData(data);

    const option: echarts.EChartsOption = {
      tooltip: {
        formatter: (params: unknown) => {
          const p = params as {
            data: Partial<SectorNode>;
            treePathInfo: Array<{ name: string }>;
          };
          const d = p.data || {};
          const changePercent = d.changePercent;
          const color = getColor(changePercent);
          const path =
            p.treePathInfo?.map((i) => i.name).filter(Boolean).join(' > ') || '';
          return `
            <div style="padding:4px;">
              <div style="font-weight:bold;margin-bottom:4px;">${path || d.name || ''}</div>
              <div style="color:${color};font-size:14px;">${formatPercent(changePercent)}</div>
              ${d.riseCount !== undefined && d.fallCount !== undefined
                ? `<div style="font-size:12px;color:#888;">涨:${d.riseCount} 跌:${d.fallCount}</div>`
                : ''}
            </div>
          `;
        },
        backgroundColor: 'rgba(20,20,30,0.9)',
        borderColor: '#333',
        textStyle: { color: '#eee' },
      },
      series: [
        {
          type: 'treemap',
          data: coloredData,
          left: 0,
          right: 0,
          top: 0,
          bottom: 0,
          squareRatio: 0.5 * (1 + Math.sqrt(5)),
          itemStyle: {
            borderColor: '#1a1a2e',
            borderWidth: 1,
            gapWidth: 0,
          },
          label: {
            show: true,
            position: 'inside',
            textBorderColor: 'transparent',
            textBorderWidth: 0,
            color: '#ffffff',
            fontSize: 12,
            fontWeight: 'bold',
          },
          upperLabel: {
            show: false,
          },
          // 点击节点不钻取（由外层 click 事件处理业务逻辑）
          nodeClick: false,
          roam: false,
          breadcrumb: {
            show: false,
          },
          levels: flat
            ? [
                {
                  itemStyle: {
                    borderColor: '#1a1a2e',
                    borderWidth: 1,
                    gapWidth: 1,
                  },
                  label: {
                    show: true,
                    position: 'inside',
                    textBorderColor: 'transparent',
                    textBorderWidth: 0,
                    color: '#ffffff',
                    fontSize: 11,
                    fontWeight: 'bold',
                    lineHeight: 14,
                  },
                  upperLabel: { show: false },
                },
              ]
            : [
                {
                  itemStyle: {
                    borderColor: '#1a1a2e',
                    borderWidth: 0,
                    gapWidth: 0,
                  },
                  upperLabel: { show: false },
                  label: { show: false },
                },
                {
                  itemStyle: {
                    borderColor: '#1a1a2e',
                    borderWidth: 1,
                    gapWidth: 1,
                  },
                  upperLabel: {
                    show: true,
                    height: 20,
                    formatter: (params: unknown) => {
                      const p = params as { data: Partial<SectorNode> };
                      return p.data?.name || '';
                    },
                    fontSize: 12,
                    fontWeight: 'bold' as const,
                    color: '#ffffff',
                    textBorderColor: 'transparent',
                    textBorderWidth: 0,
                  },
                  label: {
                    show: false,
                  },
                },
                {
                  itemStyle: {
                    borderColor: '#1a1a2e',
                    borderWidth: 1,
                    gapWidth: 1,
                  },
                  label: {
                    show: true,
                    position: 'inside',
                    textBorderColor: 'transparent',
                    textBorderWidth: 0,
                    color: '#ffffff',
                    fontSize: 12,
                    fontWeight: 'bold',
                    formatter: (params: unknown) => {
                      const p = params as { data: Partial<SectorNode> };
                      const d = p.data || {};
                      return `${d.name || ''}\n${formatPercent(d.changePercent)}`;
                    },
                  },
                  upperLabel: { show: false },
                },
              ],
        },
      ],
    };

    chart.setOption(option, true);

    chart.off('click');
    chart.on('click', (params: unknown) => {
      const p = params as { data: Partial<SectorNode> };
      if (p.data?.code && p.data?.name && onSectorClick) {
        onSectorClick(p.data.code, p.data.name);
      }
    });

    const handleResize = () => chart.resize();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [data, onSectorClick, language]);

  // 缩放变化时触发 ECharts resize
  useEffect(() => {
    chartInstance.current?.resize();
  }, [scale]);

  // 数据为空时显示友好提示
  if (data.length === 0) {
    return (
      <div
        style={{
          width: '100%',
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#888',
          fontSize: 14,
        }}
      >
        暂无数据（当前周期无可用数据，请尝试切换其他周期）
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height,
        overflow: 'hidden',
        position: 'relative',
        cursor: scale > 1 ? (dragging ? 'grabbing' : 'grab') : 'default',
      }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* 缩放指示器 */}
      {scale > 1 && (
        <div
          style={{
            position: 'absolute',
            top: 8,
            right: 8,
            zIndex: 10,
            background: 'rgba(20,20,30,0.8)',
            color: '#aaa',
            fontSize: 11,
            padding: '2px 8px',
            borderRadius: 4,
            pointerEvents: 'none',
          }}
        >
          {Math.round(scale * 100)}% · 滚轮缩放 · 拖拽平移
        </div>
      )}
      <div
        ref={chartRef}
        style={{
          width: '100%',
          height: '100%',
          transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})`,
          transformOrigin: 'top left',
          transition: dragging ? 'none' : 'transform 0.15s ease-out',
        }}
      />
    </div>
  );
};
