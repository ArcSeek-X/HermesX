/**
 * @file appRouter.test.ts
 * @description 数据路由守卫单测：protectedLoader 的鉴权分流逻辑。
 *   直接守护「根 / 被 index 无条件弹回登录页」的登录死循环回归。
 */
import { describe, expect, it, vi } from 'vitest';
import type { LoaderFunctionArgs } from 'react-router-dom';

const storeState = vi.hoisted(() => ({ authEnabled: false, loggedIn: false }));

vi.mock('../../stores/AuthStore', () => ({
  useAuthStore: { getState: () => storeState },
}));

// 必须在 mock 之后导入被测模块（createBrowserRouter 在加载时执行）
const { protectedLoader } = await import('../appRouter');

const makeArgs = (path: string): LoaderFunctionArgs =>
  ({ request: new Request(`http://localhost${path}`) }) as LoaderFunctionArgs;

const redirectLocation = (res: unknown): string =>
  (res as Response).headers.get('Location') ?? '';

describe('protectedLoader', () => {
  it('未登录且开启鉴权 → 抛出重定向 /login（携带来源路径）', () => {
    storeState.authEnabled = true;
    storeState.loggedIn = false;
    expect(() => protectedLoader(makeArgs('/home'))).toThrow();
    try {
      protectedLoader(makeArgs('/home'));
    } catch (e) {
      expect((e as Response).status).toBe(302);
      expect(redirectLocation(e)).toContain('/login?redirect=');
    }
  });

  it('已登录 → 放行（返回 null）', () => {
    storeState.authEnabled = true;
    storeState.loggedIn = true;
    expect(protectedLoader(makeArgs('/home'))).toBeNull();
  });

  it('未开启鉴权 → 放行（返回 null）', () => {
    storeState.authEnabled = false;
    storeState.loggedIn = false;
    expect(protectedLoader(makeArgs('/home'))).toBeNull();
  });
});
