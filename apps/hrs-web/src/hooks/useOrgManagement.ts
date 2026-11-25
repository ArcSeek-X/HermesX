import { useCallback, useEffect, useRef, useState } from 'react';
import { organizationApi, OrganizationApiError } from '../api/system/organization';
import type { OrganizationEditorDef, OrganizationNodeDef, OrganizationPageDef, OrganizationQueryDef, OrganizationSearchDef, OrganizationWriteDef } from '../types/systemOrganization';
import { buildOrgFilterDataFn, createEmptyOrgWriteDataFn, createEmptyOrgSearchDataFn, flattenOrgNodeDataFn, buildOrgWriteDataFn } from '../pages/System/orgManagementPage/utils/organizationTree';

/** 写操作后的页面提示：三种成功态，以及写成功但列表刷新失败的两态。 */
type OrganizationFeedback = 'created' | 'updated' | 'deleted' | 'savedRefreshFailed' | 'deletedRefreshFailed' | null;

/** 每次调用返回新的查询对象，避免调用方复用同一对象时被后续修改污染。 */
const createInitOrgQuery = (): OrganizationQueryDef => ({ pageNum: 1, pageSize: 10, filterList: [] });

/**
 * 组织管理页面的全部状态与操作：单页树查询、展开、筛选、增删改弹窗与操作反馈。
 *
 * 三个关键设计约束：
 * - 当前页只保存根节点树的单页结果；父节点候选另取完整树。树形展开由 Table 内部管理，不发子节点请求。
 * - 查询与编辑弹窗各用递增代次号拒绝过期响应，避免快速切换筛选或关闭弹窗后结果错乱。
 * - 保存/删除用 ref 互斥锁防止重复提交；写失败保留弹窗草稿，写成功后再刷新列表。
 */
