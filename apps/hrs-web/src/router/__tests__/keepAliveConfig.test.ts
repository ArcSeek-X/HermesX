/**
 * @file keepAliveConfig.test.ts
 * @description 路由缓存配置单测：默认配置形态（黑白名单、过期时间、数量上限）。
 *   名单规则到库匹配语法（exclude / include）的转换已移入
 *   `components/layout/KeepAliveOutlet.tsx` 的私有 `toMatchRules()`，其精度由该组件的
 *   集成测试以行为方式覆盖（`/docs/x` 离开即销毁、`/docsX` 不误伤仍缓存）。
 */
import { describe, expect, it } from 'vitest';
import { buildActiveCacheKey, KEEP_ALIVE_CONFIG } from '../keepAliveConfig';

describe('KEEP_ALIVE_CONFIG 默认配置', () => {
  it('默认黑名单语义：include 为空（除 exclude 外全部缓存）', () => {
    expect(KEEP_ALIVE_CONFIG.include).toEqual([]);
  });

  it('maxAliveTime 为 0（缓存页不过期，仅受数量上限约束）', () => {
    expect(KEEP_ALIVE_CONFIG.maxAliveTime).toBe(0);
  });

  it('maxCacheSize 为内存护栏（8）', () => {
    expect(KEEP_ALIVE_CONFIG.maxCacheSize).toBe(8);
  });

  it('exclude 覆盖登录页、流式对话、调试模块与兜底页', () => {
    expect(KEEP_ALIVE_CONFIG.exclude).toContain('/login');
    expect(KEEP_ALIVE_CONFIG.exclude).toContain('/choose/chat');
    expect(KEEP_ALIVE_CONFIG.exclude).toContain('/docs/*');
    expect(KEEP_ALIVE_CONFIG.exclude).toContain('/codeTest');
    expect(KEEP_ALIVE_CONFIG.exclude).toContain('/404');
  });
});

describe('buildActiveCacheKey 缓存键 query 白名单', () => {
  it('/stock/kline 忽略 search 与 hash：带参 / 不带参 / 换参都是同一实例', () => {
    expect(KEEP_ALIVE_CONFIG.cacheKeyParams['/stock/kline']).toEqual([]);
    expect(buildActiveCacheKey('/stock/kline', '', '')).toBe('/stock/kline');
    expect(buildActiveCacheKey('/stock/kline', '?stockCode=603019', '')).toBe('/stock/kline');
    expect(buildActiveCacheKey('/stock/kline', '?stockCode=600519', '#chart')).toBe('/stock/kline');
  });

  it('未声明白名单的路由仍按 pathname + search + hash 计算', () => {
    expect(buildActiveCacheKey('/watchlist', '?group=7', '#top')).toBe('/watchlist?group=7#top');
    expect(buildActiveCacheKey('/watchlist', '', '')).toBe('/watchlist');
  });

  it('白名单非空时只取指定参数并按 key 排序，忽略 hash 与其他 query', () => {
    const original = KEEP_ALIVE_CONFIG.cacheKeyParams['/probe'];
    KEEP_ALIVE_CONFIG.cacheKeyParams['/probe'] = ['tab', 'id'];
    try {
      expect(buildActiveCacheKey('/probe', '?id=2&tab=a&other=x', '#ignored')).toBe(
        '/probe?id=2&tab=a',
      );
      expect(buildActiveCacheKey('/probe', '?other=x', '#ignored')).toBe('/probe');
    } finally {
      if (original) KEEP_ALIVE_CONFIG.cacheKeyParams['/probe'] = original;
      else delete KEEP_ALIVE_CONFIG.cacheKeyParams['/probe'];
    }
  });
});
