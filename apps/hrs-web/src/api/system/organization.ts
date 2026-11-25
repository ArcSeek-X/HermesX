/**
 * 组织管理 API：分页列表、父节点候选树、详情、新增、编辑与删除。
 *
 * 设计要点：
 * - 网络 JSON 不受 TypeScript 约束，所有入口响应在边界处按组织契约校验，异常数据直接报错；
 * - 业务码（resultCode）原样保留在 OrganizationApiError 中，由页面映射到提示文案；
 * - 读操作跳过缓存，避免组织树变更后父节点候选与列表读到旧数据。
 */

import axios from 'axios';
import apiClient from '@/api';
import type { OrganizationNodeDef, OrganizationPageDef, OrganizationQueryDef, OrganizationWriteDef } from '@/types/systemOrganization';

const ORG_API_ENDPOINT = '/api/system/organization';
/** 组织数据变动频繁；错误处理交给调用方，避免 API 层弹窗覆盖业务码对应的页面文案。 */
const ORG_REQUEST_OPTIONS = { skipCache: true, handleErrorLocally: true };

/** 可为空的文本字段：后端允许返回 null，但不允许返回数字或对象。 */
const ORG_OPTIONAL_TEXT_FIELDS = ['shortName', 'code', 'email', 'phone', 'leader', 'nature', 'type', 'remark'] as const;
/** 后端计算并返回的字符串字段，缺失即视为契约不符。 */
const ORG_AUDIT_TEXT_FIELDS = ['ancestors', 'createBy', 'updateBy', 'createTime', 'updateTime'] as const;
const MAX_ORG_NODE_DEPTH = 64;
const MAX_ORG_PAGE_SIZE = 100;

/** 携带服务端业务码的异常：业务失败、响应契约不符或服务不可达时统一抛出。 */
export class OrganizationApiError extends Error {
  readonly resultCode: string;

  /**
   * @param resultCode - 服务端业务码，或本地契约码 INVALID_RESPONSE / SERVICE_UNAVAILABLE
   * @param errorMsg - 排查用的错误说明，不直接作为页面提示
   */
  constructor(resultCode: string, errorMsg: string) {
    super(errorMsg);
    this.name = 'OrganizationApiError';
    this.resultCode = resultCode;
  }
}

/** 把未知响应收敛为对象；数组、null 与基本类型均不符合通用响应契约。 */
function requireOrgRecordFn(orgResponseData: unknown): Record<string, unknown> {
  if (orgResponseData === null || typeof orgResponseData !== 'object' || Array.isArray(orgResponseData)) {
    throw new OrganizationApiError('INVALID_RESPONSE', 'Invalid organization response');
  }
  return orgResponseData as Record<string, unknown>;
}

/** 主键、父键、排序、分页等数值必须是可无损表示且不小于下限的整数。 */
function isSafeOrgIntegerFn(fieldValue: unknown, minimumValue: number): fieldValue is number {
  return typeof fieldValue === 'number' && Number.isSafeInteger(fieldValue) && fieldValue >= minimumValue;
}

/** 组织契约断言：不通过即以 INVALID_RESPONSE 抛出，不用空数据掩盖联调问题。 */
function assertOrgContractFn(isValidState: boolean, contractErrorMsg: string): asserts isValidState {
  if (!isValidState) throw new OrganizationApiError('INVALID_RESPONSE', contractErrorMsg);
}

/**
 * 递归校验并规范化单个组织节点。
 * 共享 visitedOrgIdDataSet 可同时拦截重复主键与环形父子引用；orgNodeDepth 防止异常数据造成栈溢出。
 *
 * @param orgNodeResponseData - 服务端返回的单个节点（未知结构）
 * @param visitedOrgIdDataSet - 已访问主键集合，跨兄弟节点共享
 * @param orgNodeDepth - 当前节点深度，根节点为 1
 * @returns 通过契约校验的组织节点，children 已递归规范化
 */
