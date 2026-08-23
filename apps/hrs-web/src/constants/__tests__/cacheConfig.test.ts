import { describe, expect, it } from 'vitest';
import { getCacheTTL } from '../cacheConfig';

/**
 * 缓存 TTL 匹配回归测试：
 * CACHE_TTL_MAP 的键必须与 axios 实际请求路径（含 /api/v1 前缀）一致，
 * 否则会全部回落到 DEFAULT_CACHE_TTL（60s），导致：
 * - 鉴权状态被缓存，登录成功后 fetchStatus 命中旧值，跳转被弹回登录页
 * - 用户私有数据（portfolio/alerts）被错误缓存，破坏数据一致性
 */
describe('cacheConfig TTL 匹配', () => {
  it('鉴权状态不缓存', () => {
    expect(getCacheTTL('/api/v1/auth/status')).toBe(0);
    expect(getCacheTTL('/api/v1/auth/login')).toBe(0);
  });
  it('用户私有数据不缓存', () => {
    expect(getCacheTTL('/api/v1/portfolio/snapshot')).toBe(0);
    expect(getCacheTTL('/api/v1/alerts/rules')).toBe(0);
  });
  it('AI 聊天相关不缓存', () => {
    expect(getCacheTTL('/api/v1/agent/chat/sessions')).toBe(0);
  });
  it('行情与板块按规则缓存', () => {
    expect(getCacheTTL('/api/v1/kline/603019')).toBe(30);
    expect(getCacheTTL('/api/v1/kline/search')).toBe(300);
    expect(getCacheTTL('/api/v1/sector/market-overview')).toBe(30);
    expect(getCacheTTL('/api/v1/sector/concept-scale')).toBe(300);
  });
  it('回测与决策信号按规则缓存', () => {
    expect(getCacheTTL('/api/v1/backtest/tasks')).toBe(600);
    expect(getCacheTTL('/api/v1/decision-signals')).toBe(300);
    expect(getCacheTTL('/api/v1/screening/result')).toBe(60);
  });
});
