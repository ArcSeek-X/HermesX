/**
 * @file components/basic/Table/fixedColumns.ts
 * @description 通用表格固定列（fixed col）逻辑：取值归一、列定位属性、连续固定区边界阴影、
 * 以及按运行时列宽计算偏移的观测器。
 * 只依赖「列 key + fixed 取值」这一最小契约，不引用 TableColumnDef，避免与 Table.tsx 循环依赖。
 * @author Lensgcx (GaoCangxiong)
 */

import { useLayoutEffect } from 'react';
import type { CSSProperties, RefObject } from 'react';
import { cn } from '../../../utils/cn';
import styles from './Table.module.scss';

/**
 * 表格列 `fixed` 字段的取值（固定模式），描述这一列以何种方式固定。
 * - `true`：固定在左侧（简写）
 * - `'left'`：显式固定在左侧
 * - `'right'`：固定在右侧
 * - `false` / 不传：默认不固定
 */
export type TableColumnFixedMode = boolean | 'left' | 'right';

/** 固定列属性：列头与单元格共用同一份，避免两处漂移 */
export interface FixedColumnProps {
  className?: string;
  style?: CSSProperties;
}

/** 固定列 CSS 变量名：由 ResizeObserver 按实际列宽写入外层容器 */
const fixedLeftVar = (index: number): string => `--hrs-table-fixed-left-${index}`;
const fixedRightVar = (index: number): string => `--hrs-table-fixed-right-${index}`;

/** 把 fixed 取值归一为方向；true 视为左侧，false / 不传视为不固定 */
function toFixedSide(fixed: TableColumnFixedMode | undefined): 'left' | 'right' | undefined {
  if (fixed === true || fixed === 'left') return 'left';
  if (fixed === 'right') return 'right';
  return undefined;
}

/**
 * 按列 key 建索引的固定列属性：Row 的 render prop 只给列对象、不给索引，
 * 故表头与单元格统一从这里取。
 * 每列只归一一次方向，定位属性与连续固定区边界共用结果。
 * 分隔阴影只加在边界列（左侧连续固定区末列 / 右侧连续固定区首列），避免逐列叠加。
 */
export function buildFixedColumnPropsByKey(
  columns: ReadonlyArray<{ key: string; fixed?: TableColumnFixedMode }>,
): Map<string, FixedColumnProps> {
  const sides = columns.map((column) => toFixedSide(column.fixed));

  let lastLeft = -1;
  for (let index = 0; index < sides.length; index += 1) {
    if (sides[index] !== 'left') break;
    lastLeft = index;
  }
  let firstRight = -1;
  for (let index = sides.length - 1; index >= 0; index -= 1) {
    if (sides[index] !== 'right') break;
    firstRight = index;
  }

  return new Map<string, FixedColumnProps>(columns.map((column, index) => {
    const side = sides[index];
    let className: string | undefined;
    let style: CSSProperties | undefined;
    if (side === 'left') {
      className = styles.colFixedLeft;
      style = { left: `var(${fixedLeftVar(index)})` };
    } else if (side === 'right') {
      className = styles.colFixedRight;
      style = { right: `var(${fixedRightVar(index)})` };
    }

    if (index === lastLeft) className = cn(className, styles.colFixedEdgeLeft);
    else if (index === firstRight) className = cn(className, styles.colFixedEdgeRight);

    return [column.key, { className, style }] as const;
  }));
}

/**
 * 固定列偏移：列宽由 ResizableContainer 运行时计算且可拖动，left / right 不能写死。
 * 用 ResizeObserver 观察表头 th 的实际宽度，把累计偏移写到 wrapper 的 CSS 变量上；
 * 只改 DOM、不进 React state，避免 RAC collection 因重渲染重新构建。
 */
export function useFixedColumnOffsets(
  wrapperRef: RefObject<HTMLDivElement | null>,
  columnCount: number,
  columnSignature: string,
): void {
  useLayoutEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;

    // RAC collection 可能在本 effect 之后才 commit DOM，节点不能缓存，每次重新查询。
    const observed = new Set<HTMLElement>();
    let resizeObserver: ResizeObserver | null = null;

    const updateOffsets = (): void => {
      const headerCells = Array.from(wrapper.querySelectorAll<HTMLElement>('thead th'));
      if (headerCells.length === 0) return;
      headerCells.forEach((cell) => {
        if (!observed.has(cell)) {
          resizeObserver?.observe(cell);
          observed.add(cell);
        }
      });

      // selectionMode 非 none 时 RAC 会在最前面插入 checkbox 列，按列数对齐后再累加。
      const extra = Math.max(0, headerCells.length - columnCount);
      const widthOf = (cell: HTMLElement): number => cell.getBoundingClientRect().width;
      let left = headerCells.slice(0, extra).reduce((sum, cell) => sum + widthOf(cell), 0);
      const widths = headerCells.slice(extra).map(widthOf);
      widths.forEach((width, index) => {
        wrapper.style.setProperty(fixedLeftVar(index), `${left}px`);
        left += width;
      });
      let right = 0;
      for (let index = widths.length - 1; index >= 0; index -= 1) {
        wrapper.style.setProperty(fixedRightVar(index), `${right}px`);
        right += widths[index];
      }
    };

    if (typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(updateOffsets);
      resizeObserver.observe(wrapper);
    }
    updateOffsets();

    // RAC 集合 DOM 可能晚于本 effect 提交：仅在首帧缺失时补测一次并立即断开，
    // 不持续监听子树（列宽变化交给 ResizeObserver，列集合变化由 columnSignature 重建）。
    let mutationObserver: MutationObserver | null = null;
    if (wrapper.querySelectorAll('thead th').length === 0) {
      mutationObserver = new MutationObserver(() => {
        if (wrapper.querySelectorAll('thead th').length === 0) return;
        updateOffsets();
        mutationObserver?.disconnect();
        mutationObserver = null;
      });
      mutationObserver.observe(wrapper, { childList: true, subtree: true });
    }

    return () => {
      resizeObserver?.disconnect();
      mutationObserver?.disconnect();
      observed.clear();
    };
  }, [wrapperRef, columnCount, columnSignature]);
}