export function useOrgManagement() {
  // ── 列表查询状态 ──────────────────────────────────────────────────────────
  /** 当前页根节点树；total/pages 是全量统计，可能大于当前页的根节点数。 */
  const [orgTableData, setOrganizationPage] = useState<OrganizationPageDef>({ list: [], total: 0, pages: 0, pageNum: 1, pageSize: 10 });
  /** 搜索表单草稿，与已提交的筛选条件解耦：输入即时生效，点「查询」才发请求。 */
  const [orgSearchDraftData, setOrgSearchDraftFn] = useState<OrganizationSearchDef>(createEmptyOrgSearchDataFn);
  /** 初始为 true，让首屏直接显示加载态而不是闪一下空列表。 */
  const [isOrgFetchingState, setIsFetchingOrganizations] = useState(true);
  /** 查询失败原因，页面据此展示错误态与重试入口。 */
  const [orgQueryErrorData, setOrganizationQueryError] = useState<unknown>(null);
  /** 保存/删除失败原因，由编辑弹窗和删除确认框共用。 */
  const [orgActionErrorData, setOrganizationActionError] = useState<unknown>(null);
  /** 写操作结果提示，区分「成功」与「写成功但列表刷新失败」。 */
  const [orgActionFeedbackCode, setOrganizationFeedback] = useState<OrganizationFeedback>(null);

  // ── 弹窗状态 ──────────────────────────────────────────────────────────────
  /** 编辑弹窗入参；null 表示未打开。 */
  const [orgEditorDialogData, setOrganizationEditor] = useState<OrganizationEditorDef | null>(null);
  /** 删除确认框的目标组织；null 表示未打开。 */
  const [orgDeleteDialogData, setOrganizationToDelete] = useState<OrganizationNodeDef | null>(null);
  /** 弹窗准备阶段（拉取父候选树与详情）的加载态。 */
  const [isOrgPreparingEditorState, setIsPreparingOrganizationEditor] = useState(false);
  /** 保存中的加载态，用于禁用提交按钮。 */
  const [isOrgSavingState, setIsSavingOrganization] = useState(false);
  /** 删除中的加载态，用于禁用确认按钮。 */
  const [isOrgDeletingState, setIsDeletingOrganization] = useState(false);

  // ── 引用：跨渲染共享、但不触发重渲染的控制量 ──────────────────────────────
  /** 最近一次实际发出的查询，供「重试」和删除后原地刷新复用。 */
  const organizationQueryRef = useRef(createInitOrgQuery());
  /** 查询代次：只有最新一次请求能写回状态，旧响应一律丢弃。 */
  const queryGenerationRef = useRef(0);
  /** 弹窗代次：关闭弹窗后到达的旧响应不得重新写入弹窗状态。 */
  const editorGenerationRef = useRef(0);
  /** 写操作互斥锁：保存或删除进行中拒绝第二次提交。 */
  const mutationInFlightRef = useRef(false);
  /** 组件是否已挂载：卸载后所有异步回调都不再 setState。 */
  const isPageMountedRef = useRef(false);

  /**
   * 拉取一页组织树。页码越界时自动回退到最后一页重查；每个请求带代次号，
   * 过期或未挂载时直接丢弃结果。返回本次结果是否真正写回了页面。
   */
  const fetchOrganizationPage = useCallback(async (organizationQuery: OrganizationQueryDef): Promise<boolean> => {
    // 发请求前先递增代次，保证后发请求的代次一定更大。
    const queryGeneration = ++queryGenerationRef.current;
    organizationQueryRef.current = organizationQuery;
    setIsFetchingOrganizations(true);
    setOrganizationQueryError(null);
    try {
      let requestedQuery = organizationQuery;
      let fetchedPage = await organizationApi.queryOrganizations(requestedQuery);
      // 删除末页最后一条后，原页码会超过总页数；回退到最后一页重查，避免展示空列表。
      if (fetchedPage.total > 0 && fetchedPage.pageNum > fetchedPage.pages) {
        requestedQuery = { ...requestedQuery, pageNum: fetchedPage.pages };
        fetchedPage = await organizationApi.queryOrganizations(requestedQuery);
      }
      // 组件已卸载，或期间又发起了新查询：本次结果作废。
      if (!isPageMountedRef.current || queryGeneration !== queryGenerationRef.current) return false;
      // 记录回退后的真实页码，重试与删除后刷新都基于它。
      organizationQueryRef.current = requestedQuery;
      setOrganizationPage(fetchedPage);
      return true;
    } catch (queryError) {
      if (isPageMountedRef.current && queryGeneration === queryGenerationRef.current) setOrganizationQueryError(queryError);
      return false;
    } finally {
      if (isPageMountedRef.current && queryGeneration === queryGenerationRef.current) setIsFetchingOrganizations(false);
    }
  }, []);

  useEffect(() => {
    isPageMountedRef.current = true;
    let isInitialQueryCancelled = false;
    // 放到微任务里发首屏查询，避免在 render 阶段同步 setState。
    void Promise.resolve().then(() => {
      if (!isInitialQueryCancelled) void fetchOrganizationPage(createInitOrgQuery());
    });
    return () => {
      isInitialQueryCancelled = true;
      isPageMountedRef.current = false;
    };
  }, [fetchOrganizationPage]);

  /** 按草稿筛选查询：回到第一页，并清除上一次写操作留下的提示。 */
  function queryOrgTableFn() {
    setOrganizationFeedback(null);
    void fetchOrganizationPage({ ...createInitOrgQuery(), filterList: buildOrgFilterDataFn(orgSearchDraftData) });
  }

  /** 清空筛选草稿并恢复默认第一页。 */
  function resetOrgSearchFn() {
    setOrgSearchDraftFn(createEmptyOrgSearchDataFn());
    setOrganizationFeedback(null);
    void fetchOrganizationPage(createInitOrgQuery());
  }

  /** 用最后一次实际提交的查询重试，保留原有筛选条件与页码。 */
  const retryOrgQueryFn = useCallback(() => {
    void fetchOrganizationPage(organizationQueryRef.current);
  }, [fetchOrganizationPage]);

  /** 跳转分页；筛选条件沿用最后一次查询，不从草稿重新拼装。 */
  function changeOrgTablePageFn(pageNum: number) {
    void fetchOrganizationPage({ ...organizationQueryRef.current, pageNum });
  }

  /**
   * 打开新增/编辑弹窗：先取完整父候选树，编辑时再取详情，
   * 避免把当前页的过期字段（nature/type/remark 等）带进表单。
   * 新建子组织时从完整树中定位父节点，并继承其 enterpriseId。
   */
  async function openOrgEditorDialogFn(organizationTarget?: OrganizationNodeDef, isChildCreation = false) {
    const editorGeneration = ++editorGenerationRef.current;
    setIsPreparingOrganizationEditor(true);
    setOrganizationActionError(null);
    setOrganizationFeedback(null);
    try {
      const parentCandidates = await organizationApi.getParentCandidates();
      // 详情只在编辑已有组织时拉取；新增（含新建子组织）使用空字段。
      const latestOrganization = organizationTarget && !isChildCreation
        ? await organizationApi.getOrganization(organizationTarget.organizationId)
        : undefined;
      // 弹窗已关闭或又被重新打开：丢弃本次结果。
      if (!isPageMountedRef.current || editorGeneration !== editorGenerationRef.current) return;
      const initialFields = latestOrganization ? buildOrgWriteDataFn(latestOrganization) : createEmptyOrgWriteDataFn();
      if (organizationTarget && isChildCreation) {
        const currentParent = flattenOrgNodeDataFn(parentCandidates)
          .find(organization => organization.organizationId === organizationTarget.organizationId);
        if (!currentParent) throw new OrganizationApiError('ORGANIZATION_NOT_FOUND', 'Parent unavailable');
        initialFields.parentId = currentParent.organizationId;
        initialFields.enterpriseId = currentParent.enterpriseId;
      }
      setOrganizationEditor({ organizationId: latestOrganization?.organizationId ?? null, initialFields, parentCandidates, auditDetails: latestOrganization });
    } catch (editorError) {
      if (isPageMountedRef.current && editorGeneration === editorGenerationRef.current) setOrganizationActionError(editorError);
    } finally {
      if (isPageMountedRef.current && editorGeneration === editorGenerationRef.current) setIsPreparingOrganizationEditor(false);
    }
  }

  /** 关闭编辑弹窗并递增代次；保存进行中不允许关闭，避免写入中的结果丢失。 */
  function closeOrgEditorDialogFn() {
    if (!mutationInFlightRef.current) {
      editorGenerationRef.current++;
      setOrganizationEditor(null);
      setOrganizationActionError(null);
    }
  }

  /**
   * 提交新增/编辑。写失败时保留弹窗和草稿供用户直接重试；
   * 写成功后清空筛选、刷新第一页，并区分「写入成功」与「刷新失败」。
   */
  async function submitOrgFormFn(organizationFields: OrganizationWriteDef) {
    if (!orgEditorDialogData || mutationInFlightRef.current) return;
    mutationInFlightRef.current = true;
    setIsSavingOrganization(true);
    setOrganizationActionError(null);
    try {
      if (orgEditorDialogData.organizationId === null) await organizationApi.createOrganization(organizationFields);
      else await organizationApi.editOrganization(orgEditorDialogData.organizationId, organizationFields);
    } catch (saveError) {
      if (isPageMountedRef.current) {
        setOrganizationActionError(saveError);
        setIsSavingOrganization(false);
      }
      mutationInFlightRef.current = false;
      return;
    }
    if (isPageMountedRef.current) {
      setOrganizationEditor(null);
      setOrgSearchDraftFn(createEmptyOrgSearchDataFn());
      const didRefresh = await fetchOrganizationPage(createInitOrgQuery());
      if (isPageMountedRef.current) {
        // orgEditorDialogData 是本次调用闭包里的值，setState 不会改变它，可安全用于判定新增还是编辑。
        setOrganizationFeedback(didRefresh ? (orgEditorDialogData.organizationId === null ? 'created' : 'updated') : 'savedRefreshFailed');
        setIsSavingOrganization(false);
      }
    }
    mutationInFlightRef.current = false;
  }

  /** 打开删除确认框。 */
  function openOrgDeletionFn(organization: OrganizationNodeDef) {
    setOrganizationActionError(null);
    setOrganizationToDelete(organization);
  }

  /** 关闭删除确认框；删除进行中不允许取消。 */
  function closeOrgDeletionFn() {
    if (!mutationInFlightRef.current) {
      setOrganizationToDelete(null);
      setOrganizationActionError(null);
    }
  }

  /** 确认删除：成功后按最后一次查询原地刷新，末页删空时由 fetch 自动回退页码。 */
  async function confirmOrgDeletionFn() {
    if (!orgDeleteDialogData || mutationInFlightRef.current) return;
    mutationInFlightRef.current = true;
    setIsDeletingOrganization(true);
    setOrganizationActionError(null);
    try {
      await organizationApi.deleteOrganization(orgDeleteDialogData.organizationId);
    } catch (deleteError) {
      if (isPageMountedRef.current) {
        setOrganizationActionError(deleteError);
        setIsDeletingOrganization(false);
      }
      mutationInFlightRef.current = false;
      return;
    }
    if (isPageMountedRef.current) {
      setOrganizationToDelete(null);
      const didRefresh = await fetchOrganizationPage(organizationQueryRef.current);
      if (isPageMountedRef.current) {
        setOrganizationFeedback(didRefresh ? 'deleted' : 'deletedRefreshFailed');
        setIsDeletingOrganization(false);
      }
    }
    mutationInFlightRef.current = false;
  }

  return {
    /** 当前页组织树与分页统计；list 为根节点树，total/pages 为全量统计 */
    orgTableData,
    /** 搜索表单草稿，输入即时生效，点「查询」才提交 */
    orgSearchDraftData,
    /** 更新搜索表单草稿 */
    setOrgSearchDraftFn,
    /** 列表查询进行中 */
    isOrgFetchingState,
    /** 查询失败原因，供页面展示重试入口 */
    orgQueryErrorData,
    /** 保存/删除失败原因，由对应弹窗内部展示 */
    orgActionErrorData,
    /** 写操作结果码：新增/编辑/删除成功，或写入成功但列表刷新失败 */
    orgActionFeedbackCode,
    /** 新增/编辑弹窗上下文；null 表示未打开 */
    orgEditorDialogData,
    /** 删除弹窗上下文（待删除的组织节点）；null 表示未打开 */
    orgDeleteDialogData,
    /** 弹窗数据准备中（拉取父候选树与详情） */
    isOrgPreparingEditorState,
    /** 保存进行中 */
    isOrgSavingState,
    /** 删除进行中 */
    isOrgDeletingState,
    /** 按草稿筛选查询并回到第一页 */
    queryOrgTableFn,
    /** 清空筛选草稿并恢复默认第一页 */
    resetOrgSearchFn,
    /** 用最后一次实际发出的查询重试，保留筛选条件与页码 */
    retryOrgQueryFn,
    /** 跳转到指定页，筛选条件沿用最后一次查询 */
    changeOrgTablePageFn,
    /** 打开新增/编辑弹窗；传目标为编辑，传目标且 isChildCreation 为新建子组织 */
    openOrgEditorDialogFn,
    /** 关闭编辑弹窗并递增弹窗代次；保存进行中不允许关闭 */
    closeOrgEditorDialogFn,
    /** 提交组织表单（新增/编辑）；失败保留草稿，成功后清空筛选并刷新第一页 */
    submitOrgFormFn,
    /** 打开删除确认框 */
    openOrgDeletionFn,
    /** 关闭删除确认框；删除进行中不允许取消 */
    closeOrgDeletionFn,
    /** 确认删除并按最后一次查询原地刷新，末页删空时自动回退页码 */
    confirmOrgDeletionFn,
  };
}
