/**
 * 简体中文（zh）主字典聚合出口：按类别合并拆分后的文案分片。
 *
 * 对外两个出口：
 * - 默认导出 zh：完整 key → 文案映射，供 uiText.ts 聚合三语；
 * - UiTextKey：由合并结果推导的 key 联合类型，是三语 key 集合的唯一真源。
 *
 * 新增文案时按类别修改对应分片；分片之间不得出现重复 key，否则后者会静默覆盖前者。
 */

import { commonZh } from './common-zh';
import { languageZh } from './language-zh';
import { themeZh } from './theme-zh';
import { layoutZh } from './layout-zh';
import { navZh } from './nav-zh';
import { componentZh } from './component-zh';
import { dataSourceZh } from './dataSource-zh';
import { exceptionZh } from './exception-zh';
import { authZh } from './auth-zh';
import { columnZh } from './column-zh';
import { pageZh } from './page-zh';

const zh = {
  ...commonZh,
  ...languageZh,
  ...themeZh,
  ...layoutZh,
  ...navZh,
  ...componentZh,
  ...dataSourceZh,
  ...exceptionZh,
  ...authZh,
  ...columnZh,
  ...pageZh,
} as const;

export type UiTextKey = keyof typeof zh;

export default zh;
