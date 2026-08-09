/**
 * UUID 生成工具
 *
 * 作用：生成符合 RFC 4122 标准的 UUID v4 字符串。
 * 优先使用浏览器原生 crypto.randomUUID（仅在 HTTPS 或 localhost 等安全上下文中可用），
 * 在非安全 HTTP 上下文（例如纯 http 部署）下自动降级到基于 Math.random 的实现，
 * 保证任何环境下都能拿到可用的唯一标识。
 */

/**
 * 生成 UUID v4。
 *
 * 优先使用 crypto.randomUUID（安全上下文：HTTPS/localhost），
 * 否则在非安全 HTTP 上下文下降级为基于 Math.random 的实现。
 * 参考：https://developer.mozilla.org/en-US/docs/Web/API/Crypto/randomUUID
 */
export function generateUUID(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  // 降级实现：固定版本位（4）与变体位（8/9/A/B），其余位使用随机数填充
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