function parseOrgNodeFn(
  orgNodeResponseData: unknown,
  visitedOrgIdDataSet = new Set<number>(),
  orgNodeDepth = 1,
): OrganizationNodeDef {
  const orgNodeData = requireOrgRecordFn(orgNodeResponseData);
  const orgNodeIdValue = orgNodeData.organizationId;
  const parentNodeIdValue = orgNodeData.parentId;

  assertOrgContractFn(orgNodeDepth <= MAX_ORG_NODE_DEPTH, 'Organization node is too deep');
  assertOrgContractFn(isSafeOrgIntegerFn(orgNodeIdValue, 1), 'Invalid organization id');
  assertOrgContractFn(!visitedOrgIdDataSet.has(orgNodeIdValue), 'Duplicate organization id');
  assertOrgContractFn(isSafeOrgIntegerFn(parentNodeIdValue, 0), 'Invalid parent organization id');
  assertOrgContractFn(typeof orgNodeData.name === 'string' && orgNodeData.name.trim().length > 0, 'Invalid organization name');
  assertOrgContractFn(isSafeOrgIntegerFn(orgNodeData.sort, 0), 'Invalid organization sort');
  assertOrgContractFn(orgNodeData.status === 0 || orgNodeData.status === 1, 'Invalid organization status');
  assertOrgContractFn(
    orgNodeData.enterpriseId === null || isSafeOrgIntegerFn(orgNodeData.enterpriseId, 1),
    'Invalid enterprise id',
  );
  assertOrgContractFn(Array.isArray(orgNodeData.children), 'Invalid organization children');

  for (const orgFieldName of ORG_OPTIONAL_TEXT_FIELDS) {
    const orgTextFieldValue = orgNodeData[orgFieldName];
    assertOrgContractFn(
      orgTextFieldValue === null || typeof orgTextFieldValue === 'string',
      `Invalid organization field ${orgFieldName}`,
    );
  }
  for (const orgFieldName of ORG_AUDIT_TEXT_FIELDS) {
    assertOrgContractFn(typeof orgNodeData[orgFieldName] === 'string', `Invalid organization audit field ${orgFieldName}`);
  }

  visitedOrgIdDataSet.add(orgNodeIdValue);
  const orgChildNodesData = orgNodeData.children.map((orgChildResponseData: unknown) => {
    const orgChildNode = parseOrgNodeFn(orgChildResponseData, visitedOrgIdDataSet, orgNodeDepth + 1);
    assertOrgContractFn(orgChildNode.parentId === orgNodeIdValue, 'Broken organization hierarchy');
    return orgChildNode;
  });

  // 断言已覆盖 OrganizationNodeDef 的全部字段；此处仅把 unknown 字典收敛到接口类型。
  return { ...orgNodeData, children: orgChildNodesData } as unknown as OrganizationNodeDef;
}

/**
 * 校验组织树根数组：每项必须是 parentId = 0 的根节点，整棵树主键不重复（环会被重复主键拦截）。
 *
 * @param orgTreeResponseData - 服务端返回的根组织数组
 * @returns 通过契约校验的根组织列表
 */
function parseOrgRootsFn(orgTreeResponseData: unknown): OrganizationNodeDef[] {
  assertOrgContractFn(Array.isArray(orgTreeResponseData), 'Invalid organization tree');
  const visitedOrgIdDataSet = new Set<number>();
  return orgTreeResponseData.map((orgRootResponseData: unknown) => {
    const orgRootNode = parseOrgNodeFn(orgRootResponseData, visitedOrgIdDataSet);
    assertOrgContractFn(orgRootNode.parentId === 0, 'Missing organization root');
    return orgRootNode;
  });
}

/**
 * 发起组织请求并解包通用响应包。
 * HTTP 失败时优先保留响应体业务码；无业务码时统一归为 SERVICE_UNAVAILABLE，
 * 使调用方始终能按 resultCode 映射提示，而不是收到裸 axios 错误。
 *
 * @param httpMethodCode - 请求方法：get / post
 * @param orgOperationPath - 接口路径（不含公共前缀）
 * @param orgRequestData - 请求体；GET 请求不传
 * @returns 通用响应中的 resultData，尚未做业务契约校验
 */
