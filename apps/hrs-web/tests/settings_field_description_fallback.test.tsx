/**
 * 文件介绍（settings_field_description_fallback.test.tsx）
 * ============================================================
 * 本文件验证「设置项字段（SettingsField）」的「描述文案回退（fallback）」策略：
 * 当国际化（i18n）映射中不存在某个字段 key 的本地化描述时，组件应当
 * 回退使用字段 schema 自带的 `description`，而不是显示 key 本身或留空。
 *
 * 功能概括：
 * - 以「未映射字段（UNMAPPED_FALLBACK_FIELD）」为样例，渲染 SettingsField 组件
 *   的静态 HTML（renderToStaticMarkup），构造一个仅有 schema.description、
 *   没有 i18n 描述的字段。
 * - 断言渲染结果中包含 schema 中的描述文案 'schema fallback description'，
 *   证明回退链路生效：i18n 缺失 → 使用 schema 描述兜底。
 * - 这保证了新增配置项即使尚未补齐翻译，也能向用户展示有意义的说明，
 *   而不是暴露内部 key 或空白，提升设置页的可读性与健壮性。
 */

// 引入 Vitest 测试原语
import { describe, expect, it } from 'vitest';
// 引入 React 服务端静态渲染工具，将组件渲染为 HTML 字符串以便断言
import { renderToStaticMarkup } from 'react-dom/server';
// 引入被测组件 SettingsField（设置项字段渲染组件）
import { SettingsField } from '../src/components/settings/SettingsField';

// 测试套件：SettingsField 描述回退策略
describe('SettingsField description fallback', () => {
  // 用例：当 i18n 映射缺少该 key 的描述时，应使用 schema.description 兜底
  it('uses schema.description when i18n map has no description for key', () => {
    // 将 SettingsField 渲染为静态 HTML；传入一个未映射的字段
    const html = renderToStaticMarkup(
      <SettingsField
        // 字段运行态数据：key、当前值、原始值是否存在、是否脱敏等
        item={{
          key: 'UNMAPPED_FALLBACK_FIELD',
          value: '1',
          rawValueExists: true,
          isMasked: false,
          // 字段 schema 定义：标题、兜底描述、分类、数据类型、UI 控件等元信息
          schema: {
            key: 'UNMAPPED_FALLBACK_FIELD',
            title: 'Unmapped fallback field',
            description: 'schema fallback description',
            category: 'system',
            dataType: 'string',
            uiControl: 'text',
            isSensitive: false,
            isRequired: false,
            isEditable: true,
            defaultValue: null,
            options: [],
            validation: {},
            displayOrder: 9999,
          },
        }}
        // 受控值（当前值）与变更回调（此处无需真实行为）
        value="1"
        onChange={() => undefined}
      />
    );

    // 断言：渲染 HTML 中应包含 schema 中的兜底描述
    expect(html).toContain('schema fallback description');
  });
});
