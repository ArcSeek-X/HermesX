/**
 * 繁體中文（zh-Hant）主字典聚合出口：分片结构与 uiText-zh/index.ts 一致。
 * 只做合并，不承载逻辑；key 集合由 uiText.ts 的类型约束与中文真源对齐。
 */

import { commonZhHant } from './common-zh-Hant';
import { languageZhHant } from './language-zh-Hant';
import { themeZhHant } from './theme-zh-Hant';
import { layoutZhHant } from './layout-zh-Hant';
import { navZhHant } from './nav-zh-Hant';
import { componentZhHant } from './component-zh-Hant';
import { dataSourceZhHant } from './dataSource-zh-Hant';
import { exceptionZhHant } from './exception-zh-Hant';
import { authZhHant } from './auth-zh-Hant';
import { columnZhHant } from './column-zh-Hant';
import { pageZhHant } from './page-zh-Hant';

const zhHant = {
  ...commonZhHant,
  ...languageZhHant,
  ...themeZhHant,
  ...layoutZhHant,
  ...navZhHant,
  ...componentZhHant,
  ...dataSourceZhHant,
  ...exceptionZhHant,
  ...authZhHant,
  ...columnZhHant,
  ...pageZhHant,
} as const;

export default zhHant;
