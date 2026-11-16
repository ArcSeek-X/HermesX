/**
 * @file dataSource.test.ts
 * @description 数据源统一定义契约测试：Key 集合、输入归一、取名与输出格式保形。
 * 仅依赖 constants/dataSource.ts 的公开 API，避免测试与内部实现耦合。
 * @author Lensgcx (GaoCangxiong)
 */
import type { UiTextKey } from '@/i18n/uiText';
import { describe, expect, it } from 'vitest';
import { DATA_SOURCE_KEYS, resolveDataSourceLabel } from '../dataSource';

/** 直接回显 key，便于断言「Key → 文案键」映射本身是否正确 */
const t = (key: UiTextKey): string => key;

describe('dataSource 统一定义', () => {
  it('Key 集合稳定且覆盖 StockDB', () => {
    expect(DATA_SOURCE_KEYS).toEqual([
      'eastmoney',
      'tencent',
      'sina',
      'xueqiu',
      'stocksdk',
      'stockdb',
    ]);
  });

  it('每个数据源都解析到 dataSource.<id> 文案键', () => {
    for (const key of DATA_SOURCE_KEYS) {
      expect(resolveDataSourceLabel(key, t)).toBe(`dataSource.${key}`);
    }
  });

  it('归一化能力经取名结果验证：拆分 / 去空 / 去重 / 小写 / 保序', () => {
    expect(resolveDataSourceLabel(' Eastmoney，tencent , eastmoney,, ', t)).toBe(
      'dataSource.eastmoney，dataSource.tencent',
    );
    expect(resolveDataSourceLabel(['eastmoney，tencent', 'sina'], t)).toEqual([
      'dataSource.eastmoney',
      'dataSource.tencent',
      'dataSource.sina',
    ]);
  });

  it('数组进数组出：数量、顺序与元素数保持不变', () => {
    expect(resolveDataSourceLabel(['eastmoney', 'tencent'], t)).toEqual([
      'dataSource.eastmoney',
      'dataSource.tencent',
    ]);
    expect(resolveDataSourceLabel(['eastmoney'], t)).toEqual(['dataSource.eastmoney']);
    expect(resolveDataSourceLabel([], t)).toEqual([]);
  });

  it('字符串进字符串出：单值、英文逗号串、中文逗号串各自保形', () => {
    expect(resolveDataSourceLabel('eastmoney', t)).toBe('dataSource.eastmoney');
    expect(resolveDataSourceLabel('eastmoney,tencent', t)).toBe(
      'dataSource.eastmoney,dataSource.tencent',
    );
    expect(resolveDataSourceLabel('eastmoney，tencent', t)).toBe(
      'dataSource.eastmoney，dataSource.tencent',
    );
  });

  it('空值走占位，未登记来源回显原值', () => {
    expect(resolveDataSourceLabel(null, t)).toBe('—');
    expect(resolveDataSourceLabel('', t, '未知')).toBe('未知');
    expect(resolveDataSourceLabel('FUTU', t)).toBe('futu');
  });
});
