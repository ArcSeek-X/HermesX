/**
 * 组织树派生工具：把搜索草稿转成后端筛选条件，并从组织树派生表格、表单与父节点候选数据。
 *
 * 职责边界：
 * - 只做纯数据转换，不发请求、不持有状态；
 * - 父节点候选必须基于完整树，不能用当前页筛选结果，否则合法后代会被误排除；
 * - 写入字段与节点字段严格分离，审计字段与 children 不进入保存请求体。
 */

import type { OrganizationFilterDef, OrganizationNodeDef, OrganizationSearchDef, OrganizationWriteDef } from '@/types/systemOrganization';

/** 父节点选项：key 对齐 HrsSelectOptionDef.key（选项值），label 为完整层级路径。 */
export type OrgParentOptionDef = { key: string; label: string };

/** 空搜索草稿：status 为空串代表不限，与下拉框「全部状态」选项对应。 */
export const createEmptyOrgSearchDataFn = (): OrganizationSearchDef => ({
  organizationName: '',
  organizationNature: '',
  organizationTypes: [],
  organizationStatus: '',
});

/** 空写入字段：默认根节点、启用状态，可空文本字段统一为 null，与后端写入契约一致。 */
export const createEmptyOrgWriteDataFn = (): OrganizationWriteDef => ({
  parentId: 0,
  name: '',
  shortName: null,
  code: null,
  email: null,
  phone: null,
  leader: null,
  nature: null,
  type: null,
  remark: null,
  sort: 0,
  status: 1,
  enterpriseId: null,
});

/**
 * 把搜索草稿转成后端 filterList：只提交用户实际填写的维度，名称先去除首尾空格。
 * status 由字符串选项转回数值，且显式区分 '0'（停用）与空串（不限），避免真值判断把 0 丢失。
 *
 * @param orgSearchDraftData - 搜索表单草稿
 * @returns 后端可识别的筛选条件数组；无条件时返回空数组
 */
export function buildOrgFilterDataFn(orgSearchDraftData: OrganizationSearchDef): OrganizationFilterDef[] {
  const orgFilterData: OrganizationFilterDef[] = [];
  const orgNameText = orgSearchDraftData.organizationName.trim();

  if (orgNameText) orgFilterData.push({ fieldName: 'name', comparison: 'LIKE', fieldValue: orgNameText });
  if (orgSearchDraftData.organizationNature) {
    orgFilterData.push({ fieldName: 'nature', comparison: 'EQUAL', fieldValue: orgSearchDraftData.organizationNature });
  }
  if (orgSearchDraftData.organizationTypes.length) {
    orgFilterData.push({ fieldName: 'type', comparison: 'IN', fieldValue: orgSearchDraftData.organizationTypes });
  }
  if (orgSearchDraftData.organizationStatus !== '') {
    const orgStatusValue = Number(orgSearchDraftData.organizationStatus);
    orgFilterData.push({ fieldName: 'status', comparison: 'EQUAL', fieldValue: orgStatusValue === 1 ? 1 : 0 });
  }

  return orgFilterData;
}

/**
 * 按先序把组织树摊平为节点数组，用于按主键定位节点或统计节点数。
 * 递归深度由 API 层的 MAX_ORG_NODE_DEPTH 约束，不会无限展开。
 *
 * @param orgRootNodesData - 根组织列表
 * @returns 先序遍历的所有节点，含根节点与各级子节点
 */
export function flattenOrgNodeDataFn(orgRootNodesData: OrganizationNodeDef[]): OrganizationNodeDef[] {
  return orgRootNodesData.flatMap(orgNodeData => [orgNodeData, ...flattenOrgNodeDataFn(orgNodeData.children)]);
}

/**
 * 从节点提取写入字段，只保留 OrganizationWriteDef 声明的字段。
 * organizationId、审计字段与 children 属于只读数据，不能回填到保存请求体。
 *
 * @param orgNodeData - 详情接口返回的组织节点
 * @returns 可直接提交的新增/编辑字段
 */
export function buildOrgWriteDataFn(orgNodeData: OrganizationNodeDef): OrganizationWriteDef {
  return {
    parentId: orgNodeData.parentId,
    name: orgNodeData.name,
    shortName: orgNodeData.shortName,
    code: orgNodeData.code,
    email: orgNodeData.email,
    phone: orgNodeData.phone,
    leader: orgNodeData.leader,
    nature: orgNodeData.nature,
    type: orgNodeData.type,
    remark: orgNodeData.remark,
    sort: orgNodeData.sort,
    status: orgNodeData.status,
    enterpriseId: orgNodeData.enterpriseId,
  };
}

/**
 * 生成父组织候选项：key 为组织主键字符串，label 为用 ' / ' 连接的完整层级路径。
 *
 * 约束：
 * - 编辑时跳过自身整棵子树，防止把组织挂到自己的后代形成环；
 * - 编辑时只保留同企业候选，后端按同一口径校验；
 * - 新增时不按企业过滤，企业归属由用户选定父节点后继承其 enterpriseId。
 *
 * @param orgRootNodesData - 完整组织树的根节点列表，不能传筛选后的当前页
 * @param editingOrgId - 正在编辑的组织主键；null 表示新增
 * @param enterpriseId - 编辑组织所属企业主键；新增时不参与筛选
 * @returns 供 HrsSelect 消费的父节点选项数组
 */
export function buildOrgParentOptionDataFn(
  orgRootNodesData: OrganizationNodeDef[],
  editingOrgId: number | null,
  enterpriseId: number | null,
): OrgParentOptionDef[] {
  const orgParentOptionData: OrgParentOptionDef[] = [];

  function collectOrgParentOptions(orgNodesData: OrganizationNodeDef[], orgParentNames: string[]): void {
    for (const orgNodeData of orgNodesData) {
      if (orgNodeData.organizationId === editingOrgId) continue;
      const orgPathNames = [...orgParentNames, orgNodeData.name];
      if (editingOrgId === null || orgNodeData.enterpriseId === enterpriseId) {
        orgParentOptionData.push({ key: String(orgNodeData.organizationId), label: orgPathNames.join(' / ') });
      }
      collectOrgParentOptions(orgNodeData.children, orgPathNames);
    }
  }

  collectOrgParentOptions(orgRootNodesData, []);
  return orgParentOptionData;
}
