// @vitest-environment node

/**
 * 文件介绍（index.theme-bootstrap.test.ts）
 * ============================================================
 * 本文件是「主题（明暗模式）引导脚本」的回归测试，用于保证应用在 React
 * 挂载之前、首屏渲染之前就已经完成主题（theme）的预加载与初始化。
 *
 * 功能概括：
 * - 直接读取项目根目录的 `index.html` 源文件（而非运行页面），
 *   校验其中内联的主题引导脚本是否包含以下关键逻辑：
 *   1. 使用固定的 localStorage 键（'theme'）读取用户偏好；
 *   2. 将非法/缺失的存储值回退为 'dark'（默认暗色）；
 *   3. 在根元素上移除旧的 'light'/'dark' 类后，添加解析出的主题类；
 *   4. 同步设置根元素的 `colorScheme`，避免浏览器原生控件颜色闪烁。
 * - 目的是防止出现「首屏白屏/主题闪烁（FOUC）」：即在 JS 框架
 *   启动前就锁定正确的主题，避免页面先以错误主题渲染再跳变。
 */

// 引入 Node 文件系统与路径工具，用于在测试内读取 index.html
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
// 引入 Vitest 测试原语：describe 聚合用例，it 定义单条用例，expect 断言
import { describe, expect, it } from 'vitest';

// 测试套件：围绕「index.html 主题引导」展开
describe('index.html theme bootstrap', () => {
  // 用例：校验内联脚本在 React 挂载前预加载暗色，并尊重已存储的主题值
  it('preloads dark mode before React mounts and respects stored theme values', () => {
    // 从当前测试文件所在目录回溯到项目根目录，读取 index.html 文本
    const indexHtml = readFileSync(resolve(__dirname, '..', 'index.html'), 'utf8');

    // 断言 1：脚本中定义了存储主题为 'theme' 的常量
    expect(indexHtml).toContain("const storageKey = 'theme'");
    // 断言 2：读取已存储主题，若非 'light'/'dark' 则回退为 'dark'（默认暗色）
    expect(indexHtml).toContain("const theme = storedTheme === 'light' || storedTheme === 'dark' ? storedTheme : 'dark';");
    // 断言 3：先移除根元素上的 light/dark 类，避免样式残留
    expect(indexHtml).toContain("root.classList.remove('light', 'dark');");
    // 断言 4：将解析出的主题类加到根元素，驱动全局 CSS 变量切换
    expect(indexHtml).toContain('root.classList.add(theme);');
    // 断言 5：同步根元素的 colorScheme，保证原生表单控件颜色与主题一致
    expect(indexHtml).toContain('root.style.colorScheme = theme;');
  });
});
