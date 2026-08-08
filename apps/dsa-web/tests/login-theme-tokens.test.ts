// @vitest-environment node

/**
 * 文件介绍（login-theme-tokens.test.ts）
 * ============================================================
 * 本文件用于校验「登录页（Login）专属主题变量（CSS 自定义属性 / Design Token）」
 * 是否同时在浅色（:root）与深色（.dark）主题块中被定义。
 *
 * 功能概括：
 * - 维护一份「登录页必需的 CSS Token 清单」REQUIRED_LOGIN_TOKENS，
 *   覆盖按钮文字、标签文字、提示文字、输入框图标、显隐切换按钮的背景/
 *   边框/文字以及其 hover、active、focus-ring 等各种交互态颜色。
 * - 读取 `src/index.css`，通过正则抽取 `:root { ... }` 与 `.dark { ... }`
 *   两个主题块，断言每个必需 Token 都存在于对应主题块内。
 * - 目的：确保登录页在明暗两套主题下都能正确取到颜色变量，避免
 *   因遗漏 Token 导致某主题下登录控件颜色缺失或回退异常。
 */

// 引入 Node 文件系统与路径工具，用于在测试内读取 index.css
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
// 引入 Vitest 测试原语
import { describe, expect, it } from 'vitest';

// 登录页必需的 CSS 主题 Token 清单（变量名即语义，涵盖交互的各态）
const REQUIRED_LOGIN_TOKENS = [
  '--login-button-text',                 // 登录按钮文字颜色
  '--login-label-text',                  // 表单标签文字颜色
  '--login-hint-text',                   // 辅助提示文字颜色
  '--login-input-icon',                  // 输入框图标颜色
  '--login-input-toggle-bg',             // 显隐切换按钮背景
  '--login-input-toggle-border',         // 显隐切换按钮边框
  '--login-input-toggle-text',           // 显隐切换按钮文字
  '--login-input-toggle-border-hover',   // hover 态边框
  '--login-input-toggle-bg-hover',       // hover 态背景
  '--login-input-toggle-text-hover',     // hover 态文字
  '--login-input-toggle-ring',           // focus 态聚焦环
  '--login-input-toggle-active-bg',      // active（按下）态背景
  '--login-input-toggle-active-border',  // active 态边框
  '--login-input-toggle-active-text',    // active 态文字
];

// 测试套件：登录主题 Token 校验
describe('login theme tokens', () => {
  // 用例 1：校验所有登录 Token 都定义于浅色主题根块（:root）
  it('defines all login-specific tokens in the light theme root block', () => {
    // 读取全局样式表
    const css = readFileSync(resolve(__dirname, '..', 'src', 'index.css'), 'utf8');
    // 正则抽取 :root { ... } 块（到首个 } 结束，主题块内部不含裸 } 的简写）
    const rootMatch = css.match(/:root\s*\{([\s\S]*?)\n\}/);

    // 必须能匹配到 :root 块，否则视为结构异常
    expect(rootMatch).not.toBeNull();
    const rootBlock = rootMatch?.[1] ?? '';

    // 逐个断言浅色主题块包含必需 Token
    for (const token of REQUIRED_LOGIN_TOKENS) {
      expect(rootBlock).toContain(token);
    }
  });

  // 用例 2：校验所有登录 Token 都定义于深色主题块（.dark）
  it('defines all login-specific tokens in the dark theme block', () => {
    const css = readFileSync(resolve(__dirname, '..', 'src', 'index.css'), 'utf8');
    // 正则抽取 .dark { ... } 块
    const darkMatch = css.match(/\.dark\s*\{([\s\S]*?)\n\}/);

    expect(darkMatch).not.toBeNull();
    const darkBlock = darkMatch?.[1] ?? '';

    // 逐个断言深色主题块包含必需 Token
    for (const token of REQUIRED_LOGIN_TOKENS) {
      expect(darkBlock).toContain(token);
    }
  });
});
