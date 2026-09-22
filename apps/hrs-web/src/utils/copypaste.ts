/**
 * @file copypaste.ts
 * @description 剪贴板通用工具：复制 / 粘贴，供全项目复用。
 *  - copyToClipboard：写入剪贴板（基于 clipboard-copy，自动兼容非安全上下文）。
 *  - pasteFromClipboard：读取剪贴板（需安全上下文 + 用户手势 + 授权）。
 */
import copy from 'clipboard-copy';

/**
 * 将文本写入剪贴板。
 * 优先 navigator.clipboard，非安全上下文（http 部署）自动回退 execCommand，覆盖全环境。
 * @param text 待复制文本
 * @returns 是否复制成功
 */
export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    await copy(text);
    return true;
  } catch {
    return false;
  }
};

/**
 * 从剪贴板读取文本。
 * 注意：仅安全上下文（https / localhost）可用，且需用户手势触发并经授权；
 * 不支持或拒绝时返回 null，调用方自行决定兜底。
 */
export const pasteFromClipboard = async (): Promise<string | null> => {
  try {
    if (typeof navigator === 'undefined' || !navigator.clipboard?.readText) return null;
    return await navigator.clipboard.readText();
  } catch {
    return null;
  }
};
