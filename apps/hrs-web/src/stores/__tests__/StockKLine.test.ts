/**
 * StockKLine store 单测：增 / 覆盖 / 局部更新 / 删除 / 刷新恢复 / 脏值兜底。
 * 验证内存 store 与 sessionStorage（实际键 hrs-state-stockKLine）恒一致。
 */
import { beforeEach, describe, expect, it } from 'vitest';
import {
  getStockKLineInfo,
  hydrateStockKLineInfo,
  removeStockKLineInfo,
  setStockKLineInfo,
  updateStockKLineInfo,
  useStockKLineStore,
} from '../StockKLine';
import { getStorageItem, setStorageItem } from '@utils/storage';

const ACTUAL_KEY = 'hrs-state-stockKLine';

beforeEach(() => {
  sessionStorage.clear();
  removeStockKLineInfo();
});

describe('StockKLine store CRUD', () => {
  it('初始无持久化时未选中，且展示态为 null', () => {
    hydrateStockKLineInfo();
    expect(getStockKLineInfo()).toBeNull();
    expect(getStorageItem('stockKLine', 'session')).toBeNull();
  });

  it('setStockKLineInfo 增/整体覆盖：写入 { code, name } 并同步 sessionStorage', () => {
    setStockKLineInfo({ code: '603019', name: '中科曙光' });

    expect(getStockKLineInfo()).toEqual({ code: '603019', name: '中科曙光' });
    expect(useStockKLineStore.getState().stockKLineSelected).toEqual({ code: '603019', name: '中科曙光' });
    expect(getStorageItem('stockKLine', 'session')).toEqual({ code: '603019', name: '中科曙光' });
    expect(JSON.parse(sessionStorage.getItem(ACTUAL_KEY) ?? 'null')).toEqual({
      code: '603019',
      name: '中科曙光',
    });
  });

  it('换股时整体覆盖，持久化值无多余字段', () => {
    setStockKLineInfo({ code: '603019', name: '中科曙光' });
    setStockKLineInfo({ code: '600519', name: '贵州茅台' });

    expect(getStockKLineInfo()).toEqual({ code: '600519', name: '贵州茅台' });
    expect(Object.keys(getStorageItem<Record<string, unknown>>('stockKLine', 'session') ?? {})).toEqual([
      'code',
      'name',
    ]);
  });

  it('updateStockKLineInfo 局部更新：行情返回后补 name，不改 code', () => {
    setStockKLineInfo({ code: '603019', name: '' });
    updateStockKLineInfo({ name: '中科曙光' });

    expect(getStockKLineInfo()).toEqual({ code: '603019', name: '中科曙光' });
    expect(getStorageItem('stockKLine', 'session')).toEqual({ code: '603019', name: '中科曙光' });
  });

  it('updateStockKLineInfo 在无值时忽略，不创建半成品对象', () => {
    updateStockKLineInfo({ name: '中科曙光' });
    expect(getStockKLineInfo()).toBeNull();
    expect(getStorageItem('stockKLine', 'session')).toBeNull();
  });

  it('removeStockKLineInfo 删除：store 置 null 且持久化键消失', () => {
    setStockKLineInfo({ code: '603019', name: '中科曙光' });
    removeStockKLineInfo();

    expect(getStockKLineInfo()).toBeNull();
    expect(getStorageItem('stockKLine', 'session')).toBeNull();
    expect(sessionStorage.getItem(ACTUAL_KEY)).toBeNull();
  });

  it('hydrateStockKLineInfo 模拟刷新：从已有持久化恢复选中股票', () => {
    setStorageItem('stockKLine', { code: '603019', name: '中科曙光' }, 'session');
    useStockKLineStore.setState({ stockKLineSelected: null });

    hydrateStockKLineInfo();

    expect(getStockKLineInfo()).toEqual({ code: '603019', name: '中科曙光' });
  });

  it('清空后 hydrate 仍是未选中：刷新不会复活旧股票', () => {
    setStockKLineInfo({ code: '603019', name: '中科曙光' });
    removeStockKLineInfo();
    useStockKLineStore.setState({ stockKLineSelected: { code: '603019', name: '中科曙光' } });

    hydrateStockKLineInfo();

    expect(getStockKLineInfo()).toBeNull();
  });

  it('脏值兜底：缺 code / 非对象 / 非字符串 name 均安全降级且不回写', () => {
    setStorageItem('stockKLine', { name: '中科曙光' }, 'session');
    hydrateStockKLineInfo();
    expect(getStockKLineInfo()).toBeNull();
    // 不回写脏值，保持原样直到下一次合法写入
    expect(getStorageItem('stockKLine', 'session')).toEqual({ name: '中科曙光' });

    setStorageItem('stockKLine', 'not-an-object', 'session');
    hydrateStockKLineInfo();
    expect(getStockKLineInfo()).toBeNull();

    // name 缺失时按 '' 兼容
    setStorageItem('stockKLine', { code: '603019' }, 'session');
    hydrateStockKLineInfo();
    expect(getStockKLineInfo()).toEqual({ code: '603019', name: '' });
  });
});
