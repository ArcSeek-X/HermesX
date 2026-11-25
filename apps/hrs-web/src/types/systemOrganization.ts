/** 组织管理 API 契约：字段命名与后端 organization_id 等主键一一对应。 */

/** 新增/编辑组织时提交的字段；organizationId 由后端生成，不在写入字段中。 */
export interface OrganizationWriteDef {
  /** 父组织主键，0 表示顶级组织 */
  parentId: number;
  /** 组织名称，必填 */
  name: string;
  /** 组织简称，可为空 */
  shortName: string | null;
  /** 组织编码，可为空 */
  code: string | null;
  /** 联系邮箱，可为空 */
  email: string | null;
  /** 联系电话，可为空 */
  phone: string | null;
  /** 负责人姓名，可为空 */
  leader: string | null;
  /** 组织性质（如行政/业务），可为空 */
  nature: string | null;
  /** 组织类型，可为空 */
  type: string | null;
  /** 备注，可为空 */
  remark: string | null;
  /** 同级排序值，越小越靠前 */
  sort: number;
  /** 启用状态：1=启用，0=停用 */
  status: 0 | 1;
  /** 关联企业主键，null 表示不关联企业 */
  enterpriseId: number | null;
}

/** 组织节点：写入字段 + 后端返回的审计字段与子节点树。 */
export interface OrganizationNodeDef extends OrganizationWriteDef {
  /** 组织主键（organization_id） */
  organizationId: number;
  /** 祖先 ID 路径，逗号分隔，由后端计算；根节点为空串 */
  ancestors: string;
  /** 创建人账号 */
  createBy: string;
  /** 最后更新人账号 */
  updateBy: string;
  /** 创建时间 */
  createTime: string;
  /** 最后更新时间 */
  updateTime: string;
  /** 子组织列表，叶子节点为空数组 */
  children: OrganizationNodeDef[];
}

/** 组织列表筛选条件：按字段 + 比较方式 + 值描述，对应后端 filterList。 */
export type OrganizationFilterDef =
  | { /** 按组织名称模糊匹配 */ fieldName: 'name'; comparison: 'LIKE'; fieldValue: string }
  | { /** 按组织性质精确匹配 */ fieldName: 'nature'; comparison: 'EQUAL'; fieldValue: string }
  | { /** 按组织类型集合匹配 */ fieldName: 'type'; comparison: 'IN'; fieldValue: string[] }
  | { /** 按启用状态精确匹配 */ fieldName: 'status'; comparison: 'EQUAL'; fieldValue: 0 | 1 };

/** 组织分页查询条件；pageNum 从 1 开始，filterList 为筛选条件数组。 */
export interface OrganizationQueryDef { pageNum: number; pageSize: number; filterList: OrganizationFilterDef[] }
/** 组织分页结果：list 为当前页根节点树，total/pages 为全量统计。 */
export interface OrganizationPageDef { list: OrganizationNodeDef[]; total: number; pages: number; pageNum: number; pageSize: number }
/** 页面搜索表单的中间态；status 为空串表示不限。 */
export interface OrganizationSearchDef { organizationName: string; organizationNature: string; organizationTypes: string[]; organizationStatus: '' | '0' | '1' }
/** 组织编辑弹窗入参：organizationId 为 null 表示新增；auditDetails 为详情里取到的审计字段。 */
export interface OrganizationEditorDef { organizationId: number | null; initialFields: OrganizationWriteDef; parentCandidates: OrganizationNodeDef[]; auditDetails?: OrganizationNodeDef }
