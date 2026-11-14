/**
 * 个股 K 线页「当前选中股票」的唯一真源。
 * 会话键 `stockKLine`（实际 `hrs-state-stockKLine`）存 `{ code, name }`：有值恢复股票，无值展示最近搜索列表。
 */
import { create } from 'zustand';
import { getStorageItem, removeStorageItem, setStorageItem } from '@utils/storage';
import type { StockRef } from '../types/stock';

/** 会话级：刷新与跨路由往返保留，关标签页清空 */
const STOCK_KLINE_SESSION_KEY = 'stockKLine';

type StockKLineSelection = StockRef | null;

/** 读取会话存储；脏值按未选中处理且不回写 */
function readStockKLineSelection(): StockKLineSelection {
  const persistedStockKLine = getStorageItem<unknown>(STOCK_KLINE_SESSION_KEY, 'session');
  if (!persistedStockKLine || typeof persistedStockKLine !== 'object' || Array.isArray(persistedStockKLine)) {
    return null;
  }
  const { code, name } = persistedStockKLine as Record<string, unknown>;
  if (typeof code !== 'string' || !code.trim()) return null;
  return { code, name: typeof name === 'string' ? name : '' };
}

/** 内存与会话存储同步写入 */
function writeStockKLineSelection(stockKLineSelected: StockRef): void {
  setStorageItem(STOCK_KLINE_SESSION_KEY, stockKLineSelected, 'session');
  useStockKLineStore.setState({ stockKLineSelected });
}



/** 组件订阅当前选中股票 */
export const useStockKLineStore = create<{ stockKLineSelected: StockKLineSelection }>(() => ({
  stockKLineSelected: readStockKLineSelection(),
}));



/** 非 Hook 场景同步读取当前选中股票 */
export function getStockKLine(): StockKLineSelection {
  return useStockKLineStore.getState().stockKLineSelected;
}

/** 整体写入或换股；name 未知时传空串 */
export function setStockKLine(stockToSelect: StockRef): void {
  const code = stockToSelect.code.trim();
  if (!code) return;
  writeStockKLineSelection({ code, name: stockToSelect.name ?? '' });
}

/** 合并更新已有值；未选中时忽略，不创建缺 code 的残缺对象 */
export function updateStockKLine(stockFieldsToUpdate: Partial<StockRef>): void {
  const currentStockKLine = getStockKLine();
  if (!currentStockKLine) return;
  writeStockKLineSelection({
    code: stockFieldsToUpdate.code?.trim() || currentStockKLine.code,
    name: stockFieldsToUpdate.name ?? currentStockKLine.name,
  });
}

/** 清空选中态并删除会话键，刷新与往返都不复活旧股票 */
export function removeStockKLine(): void {
  removeStorageItem(STOCK_KLINE_SESSION_KEY, 'session');
  useStockKLineStore.setState({ stockKLineSelected: null });
}

/** 从会话存储重新载入，供测试模拟刷新 */
export function hydrateStockKLine(): void {
  useStockKLineStore.setState({ stockKLineSelected: readStockKLineSelection() });
}

