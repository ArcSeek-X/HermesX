/**
 * 英文（en）主字典聚合出口：分片结构与 uiText-zh/index.ts 一致。
 * 只做合并，不承载逻辑；key 集合由 uiText.ts 的类型约束与中文真源对齐。
 */

import { commonEn } from './common-en';
import { languageEn } from './language-en';
import { themeEn } from './theme-en';
import { layoutEn } from './layout-en';
import { navEn } from './nav-en';
import { componentEn } from './component-en';
import { dataSourceEn } from './dataSource-en';
import { exceptionEn } from './exception-en';
import { authEn } from './auth-en';
import { columnEn } from './column-en';
import { pageEn } from './page-en';

const en = {
  ...commonEn,
  ...languageEn,
  ...themeEn,
  ...layoutEn,
  ...navEn,
  ...componentEn,
  ...dataSourceEn,
  ...exceptionEn,
  ...authEn,
  ...columnEn,
  ...pageEn,
} as const;

export default en;
