/**
 * Markdown 转纯文本工具
 *
 * 作用：将含有 Markdown 语法的报告文本转换为干净的纯文本，便于复制到剪贴板、
 * 生成分享摘要或在纯文本场景展示。基于 remove-markdown 库解析，并额外清理
 * GFM 表格分隔行（如 |---|）等该库偶尔残留的内容。
 */

import removeMd from 'remove-markdown';

/**
 * 将 Markdown 转换为纯文本。
 * 使用 remove-markdown 库做标准解析，并做 GFM 表格分隔行的后处理。
 *
 * @param markdown - 原始 Markdown 字符串
 * @returns 纯文本；空输入返回空串
 */
export function markdownToPlainText(markdown: string): string {
  if (!markdown) return '';

  const plainText = removeMd(markdown, {
    gfm: true,
    useImgAltText: true,
    stripListLeaders: true,
  });

  // 额外后处理：去除 remove-markdown 偶尔残留的 GFM 表格分隔行（如 |---|）
  return plainText
    .replace(/\n\|?[\s|:-]+\|?\s*(?=\n|$)/g, '\n')
    .trim();
}
