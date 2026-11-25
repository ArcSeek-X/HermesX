/**
 * 组织管理页：标题、筛选工具栏、组织树表与新增/编辑/删除弹窗。
 * 只负责页面布局与错误提示；数据请求、选中态与弹窗状态由 useOrgManagement 管理。
 */

import { useEffect } from 'react';
import { AppPage } from '@components/layout/AppPage';
import { PageHeader } from '@components/layout/PageLayout/PageHeader';
import { HrsButton } from '@components/basic/HrsButton';
import { Plus } from 'lucide-react';
import { dismissToast, showToast } from '@components/basic/Toast';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { useOrgManagement } from '../../../hooks/useOrgManagement';
import { OrgSearchConditions } from './components/orgSearchConditions';
import { OrgTable } from './components/orgTable';
import { OrgEditorDialog } from './components/orgEditorDialog';
import { OrgDeleteDialog } from './components/orgDeleteDialog';
import { organizationErrorMessage } from './config/orgMsgMapper';

const ERROR_TOAST_DURATION = 5000;

export default function OrgManagementPage() {
  const { t } = useUiLanguage();
  const {
    orgTableData,
    orgSearchDraftData,
    setOrgSearchDraftFn,
    isOrgFetchingState,
    orgQueryErrorData,
    orgActionErrorData,
    orgActionFeedbackCode,
    orgEditorDialogData,
    orgDeleteDialogData,
    isOrgSavingState,
    isOrgDeletingState,
    isOrgPreparingEditorState,
    queryOrgTableFn,
    resetOrgSearchFn,
    retryOrgQueryFn,
    changeOrgTablePageFn,
    openOrgEditorDialogFn,
    closeOrgEditorDialogFn,
    submitOrgFormFn,
    openOrgDeletionFn,
    closeOrgDeletionFn,
    confirmOrgDeletionFn,
  } = useOrgManagement();

  // 查询失败提示常驻至重试触发；切换错误时销毁上一个 toast，避免重复。
  useEffect(() => {
    if (orgQueryErrorData == null) return;
    const queryErrorToastId = showToast.danger({
      title: t('layout.nav.orgManagement.title'),
      description: organizationErrorMessage(orgQueryErrorData, t),
      action: (
        <HrsButton size="xs" variant="outline" onClick={retryOrgQueryFn}>
          {t('orgManagement.retry')}
        </HrsButton>
      ),
      duration: ERROR_TOAST_DURATION,
    });
    return () => dismissToast(queryErrorToastId);
  }, [orgQueryErrorData, retryOrgQueryFn, t]);

  // 增删改操作失败时提示；编辑/删除弹窗打开时由弹窗自身展示错误，不重复弹 toast。
  useEffect(() => {
    if (orgActionErrorData == null || orgEditorDialogData || orgDeleteDialogData) return;
    const actionErrorToastId = showToast.danger({
      title: t('layout.nav.orgManagement.title'),
      description: organizationErrorMessage(orgActionErrorData, t),
      duration: ERROR_TOAST_DURATION,
    });
    return () => dismissToast(actionErrorToastId);
  }, [orgActionErrorData, orgEditorDialogData, orgDeleteDialogData, t]);

  /** 任一增删改流程进行中时禁用所有写操作入口，避免并发写入。 */
  const isOrgActionInProgressState = isOrgPreparingEditorState || isOrgSavingState || isOrgDeletingState;

  return (
    /* 页面顶层容器：撑满可用高度，内部各区块纵向排列 */
    <AppPage fill className="flex flex-col gap-4">
      {/* 页头：模块标题/描述，右侧为新增组织入口（增删改进行中禁用） */}
      <PageHeader
        title={t('layout.nav.orgManagement.title')}
        description={t('layout.nav.orgManagement.description')}
        rightSlot={
          <HrsButton
            size="sm"
            isDisabled={isOrgActionInProgressState}
            onClick={() => void openOrgEditorDialogFn()}
          >
            <Plus size={16} />
            {t('orgManagement.add')}
          </HrsButton>
        }
      />

      {/* 筛选区：按名称/性质/类型/状态填写条件，提交查询或重置 */}
      <OrgSearchConditions
        organizationSearch={orgSearchDraftData}
        onSearchChange={setOrgSearchDraftFn}
        onQueryOrganizations={queryOrgTableFn}
        onResetSearch={resetOrgSearchFn}
        isFetchingOrganizations={isOrgFetchingState}
      />

      {/* 操作反馈：增删改成功后的结果提示（失败走 toast / 弹窗，见上方两个 effect） */}
      {orgActionFeedbackCode && (
        <p role="status" className="text-sm text-muted-text">
          {t(`orgManagement.feedback.${orgActionFeedbackCode}`)}
        </p>
      )}

      {/* 组织树表：展示当前页根组织树，支持展开折叠、翻页与行内新增子级/编辑/删除 */}
      <OrgTable
        orgTableData={orgTableData}
        onPageChange={changeOrgTablePageFn}
        onAddChild={organization => void openOrgEditorDialogFn(organization, true)}
        onEditOrganization={organization => void openOrgEditorDialogFn(organization)}
        onDeleteOrganization={openOrgDeletionFn}
        isOrgFetchingState={isOrgFetchingState}
        areOrganizationActionsDisabled={isOrgActionInProgressState}
      />

      {/* 新增/编辑弹窗：存在编辑上下文时挂载，key 按组织 ID 区分以重置表单草稿 */}
      {orgEditorDialogData && (
        <OrgEditorDialog
          key={orgEditorDialogData.organizationId ?? 'new-organization'}
          orgEditorDialogData={orgEditorDialogData}
          isOrgSavingState={isOrgSavingState}
          organizationActionError={orgActionErrorData}
          onSaveOrganization={organizationFields => void submitOrgFormFn(organizationFields)}
          onCloseOrgEditorDialog={closeOrgEditorDialogFn}
        />
      )}

      {/* 删除确认弹窗：存在待删节点时挂载，确认后调用删除接口 */}
      {orgDeleteDialogData && (
        <OrgDeleteDialog
          orgDeleteDialogData={orgDeleteDialogData}
          isOrgDeletingState={isOrgDeletingState}
          organizationActionError={orgActionErrorData}
          onConfirmDeletion={() => void confirmOrgDeletionFn()}
          onCloseOrgDeletion={closeOrgDeletionFn}
        />
      )}
    </AppPage>
  );
}
