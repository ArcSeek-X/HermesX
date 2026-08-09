/**
 * 问股会话导出工具
 *
 * 作用：把前端“问股（agent chat）”会话的消息列表导出为 Markdown 文件。
 * formatSessionAsMarkdown 负责把每条消息（用户/AI、含技能名）拼接成带生成时间的
 * Markdown 文本；downloadSession 负责生成 Blob 并触发浏览器下载为 .md 文件，
 * 下载完成后释放 Object URL 以避免内存泄漏。
 */

import type { Message } from '../stores/agentChatStore';

/**
 * 将会话消息格式化为用于导出的 Markdown 文本。
 *
 * @param messages - 会话消息数组
 * @returns 完整的 Markdown 字符串（含“问股会话”标题与生成时间）
 */
export function formatSessionAsMarkdown(messages: Message[]): string {
  const now = new Date();
  const timeStr = now.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });

  const lines: string[] = [
    '# 问股会话',
    '',
    `生成时间: ${timeStr}`,
    '',
  ];

  for (const msg of messages) {
    const heading = msg.role === 'user' ? '## 用户' : '## AI';
    if (msg.role === 'assistant' && msg.skillName) {
      lines.push(`${heading} (${msg.skillName})`);
    } else {
      lines.push(heading);
    }
    lines.push('');
    lines.push(msg.content);
    lines.push('');
  }

  return lines.join('\n');
}

/**
 * 触发浏览器将会话下载为 .md 文件。
 * 下载后主动 revoke Object URL，防止内存泄漏。
 *
 * @param messages - 会话消息数组
 */
export function downloadSession(messages: Message[]): void {
  const content = formatSessionAsMarkdown(messages);
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const now = new Date();
  const dateStr = now.toISOString().slice(0, 10).replace(/-/g, '');
  const pad = (n: number) => n.toString().padStart(2, '0');
  const timeStr = pad(now.getHours()) + pad(now.getMinutes());
  const filename = `问股会话_${dateStr}_${timeStr}.md`;

  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
