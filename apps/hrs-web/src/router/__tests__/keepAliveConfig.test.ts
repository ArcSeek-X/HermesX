/**
 * @file keepAliveConfig.test.ts
 * @description 路由缓存配置单测：默认配置形态（黑白名单、过期时间、数量上限）。
 *   名单规则到库匹配语法（exclude / include）的转换已移入
 *   `components/layout/KeepAliveOutlet.tsx` 的私有 `toMatchRules()`，其精度由该组件的
 *   集成测试以行为方式覆盖（`/docs/x` 离开即销毁、`/docsX` 不误伤仍缓存）。
 */
import { describe, expect, it } from 'vitest';
import { KEEP_ALIVE_CONFIG } from '../keepAliveConfig';

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
