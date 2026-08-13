/**
 * ===================================
 * JSON 查看器组件（JsonViewer）
 * ===================================
 *
 * 【功能介绍】
 * 一个「JSON 结构化展示」组件，用于把任意 JSON 数据以可读、带语法高亮的方式呈现，
 * 并支持一键复制到剪贴板。适用于调试面板、API 响应预览、配置查看等场景。
 *
 * 【设计要点】
 * 1. 数据校验：data 为空（null / undefined）时显示「无数据」占位，避免崩溃。
 * 2. 语法高亮：通过正则 JSON_TOKEN_PATTERN 切分字符串，按 token 类型上色
 *    （键名 cyan、字符串 emerald、布尔/ null purple、数字 amber），无需引入高亮库。
 * 3. 复制交互：点击复制按钮将完整 JSON 写入剪贴板，2 秒后恢复「复制」文案。
 * 4. 受限滚动：内容区使用 maxHeight（默认 400px）+ 内部滚动 + 自定义滚动条，
 *    在长 JSON 下保持控件高度可控。
 * 5. 国际化：无数据文案、复制/已复制文案均取自 useUiLanguage 的 t()。
 *
 * 【使用方式】
 *   <JsonViewer data={someObject} maxHeight="500px" />
 */

import React, { useState } from 'react';
import { useUiLanguage } from '../../contexts/UiLanguageContext';

/** JsonViewer 组件的 Props 定义 */
interface JsonViewerProps {
  /** 待展示的 JSON 数据（对象 / 数组 / null / undefined） */
  data: Record<string, unknown> | unknown[] | null | undefined;
  /** 内容区最大高度（CSS 长度），默认 '400px' */
  maxHeight?: string;
  /** 透传的额外类名 */
  className?: string;
}

/** JSON token 正则：匹配字符串 / 数字 / true / false / null */
const JSON_TOKEN_PATTERN = /"(?:\\.|[^"\\])*"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b|true|false|null/g;

/** 根据 token 与行内剩余内容，返回对应的高亮颜色类名 */
function getTokenClassName(token: string, remainingLine: string): string {
  if (token.startsWith('"')) {
    // 字符串：若其后紧跟冒号则视为「键名」，否则视为「字符串值」
    return /^\s*:/.test(remainingLine) ? 'text-cyan-400' : 'text-emerald-400';
  }
  if (token === 'true' || token === 'false' || token === 'null') {
    return 'text-purple-400';
  }
  return 'text-amber-400';
}

/** 对单行 JSON 做语法高亮切分，返回带颜色的片段节点数组 */
function renderHighlightedLine(line: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const matcher = new RegExp(JSON_TOKEN_PATTERN);
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = matcher.exec(line)) !== null) {
    if (match.index > lastIndex) {
      parts.push(line.slice(lastIndex, match.index));
    }

    const token = match[0];
    const nextIndex = match.index + token.length;
    parts.push(
      <span key={`${match.index}-${token}`} className={getTokenClassName(token, line.slice(nextIndex))}>
        {token}
      </span>,
    );
    lastIndex = nextIndex;
  }

  if (lastIndex < line.length) {
    parts.push(line.slice(lastIndex));
  }

  return parts;
}

/**
 * JSON 查看器组件：格式化 + 语法高亮 + 一键复制。
 *
 * @param props - 组件属性
 * @param props.data - JSON 数据
 * @param props.maxHeight - 内容区最大高度
 * @param props.className - 额外类名
 * @returns 带复制按钮与高亮的 JSON 展示区；空数据时返回占位
 */
export const JsonViewer: React.FC<JsonViewerProps> = ({
  data,
  maxHeight = '400px',
  className = '',
}) => {
  const [copied, setCopied] = useState(false);
  const { t } = useUiLanguage();

  // 空数据占位
  if (!data) {
    return (
      <div className="text-gray-500 italic py-4 text-center">{t('common.noData')}</div>
    );
  }

  // 序列化为带 2 空格缩进的 JSON 字符串
  const jsonString = JSON.stringify(data, null, 2);

  // 复制：写入剪贴板 + 短暂展示「已复制」
  const handleCopy = async () => {
    await navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // 将整段 JSON 按行拆分并逐行高亮
  const highlightJson = (json: string): React.ReactNode => {
    return json.split('\n').map((line, index) => {
      return (
        <div key={index} className="leading-relaxed">
          {renderHighlightedLine(line)}
        </div>
      );
    });
  };

  return (
    <div className={`relative ${className}`}>
      {/* 复制按钮：绝对定位在右上角，复制后切换文案 */}
      <button
        onClick={handleCopy}
        className="absolute top-2 right-2 px-2 py-1 text-xs rounded
          bg-slate-700 hover:bg-slate-600 text-gray-300
          transition-colors z-10"
      >
        {copied ? t('common.copied') : t('common.copy')}
      </button>

      {/* JSON 内容：深色底 + 等宽字体 + 受限高度滚动 */}
      <div
        className="bg-slate-900/80 rounded-lg p-4 overflow-auto custom-scrollbar
          border border-slate-700/50 font-mono text-sm text-gray-300"
        style={{ maxHeight }}
      >
        <pre className="whitespace-pre-wrap break-words">
          {highlightJson(jsonString)}
        </pre>
      </div>
    </div>
  );
};
