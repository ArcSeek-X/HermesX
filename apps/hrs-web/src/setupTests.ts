/**
 * 测试环境全局初始化文件（setup file）。
 *
 * 在运行任何测试用例之前自动执行，负责补齐浏览器环境下存在、
 * 但 Node 测试运行时缺失的 API 与存储能力，使组件测试环境尽量贴近真实浏览器。
 */
import '@testing-library/jest-dom';

/**
 * 内存版 Storage 实现，用于在无 localStorage 的测试环境中兜底。
 * 以 Map 存储键值对，完整实现 Storage 接口（length / getItem / setItem / clear / key / removeItem）。
 */
class MemoryStorageMock implements Storage {
  private readonly values = new Map<string, string>();

  get length() {
    return this.values.size;
  }

  clear() {
    this.values.clear();
  }

  getItem(key: string) {
    return this.values.get(key) ?? null;
  }

  key(index: number) {
    return Array.from(this.values.keys())[index] ?? null;
  }

  removeItem(key: string) {
    this.values.delete(key);
  }

  setItem(key: string, value: string) {
    this.values.set(key, String(value));
  }
}

/**
 * IntersectionObserver 的空实现（no-op mock）。
 * 真实组件可能监听元素是否进入视口（如无限滚动），测试环境无此能力，这里用空方法占位。
 */
class IntersectionObserverMock implements IntersectionObserver {
  readonly root = null;
  readonly rootMargin = '';
  readonly thresholds = [0];

  disconnect() {}

  observe() {}

  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }

  unobserve() {}
}

// 用空实现替换全局 IntersectionObserver，避免组件因缺失该 API 而报错
Object.defineProperty(globalThis, 'IntersectionObserver', {
  writable: true,
  value: IntersectionObserverMock,
});

/**
 * 探测当前运行环境是否具备可用的 localStorage：
 * 检查关键方法是否都为函数，并包裹 try/catch 以防某些环境下访问 localStorage 直接抛错。
 */
const hasLocalStorage = (() => {
  try {
    return typeof globalThis.localStorage?.getItem === 'function'
      && typeof globalThis.localStorage?.setItem === 'function'
      && typeof globalThis.localStorage?.removeItem === 'function'
      && typeof globalThis.localStorage?.clear === 'function';
  } catch {
    return false;
  }
})();

// 若环境缺失可用的 localStorage，则用内存版实现兜底，保证存储相关逻辑可正常跑通
if (!hasLocalStorage) {
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: new MemoryStorageMock(),
  });
}
