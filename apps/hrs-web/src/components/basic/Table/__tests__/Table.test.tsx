/**
 * @file Table.test.tsx
 * @description Table 动态列集合回归测试：列数变化时行 Cell 数必须与表头列数一致。
 * 复现场景：切换市场（us 13 列 / cn 15 列）期间旧行数据保留，行对象引用不变，
 * React Aria 的 useCachedChildren 会命中 WeakMap 行缓存并复用绑定旧 columns 的 Row，
 * 导致 TableCollection.commit 抛 "Cell count must match column count"。
 * 固定列用例同时守住 fixedColumns.ts 的取值归一、CSS 变量偏移与连续固定区边界阴影。
 * @author Lensgcx (GaoCangxiong)
 */
import { render, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import Table from '../Table';
import type { TableColumnDef, TableColumnFixedMode } from '../Table';

interface MetricRow {
  id: string;
  code: string;
}

/** 生成 n 列定义，模拟不同市场下 13 / 15 列的差异 */
function buildColumns(count: number): TableColumnDef<MetricRow>[] {
  return Array.from({ length: count }, (_, index) => ({
    key: `field${index}`,
    title: `列${index}`,
    minWidth: 80,
    defaultWidth: 80,
  }));
}

describe('Table 动态列集合', () => {
  // 切市场时旧行在请求期间仍保留，对象引用不变 —— 这是命中 RAC 行缓存的前提
  const rows: MetricRow[] = [
    { id: 'cn:600519', code: '600519' },
    { id: 'cn:000001', code: '000001' },
  ];

  it.each([
    ['us → cn', 13, 15],
    ['cn → us', 15, 13],
  ])('%s：行对象不变时列数变化不应抛 Cell count 不匹配', (_label, from, to) => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    try {
      const { rerender, container } = render(
        <Table columns={buildColumns(from)} rows={rows} />,
      );

      expect(() => {
        rerender(<Table columns={buildColumns(to)} rows={rows} />);
      }).not.toThrow();

      expect(container.querySelectorAll('[role="columnheader"], th').length).toBe(to);
      const bodyRows = container.querySelectorAll('tbody tr');
      expect(bodyRows.length).toBe(rows.length);
      bodyRows.forEach((row) => {
        expect(row.querySelectorAll('[role="rowheader"], [role="gridcell"], td').length).toBe(to);
      });
      expect(consoleError.mock.calls.flat().join(' ')).not.toContain('Cell count must match column count');
    } finally {
      consoleError.mockRestore();
    }
  });

  it('固定列：列头与单元格引用同一 CSS 变量偏移，未固定列不带定位', async () => {
    const columns: TableColumnDef<MetricRow>[] = buildColumns(3).map((column, index) => ({
      ...column,
      fixed: index < 2 ? true : undefined,
    }));
    const { container } = render(<Table columns={columns} rows={rows} />);

    const headerCells = container.querySelectorAll<HTMLElement>('thead th');
    expect(headerCells).toHaveLength(3);
    expect(headerCells[0].style.left).toBe('var(--hrs-table-fixed-left-0)');
    expect(headerCells[1].style.left).toBe('var(--hrs-table-fixed-left-1)');
    expect(headerCells[2].style.left).toBe('');
    expect(headerCells[0].className).toContain('colFixedLeft');
    // 分隔阴影只加在连续固定区的末列，不逐列叠加
    expect(headerCells[0].className).not.toContain('colFixedEdge');
    expect(headerCells[1].className).toContain('colFixedEdgeLeft');

    const bodyCells = container.querySelectorAll<HTMLElement>('tbody tr:first-child td');
    expect(bodyCells).toHaveLength(3);
    expect(bodyCells[0].style.left).toBe('var(--hrs-table-fixed-left-0)');
    expect(bodyCells[1].style.left).toBe('var(--hrs-table-fixed-left-1)');
    expect(bodyCells[2].style.left).toBe('');
    expect(bodyCells[1].className).toContain('colFixedEdgeLeft');
    expect(bodyCells[2].className).not.toContain('colFixedEdge');

    // 偏移变量写在 wrapper 上，列宽变化只改 DOM、不触发集合重建。
    // RAC 集合 DOM 可能晚于 layout effect 提交，故等 MutationObserver 补测。
    const wrapper = container.querySelector<HTMLElement>('.hrs-table');
    await waitFor(() => {
      expect(wrapper?.style.getPropertyValue('--hrs-table-fixed-left-0')).toBe('0px');
      expect(wrapper?.style.getPropertyValue('--hrs-table-fixed-left-2')).toBe('0px');
      expect(wrapper?.style.getPropertyValue('--hrs-table-fixed-right-2')).toBe('0px');
    });
  });

  it('fixed 取值归一：true 等价左侧，false / 不传不固定，right 固定右侧', () => {
    const fixedValues: Array<TableColumnFixedMode | undefined> = [true, false, undefined, 'left', 'right'];
    const columns: TableColumnDef<MetricRow>[] = buildColumns(5).map((column, index) => ({
      ...column,
      fixed: fixedValues[index],
    }));
    const { container } = render(<Table columns={columns} rows={rows} />);

    const headerCells = container.querySelectorAll<HTMLElement>('thead th');
    expect(headerCells).toHaveLength(5);
    expect(headerCells[0].style.left).toBe('var(--hrs-table-fixed-left-0)');
    expect(headerCells[0].className).toContain('colFixedLeft');
    expect(headerCells[1].style.left).toBe('');
    expect(headerCells[2].style.left).toBe('');
    expect(headerCells[3].style.left).toBe('var(--hrs-table-fixed-left-3)');
    expect(headerCells[4].style.right).toBe('var(--hrs-table-fixed-right-4)');
    expect(headerCells[4].className).toContain('colFixedRight');
  });
});
