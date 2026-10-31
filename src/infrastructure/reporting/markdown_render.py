# -*- coding: utf-8 -*-
"""
===================================
Markdown 渲染 / 平台格式转换（基础设施层）
===================================

将通用 Markdown 转换为 HTML 文档、纯文本，或飞书 / Telegram / 微信 /
Slack 等平台特定格式，含 pipe 表格转键值行、fenced code 保护等。纯文本长度
分块见 `src/domain/shared/text_chunking.py`（本模块不做分块）。

（本文件由 `src/formatters.py` 机械拆分而来，函数实现逐字保留。）
"""

import re
from typing import Callable, List

import markdown2


FENCED_CODE_BLOCK_RE = re.compile(r"(^```[^\n]*\n.*?^```[ \t]*$)", re.MULTILINE | re.DOTALL)
FENCED_CODE_BLOCK_PLACEHOLDER = "@@HRS_FENCED_CODE_BLOCK_{}@@"

def markdown_to_html_document(markdown_text: str) -> str:
    """
    Convert Markdown to a complete HTML document (for email, md2img, etc.).

    Uses markdown2 with table and code block support, wraps with inline CSS
    for compact, readable layout. Reused by notification email and md2img.

    Args:
        markdown_text: Raw Markdown content.

    Returns:
        Full HTML document string with DOCTYPE, head, and body.
    """
    html_content = markdown2.markdown(
        markdown_text,
        extras=["tables", "fenced-code-blocks", "break-on-newline", "cuddled-lists"],
    )

    css_style = """
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                line-height: 1.5;
                color: #24292e;
                font-size: 14px;
                padding: 15px;
                max-width: 900px;
                margin: 0 auto;
            }
            h1 {
                font-size: 20px;
                border-bottom: 1px solid #eaecef;
                padding-bottom: 0.3em;
                margin-top: 1.2em;
                margin-bottom: 0.8em;
                color: #0366d6;
            }
            h2 {
                font-size: 18px;
                border-bottom: 1px solid #eaecef;
                padding-bottom: 0.3em;
                margin-top: 1.0em;
                margin-bottom: 0.6em;
            }
            h3 {
                font-size: 16px;
                margin-top: 0.8em;
                margin-bottom: 0.4em;
            }
            p {
                margin-top: 0;
                margin-bottom: 8px;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin: 12px 0;
                display: block;
                overflow-x: auto;
                font-size: 13px;
            }
            th, td {
                border: 1px solid #dfe2e5;
                padding: 6px 10px;
                text-align: left;
            }
            th {
                background-color: #f6f8fa;
                font-weight: 600;
            }
            tr:nth-child(2n) {
                background-color: #f8f8f8;
            }
            tr:hover {
                background-color: #f1f8ff;
            }
            blockquote {
                color: #6a737d;
                border-left: 0.25em solid #dfe2e5;
                padding: 0 1em;
                margin: 0 0 10px 0;
            }
            code {
                padding: 0.2em 0.4em;
                margin: 0;
                font-size: 85%;
                background-color: rgba(27,31,35,0.05);
                border-radius: 3px;
                font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
            }
            pre {
                padding: 12px;
                overflow: auto;
                line-height: 1.45;
                background-color: #f6f8fa;
                border-radius: 3px;
                margin-bottom: 10px;
            }
            hr {
                height: 0.25em;
                padding: 0;
                margin: 16px 0;
                background-color: #e1e4e8;
                border: 0;
            }
            ul, ol {
                padding-left: 20px;
                margin-bottom: 10px;
            }
            li {
                margin: 2px 0;
            }
        """

    return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                {css_style}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

def markdown_to_plain_text(markdown_text: str) -> str:
    """
    将 Markdown 转换为纯文本
    
    移除 Markdown 格式标记，保留可读性
    """
    text = markdown_text
    
    # 移除标题标记 # ## ###
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # 移除加粗 **text** -> text
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    
    # 移除斜体 *text* -> text
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    
    # 移除引用 > text -> text
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    
    # 移除列表标记 - item -> item
    text = re.sub(r'^[-*]\s+', '• ', text, flags=re.MULTILINE)
    
    # 移除分隔线 ---
    text = re.sub(r'^---+$', '────────', text, flags=re.MULTILINE)
    
    # 移除表格语法 |---|---|
    text = re.sub(r'\|[-:]+\|[-:|\s]+\|', '', text)
    text = re.sub(r'^\|(.+)\|$', r'\1', text, flags=re.MULTILINE)
    
    # 清理多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def _is_markdown_table_separator(row: str) -> bool:
    return bool(re.match(r'^\s*\|?\s*[:-]+\s*(\|\s*[:-]+\s*)+\|?\s*$', row))


def _parse_markdown_table_row(row: str) -> List[str]:
    stripped = row.strip()
    if stripped.startswith('|'):
        stripped = stripped[1:]
    if stripped.endswith('|'):
        stripped = stripped[:-1]
    return [c.strip() for c in stripped.split('|')]


