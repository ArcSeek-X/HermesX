/**
 * 文件介绍（ui_governance.test.ts）
 * ============================================================
 * 本文件是「Web UI 治理（governance）」的静态守门测试，用于防止不符合规范
 * 的写法被重新引入应用源码（src 目录），属于「架构护栏」类测试。
 *
 * 功能概括：
 * - 递归扫描 src 目录下所有 .ts/.tsx 源文件（排除 .test 文件），
 *   收集为待检查文件清单。
 * - 守卫 1：禁止在常见可交互元素（button/a/input/textarea/select/div/span）
 *   上使用原生 `title=` 属性——应使用统一的 tooltip/无障碍方案替代，
 *   避免零散、不可控的原生提示。
 * - 守卫 2：禁止在应用源码中出现 `input-terminal` 这类类名的残留，
 *   避免遗留的终端输入框样式/结构污染生产产物。
 * - 通过「扫描源码并断言违规文件列表为空」的方式，保障 UI 规范长期不被破坏。
 */

// 引入 Node 文件系统与路径工具，用于遍历 src 目录
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
// 引入 Vitest 测试原语
import { describe, expect, it } from 'vitest';

// 以当前工作目录下的 src 为源码根目录
const srcRoot = join(process.cwd(), 'src');

// 正则 1：匹配常见可交互元素上的原生 title 属性（如 <button title="...">）
const nativeTitlePattern = /<(button|a|input|textarea|select|div|span)\b[^>]*\btitle=/;
// 正则 2：匹配残留的 input-terminal 类名
const inputTerminalPattern = /\binput-terminal\b/;

/**
 * 递归收集 src 目录下所有「非测试」的 .ts/.tsx 源文件
 * @param dir 待扫描目录
 * @returns 源文件绝对路径数组
 */
function collectSourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const fullPath = join(dir, entry);
    const stats = statSync(fullPath);

    // 目录：递归继续收集
    if (stats.isDirectory()) {
      return collectSourceFiles(fullPath);
    }

    // 非 .ts/.tsx 文件：跳过
    if (!/\.(ts|tsx)$/.test(fullPath)) {
      return [];
    }

    // 测试文件（*.test.*）：跳过，不纳入 UI 规范扫描范围
    if (/\.test\.(ts|tsx)$/.test(fullPath)) {
      return [];
    }

    // 普通源文件：纳入清单
    return [fullPath];
  });
}

// 预扫描所有待检查源文件
const sourceFiles = collectSourceFiles(srcRoot);

// 测试套件：Web UI 治理守卫
describe('web UI governance guards', () => {
  // 守卫 1：不得重新引入在常见交互元素上的原生 title 属性
  it('does not reintroduce native title attributes on common interactive elements', () => {
    // 筛选出违反规范的源文件
    const violations = sourceFiles.filter((filePath) => nativeTitlePattern.test(readFileSync(filePath, 'utf8')));
    // 断言违规列表为空
    expect(violations).toEqual([]);
  });

  // 守卫 2：应用源码中不得包含 input-terminal 残留
  it('keeps input-terminal out of application source', () => {
    const violations = sourceFiles.filter((filePath) => inputTerminalPattern.test(readFileSync(filePath, 'utf8')));
    expect(violations).toEqual([]);
  });
});
