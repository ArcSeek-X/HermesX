/**
 * 组织管理错误码到文案的映射：把 API 抛出的业务码转换为可展示的提示。
 * 不在映射内的错误码与非 API 异常统一按连接失败处理。
 */

import { OrganizationApiError } from '../../../../api/system/organization';
import type { UiTextKey } from '../../../../i18n/uiText-zh';

/** 服务端业务码 -> i18n key；多个码可映射到同一文案（如树深/祖先链超限）。 */
const organizationErrorKeys: Record<string, UiTextKey> = {
  HAS_CHILDREN: 'orgManagement.error.children',
  DEPARTMENT_IN_USE: 'orgManagement.error.members',
  INVALID_PARENT: 'orgManagement.error.parent',
  SCOPE_MISMATCH: 'orgManagement.error.enterprise',
  ORGANIZATION_NOT_FOUND: 'orgManagement.error.missing',
  INVALID_REQUEST: 'orgManagement.error.validation',
  TREE_TOO_DEEP: 'orgManagement.error.depth',
  ANCESTORS_TOO_LONG: 'orgManagement.error.depth',
  UNAUTHENTICATED: 'orgManagement.error.authentication',
  FORBIDDEN: 'orgManagement.error.forbidden',
  CSRF_INVALID: 'orgManagement.error.csrf',
  INVALID_RESPONSE: 'orgManagement.error.contract',
};

/**
 * 把错误对象转换为可展示的组织管理提示文案。
 * 只有 OrganizationApiError 且业务码在映射表内才取对应文案；其余（含网络异常）回退到连接失败提示。
 *
 * @param organizationError 捕获到的异常对象
 * @param translate 当前语言的文案翻译函数
 * @returns 可直接展示的提示文案
 */
export function organizationErrorMessage(organizationError: unknown, translate: (translationKey: UiTextKey) => string): string {
  const translationKey = organizationError instanceof OrganizationApiError
    ? organizationErrorKeys[organizationError.resultCode]
    : undefined;
  return translate(translationKey ?? 'orgManagement.error.connection');
}