def _strip_inline_markdown(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^\*\*(.+)\*\*$', r'\1', text)
    text = re.sub(r'^\*(.+)\*$', r'\1', text)
    text = text.replace("**", "")
    return text.strip()


def _format_two_column_table_row(header: List[str], row: List[str]) -> str:
    key = _strip_inline_markdown(row[0]) if row else ""
    value = _strip_inline_markdown(row[1]) if len(row) > 1 else ""
    value_header = _strip_inline_markdown(header[1]) if len(header) > 1 else ""

    if not value:
        return key
    if value.upper() == "N/A" and value_header in {"类型", "Type"}:
        return key
    return f"{key}：{value}"


def _flush_table_as_key_value_rows(buffer: List[str], output: List[str], *, bullet: str) -> None:
    if not buffer:
        return

    rows = []
    for raw in buffer:
        if _is_markdown_table_separator(raw):
            continue
        parsed = _parse_markdown_table_row(raw)
        if parsed:
            rows.append(parsed)

    if not rows:
        return

    header = rows[0]
    data_rows = rows[1:] if len(rows) > 1 else []
    for row in data_rows:
        if len(row) < len(header):
            row = row + [""] * (len(header) - len(row))
        if len(header) == 2 and len(row) >= 2:
            output.append(f"{bullet} {_format_two_column_table_row(header, row)}")
            continue

        pairs = []
        for idx, cell in enumerate(row):
            key = _strip_inline_markdown(header[idx]) if idx < len(header) else f"列{idx + 1}"
            pairs.append(f"{key}：{_strip_inline_markdown(cell)}")
        output.append(f"{bullet} {' | '.join(pairs)}")


def _protect_fenced_code_blocks(content: str) -> tuple[str, List[str]]:
    blocks: List[str] = []

    def _replace(match: re.Match) -> str:
        blocks.append(match.group(0))
        return FENCED_CODE_BLOCK_PLACEHOLDER.format(len(blocks) - 1)

    return FENCED_CODE_BLOCK_RE.sub(_replace, content), blocks


def _restore_fenced_code_blocks(content: str, blocks: List[str]) -> str:
    restored = content
    for idx, block in enumerate(blocks):
        restored = restored.replace(FENCED_CODE_BLOCK_PLACEHOLDER.format(idx), block)
    return restored


def _transform_outside_fenced_code_blocks(content: str, transform: Callable[[str], str]) -> str:
    protected, blocks = _protect_fenced_code_blocks(content)
    return _restore_fenced_code_blocks(transform(protected), blocks)


def _markdown_tables_to_key_value_rows_unprotected(content: str, *, bullet: str) -> str:
    """Convert pipe tables to compact key-value rows for chat clients."""

    lines: List[str] = []
    table_buffer: List[str] = []

    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        if line.strip().startswith('|'):
            table_buffer.append(line)
            continue

        if table_buffer:
            _flush_table_as_key_value_rows(table_buffer, lines, bullet=bullet)
            table_buffer = []

        lines.append(line)

    if table_buffer:
        _flush_table_as_key_value_rows(table_buffer, lines, bullet=bullet)

    return "\n".join(lines).strip()


def markdown_tables_to_key_value_rows(content: str, *, bullet: str = "•") -> str:
    """Convert pipe tables to compact key-value rows outside fenced code blocks."""

    return _transform_outside_fenced_code_blocks(
        content,
        lambda text: _markdown_tables_to_key_value_rows_unprotected(text, bullet=bullet),
    ).strip()

def _format_feishu_markdown_unprotected(content: str) -> str:
    lines = []
    table_buffer: List[str] = []

    for raw_line in content.splitlines():
        line = raw_line.rstrip()

        # 处理表格行
        if line.strip().startswith('|'):
            table_buffer.append(line)
            continue

        # 刷新表格缓冲区
        if table_buffer:
            _flush_table_as_key_value_rows(table_buffer, lines, bullet="•")
            table_buffer = []

        # 转换标题（# ## ### 等）
        if re.match(r'^#{1,6}\s+', line):
            title = re.sub(r'^#{1,6}\s+', '', line).strip()
            line = f"**{title}**" if title else ""
        # 转换引用块
        elif line.startswith('> '):
            quote = line[2:].strip()
            line = quote
        # 转换分隔线
        elif line.strip() == '---':
            line = '────────'
        # 转换列表项
        elif line.startswith('- '):
            line = f"• {line[2:].strip()}"

        lines.append(line)

    # 处理末尾的表格
    if table_buffer:
        _flush_table_as_key_value_rows(table_buffer, lines, bullet="•")

    return "\n".join(lines).strip()


def format_feishu_markdown(content: str) -> str:
    """
    将通用 Markdown 转换为飞书 lark_md 更友好的格式

    转换规则：
    - 飞书不支持 Markdown 标题（# / ## / ###），用加粗代替
    - 引用块使用前缀替代
    - 分隔线统一为细线
    - 表格转换为条目列表

    Args:
        content: 原始 Markdown 内容

    Returns:
        转换后的飞书 Markdown 格式内容

    Example:
        >>> markdown = "# 标题\\n> 引用\\n| 列1 | 列2 |"
        >>> formatted = format_feishu_markdown(markdown)
        >>> print(formatted)
        **标题**
        💬 引用
        • 列1：值1 | 列2：值2
    """
    def _flush_table_rows(buffer: List[str], output: List[str]) -> None:
        """将表格缓冲区中的行转换为飞书格式"""
        if not buffer:
            return

        def _parse_row(row: str) -> List[str]:
            """解析表格行，提取单元格"""
            return _parse_markdown_table_row(row)

        rows = []
        for raw in buffer:
            # 跳过分隔行（如 |---|---|）
            if re.match(r'^\s*\|?\s*[:-]+\s*(\|\s*[:-]+\s*)+\|?\s*$', raw):
                continue
            parsed = _parse_row(raw)
            if parsed:
                rows.append(parsed)

        if not rows:
            return

        header = rows[0]
        data_rows = rows[1:] if len(rows) > 1 else []
        for row in data_rows:
            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))
            pairs = []
            for idx, cell in enumerate(row):
                key = header[idx] if idx < len(header) else f"列{idx + 1}"
                pairs.append(f"{key}：{cell}")
            output.append(f"• {' | '.join(pairs)}")

    lines = []
    table_buffer: List[str] = []

    for raw_line in content.splitlines():
        line = raw_line.rstrip()

        # 处理表格行
        if line.strip().startswith('|'):
            table_buffer.append(line)
            continue

        # 刷新表格缓冲区
        if table_buffer:
            _flush_table_rows(table_buffer, lines)
            table_buffer = []

        # 转换标题（# ## ### 等）
        if re.match(r'^#{1,6}\s+', line):
            title = re.sub(r'^#{1,6}\s+', '', line).strip()
            line = f"**{title}**" if title else ""
        # 转换引用块
        elif line.startswith('> '):
            quote = line[2:].strip()
            line = f"💬 {quote}" if quote else ""
        # 转换分隔线
        elif line.strip() == '---':
            line = '────────'
        # 转换列表项
        elif line.startswith('- '):
            line = f"• {line[2:].strip()}"

        lines.append(line)

    # 处理末尾的表格
    if table_buffer:
        _flush_table_rows(table_buffer, lines)

    return "\n".join(lines).strip()