async function requestOrgDataFn(
  httpMethodCode: 'get' | 'post',
  orgOperationPath: string,
  orgRequestData?: unknown,
): Promise<unknown> {
  const orgRequestOptionsData = {
    ...ORG_REQUEST_OPTIONS,
    method: httpMethodCode,
    url: `${ORG_API_ENDPOINT}/${orgOperationPath}`,
    ...(orgRequestData === undefined ? {} : { data: orgRequestData }),
  };

  try {
    const orgApiResponseData = await apiClient.request<unknown>(orgRequestOptionsData);
    const orgApiEnvelopeData = requireOrgRecordFn(orgApiResponseData.data);
    const orgResultCode = orgApiEnvelopeData.resultCode;
    const orgResultMsg = orgApiEnvelopeData.resultMsg;
    assertOrgContractFn(
      typeof orgResultCode === 'string' && typeof orgResultMsg === 'string' && 'resultData' in orgApiEnvelopeData,
      'Invalid common response',
    );
    if (orgResultCode !== '200') throw new OrganizationApiError(orgResultCode, orgResultMsg);
    return orgApiEnvelopeData.resultData;
  } catch (orgRequestErrorData) {
    if (orgRequestErrorData instanceof OrganizationApiError) throw orgRequestErrorData;
    if (axios.isAxiosError(orgRequestErrorData)) {
      const orgErrorResponseData = orgRequestErrorData.response?.data;
      if (orgErrorResponseData && typeof orgErrorResponseData === 'object'
        && 'resultCode' in orgErrorResponseData && typeof orgErrorResponseData.resultCode === 'string') {
        const orgErrorMsg = 'resultMsg' in orgErrorResponseData ? String(orgErrorResponseData.resultMsg ?? '') : '';
        throw new OrganizationApiError(orgErrorResponseData.resultCode, orgErrorMsg);
      }
    }
    throw new OrganizationApiError('SERVICE_UNAVAILABLE', 'Organization service unavailable');
  }
}

export const organizationApi = {
  /**
   * 分页查询组织树。
   * 分页参数要求原样回显、总页数与总数/页大小自洽，避免页面拿到不自洽的分页状态。
   *
   * @param orgQueryData - 页码、页大小与筛选条件
   * @returns 当前页根组织树及分页统计
   */
  async queryOrganizations(orgQueryData: OrganizationQueryDef): Promise<OrganizationPageDef> {
    const orgPageData = requireOrgRecordFn(await requestOrgDataFn('post', 'list-organization', orgQueryData));
    const { total, pages, pageNum, pageSize } = orgPageData;
    assertOrgContractFn(
      isSafeOrgIntegerFn(total, 0)
        && isSafeOrgIntegerFn(pages, 0)
        && isSafeOrgIntegerFn(pageNum, 1)
        && isSafeOrgIntegerFn(pageSize, 1)
        && pageSize <= MAX_ORG_PAGE_SIZE
        && pages === Math.ceil(total / pageSize)
        && pageNum === orgQueryData.pageNum
        && pageSize === orgQueryData.pageSize,
      'Invalid organization pagination',
    );

    const orgRootNodesData = parseOrgRootsFn(orgPageData.list);
    assertOrgContractFn(
      orgRootNodesData.length <= pageSize && orgRootNodesData.length <= total,
      'Invalid organization root count',
    );
    return { list: orgRootNodesData, total, pages, pageNum, pageSize };
  },

  /**
   * 获取完整组织树，供编辑弹窗选择父节点。
   * @returns 校验通过的根组织列表
   */
  async getParentCandidates(): Promise<OrganizationNodeDef[]> {
    return parseOrgRootsFn(await requestOrgDataFn('get', 'get-organization-tree'));
  },

  /**
   * 获取单个组织详情（含祖先链等审计字段）。
   * @param organizationId - 组织主键
   * @returns 校验通过的组织节点
   */
  async getOrganization(organizationId: number): Promise<OrganizationNodeDef> {
    return parseOrgNodeFn(await requestOrgDataFn('get', `detail-organization/${organizationId}`));
  },

  /**
   * 新增组织。
   * @param orgWriteData - 组织写入字段，主键由后端生成
   * @returns 后端返回的新增节点
   */
  async createOrganization(orgWriteData: OrganizationWriteDef): Promise<OrganizationNodeDef> {
    return parseOrgNodeFn(await requestOrgDataFn('post', 'add-organization', orgWriteData));
  },

  /**
   * 编辑组织：主键随请求体提交。
   * @param organizationId - 待编辑组织主键
   * @param orgWriteData - 组织写入字段
   * @returns 后端返回的组织节点
   */
  async editOrganization(organizationId: number, orgWriteData: OrganizationWriteDef): Promise<OrganizationNodeDef> {
    return parseOrgNodeFn(await requestOrgDataFn('post', 'edit-organization', { ...orgWriteData, organizationId }));
  },

  /**
   * 删除组织：服务端结果必须严格为 true，避免把格式异常当成删除成功。
   * @param organizationId - 待删除组织主键
   */
  async deleteOrganization(organizationId: number): Promise<void> {
    const orgDeleteResult = await requestOrgDataFn('post', 'delete-organization', { organizationId });
    assertOrgContractFn(orgDeleteResult === true, 'Invalid deletion response');
  },
};