def _format_telegram_markdown_unprotected(content: str) -> str:
    """Convert common report Markdown to Telegram legacy Markdown."""

    result = _markdown_tables_to_key_value_rows_unprotected(content, bullet="-")
    result = re.sub(r'^#{1,6}\s+(.+)$', r'*\1*', result, flags=re.MULTILINE)
    result = re.sub(r'\*\*(.+?)\*\*', r'*\1*', result)
    result = re.sub(r'^\s*---+\s*$', '────────', result, flags=re.MULTILINE)
    result = _escape_telegram_non_link_markdown_chars(result)
    return result.strip()


def _escape_telegram_non_link_markdown_chars(content: str) -> str:
    """Escape Telegram Markdown link metacharacters outside valid links."""

    links: list[str] = []

    def _save_link(match: re.Match) -> str:
        links.append(match.group(0))
        return f"@@HRS_TELEGRAM_LINK_{len(links) - 1}@@"

    result = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', _save_link, content)
    for char in ("[", "]", "(", ")"):
        result = result.replace(char, f"\\{char}")

    for index, link in enumerate(links):
        result = result.replace(f"@@HRS_TELEGRAM_LINK_{index}@@", link)
    return result


def format_telegram_markdown(content: str) -> str:
    """Convert common report Markdown to Telegram legacy Markdown."""

    return _transform_outside_fenced_code_blocks(
        content,
        _format_telegram_markdown_unprotected,
    ).strip()


def format_wechat_markdown(content: str) -> str:
    """Keep WeChat Markdown style while making pipe tables mobile-readable."""

    result = markdown_tables_to_key_value_rows(content, bullet="•")
    result = re.sub(r'^\s*---+\s*$', '────────', result, flags=re.MULTILINE)
    return result.strip()


def _format_slack_mrkdwn_unprotected(content: str) -> str:
    """Convert common report Markdown to Slack mrkdwn."""

    result = _markdown_tables_to_key_value_rows_unprotected(content, bullet="•")
    result = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<\2|\1>', result)
    result = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<\2|\1>', result)
    result = re.sub(r'^#{1,6}\s+(.+)$', r'*\1*', result, flags=re.MULTILINE)
    result = re.sub(r'\*\*(.+?)\*\*', r'*\1*', result)
    result = re.sub(r'^\s*---+\s*$', '────────', result, flags=re.MULTILINE)
    return result.strip()


def format_slack_mrkdwn(content: str) -> str:
    """Convert common report Markdown to Slack mrkdwn."""

    return _transform_outside_fenced_code_blocks(
        content,
        _format_slack_mrkdwn_unprotected,
    ).strip()
