/**
 * 组织新增/编辑弹窗：完整字段表单、未保存离开确认与提交前校验。
 * 表单使用本地草稿态，保存成功后由页面 hook 关闭弹窗；撤销修改时弹确认框。
 */

import { useState } from 'react';
import { Modal } from '@components/basic/Modal';
import { HrsInput } from '@components/basic/HrsInput';
import { HrsSelect } from '@components/basic/HrsSelect';
import { HrsButton } from '@components/basic/HrsButton';
import { HrsNumberField } from '@components/basic/NumberField';
import { TextArea } from '@components/basic/TextArea';
import { Switch } from '@components/basic/Switch';
import { useUiLanguage } from '../../../../contexts/UiLanguageContext';
import type { UiTextKey } from '../../../../i18n/uiText-zh';
import type { OrganizationEditorDef, OrganizationWriteDef } from '../../../../types/systemOrganization';
import { flattenOrgNodeDataFn, buildOrgParentOptionDataFn } from '../utils/organizationTree';
import { formatDateTime } from '../../../../utils/format';
import { organizationErrorMessage } from '../config/orgMsgMapper';

const MAX_ORGANIZATION_SORT = 2147483647;

interface OrgEditorDialogProps {
  /** 输入：编辑上下文，organizationId 为 null 表示新增，含初始字段、父节点候选与审计详情 */
  orgEditorDialogData: OrganizationEditorDef;
  /** 输入：保存中，禁用表单与取消按钮，提交按钮显示加载态 */
  isOrgSavingState: boolean;
  /** 输入：服务端返回的操作错误，在表单顶部展示 */
  organizationActionError: unknown;
  /** 输出：提交写入字段，由页面 hook 决定走新增还是编辑 */
  onSaveOrganization: (organizationFields: OrganizationWriteDef) => void;
  /** 输出：关闭弹窗（保存成功或放弃修改） */
  onCloseOrgEditorDialog: () => void;
}

export function OrgEditorDialog(props: OrgEditorDialogProps) {
  const { t } = useUiLanguage();
  const [organizationDraft, setOrganizationDraft] = useState(props.orgEditorDialogData.initialFields);
  const [organizationValidationKey, setOrganizationValidationKey] = useState<UiTextKey | null>(null);
  const [isDiscardConfirmationVisible, setIsDiscardConfirmationVisible] = useState(false);

  // 草稿与初始字段完全一致才允许直接关闭；用 JSON 比较覆盖所有字段。
  const organizationHasChanges = JSON.stringify(organizationDraft) !== JSON.stringify(props.orgEditorDialogData.initialFields);

  // 根节点作为固定选项；其余候选由工具函数排除自身及后代，避免形成环。
  const parentOptions = [
    { key: '0', label: t('orgManagement.root') },
    ...buildOrgParentOptionDataFn(
      props.orgEditorDialogData.parentCandidates,
      props.orgEditorDialogData.organizationId,
      organizationDraft.enterpriseId,
    ),
  ];

  /** 关闭前判断是否有未保存修改：保存中不允许关闭，有改动则弹确认框。 */
  function closeEditorDialog() {
    if (props.isOrgSavingState) return;
    if (organizationHasChanges) setIsDiscardConfirmationVisible(true);
    else props.onCloseOrgEditorDialog();
  }

  /**
   * 提交前校验必填与数值范围；通过后去掉首尾空格再交给页面保存。
   * 校验失败只更新表单内的提示，不清空用户已填内容。
   *
   * @param event 表单提交事件，需阻止默认刷新
   */
  function submitOrganization(event: React.FormEvent) {
    event.preventDefault();
    const isValidName = organizationDraft.name.trim().length > 0;
    const isValidSort = Number.isSafeInteger(organizationDraft.sort)
      && organizationDraft.sort >= 0
      && organizationDraft.sort <= MAX_ORGANIZATION_SORT;
    const isValidEnterprise = organizationDraft.enterpriseId === null
      || (Number.isSafeInteger(organizationDraft.enterpriseId) && organizationDraft.enterpriseId >= 1);
    if (!isValidName || !isValidSort || !isValidEnterprise) {
      setOrganizationValidationKey('orgManagement.error.validation');
      return;
    }
    setOrganizationValidationKey(null);
    props.onSaveOrganization({ ...organizationDraft, name: organizationDraft.name.trim() });
  }

  const organizationTextFields: {
    property: 'name' | 'shortName' | 'code' | 'leader' | 'phone' | 'email';
    labelKey: UiTextKey;
    maximumLength: number;
  }[] = [
    { property: 'name', labelKey: 'orgManagement.field.name', maximumLength: 100 },
    { property: 'shortName', labelKey: 'orgManagement.field.shortName', maximumLength: 64 },
    { property: 'code', labelKey: 'orgManagement.field.code', maximumLength: 64 },
    { property: 'leader', labelKey: 'orgManagement.field.leader', maximumLength: 64 },
    { property: 'phone', labelKey: 'orgManagement.field.phone', maximumLength: 32 },
    { property: 'email', labelKey: 'orgManagement.field.email', maximumLength: 128 },
  ];

  return (
    <>
      <Modal
        isOpen
        onClose={closeEditorDialog}
        isDismissable={!props.isOrgSavingState}
        hideCloseButton={props.isOrgSavingState}
        size="lg"
      >
        <Modal.Header>
          <Modal.Heading>
            {t(props.orgEditorDialogData.organizationId === null ? 'orgManagement.add' : 'orgManagement.edit')}
          </Modal.Heading>
        </Modal.Header>

        <Modal.Body>
          <form id="organization-editor-form" onSubmit={submitOrganization} className="space-y-4">
            {props.organizationActionError != null && (
              <p role="alert" className="text-sm text-danger">
                {organizationErrorMessage(props.organizationActionError, t)}
              </p>
            )}
            {organizationValidationKey && (
              <p role="alert" className="text-sm text-danger">{t(organizationValidationKey)}</p>
            )}

            <fieldset disabled={props.isOrgSavingState} className="grid min-w-0 gap-4 sm:grid-cols-2">
              <HrsSelect
                className="w-full sm:col-span-2"
                label={t('orgManagement.field.parent')}
                value={String(organizationDraft.parentId)}
                options={parentOptions}
                isDisabled={props.isOrgSavingState}
                onChange={parentOption => {
                  const parentId = Number(parentOption);
                  // 切换父组织时继承其 enterpriseId，保证子组织与父组织属于同一企业范围。
                  const selectedParent = flattenOrgNodeDataFn(props.orgEditorDialogData.parentCandidates)
                    .find(organization => organization.organizationId === parentId);
                  setOrganizationDraft(previousDraft => ({
                    ...previousDraft,
                    parentId,
                    enterpriseId: selectedParent ? selectedParent.enterpriseId : previousDraft.enterpriseId,
                  }));
                }}
              />

              {organizationTextFields.map(organizationField => (
                <label
                  key={organizationField.property}
                  className="flex min-w-0 flex-col gap-2 text-sm text-muted-text"
                >
                  {t(organizationField.labelKey)}{organizationField.property === 'name' ? ' *' : ''}
                  <HrsInput
                    className="w-full"
                    name={`organization-${organizationField.property}`}
                    value={organizationDraft[organizationField.property] ?? ''}
                    autoFocus={organizationField.property === 'name'}
                    type={organizationField.property === 'email' ? 'email' : 'text'}
                    maxLength={organizationField.maximumLength}
                    required={organizationField.property === 'name'}
                    onChange={event => setOrganizationDraft({
                      ...organizationDraft,
                      // 必填的名称保留原值；选填字段清空时归一为 null，与后端契约一致。
                      [organizationField.property]: organizationField.property === 'name'
                        ? event.target.value
                        : event.target.value || null,
                    })}
                  />
                </label>
              ))}

              {/* 字典未接入：性质/类型只回显已有值，不提供选择。 */}
              <HrsSelect
                className="w-full"
                label={t('orgManagement.field.nature')}
                value={organizationDraft.nature}
                options={organizationDraft.nature ? [{ key: organizationDraft.nature, label: organizationDraft.nature }] : []}
                isDisabled
                placeholder={t('orgManagement.dictionaryPending')}
              />
              <HrsSelect
                className="w-full"
                label={t('orgManagement.field.type')}
                value={organizationDraft.type}
                options={organizationDraft.type ? [{ key: organizationDraft.type, label: organizationDraft.type }] : []}
                isDisabled
                placeholder={t('orgManagement.dictionaryPending')}
              />

              <HrsNumberField
                label={t('orgManagement.field.sort')}
                value={organizationDraft.sort}
                minValue={0}
                maxValue={MAX_ORGANIZATION_SORT}
                onChange={organizationSort => setOrganizationDraft({ ...organizationDraft, sort: organizationSort })}
              />

              <div className="flex items-end pb-2">
                <Switch
                  label={t('orgManagement.field.status')}
                  checked={organizationDraft.status === 1}
                  disabled={props.isOrgSavingState}
                  onChange={isOrganizationEnabled => setOrganizationDraft({
                    ...organizationDraft,
                    status: isOrganizationEnabled ? 1 : 0,
                  })}
                />
              </div>

              <label className="flex flex-col gap-2 text-sm text-muted-text sm:col-span-2">
                {t('orgManagement.field.remark')}
                <TextArea
                  className="w-full"
                  value={organizationDraft.remark ?? ''}
                  rows={3}
                  maxLength={500}
                  onChange={event => setOrganizationDraft({
                    ...organizationDraft,
                    remark: event.target.value || null,
                  })}
                />
              </label>

              {/* 关联企业仅新增根节点可填：编辑或非根节点时由父组织继承。 */}
              <details className="sm:col-span-2">
                <summary className="cursor-pointer text-sm text-muted-text">
                  {t('orgManagement.enterpriseSection')}
                </summary>
                <div className="mt-3">
                  <HrsNumberField
                    label={t('orgManagement.field.enterprise')}
                    value={organizationDraft.enterpriseId ?? NaN}
                    minValue={1}
                    maxValue={Number.MAX_SAFE_INTEGER}
                    isDisabled={props.isOrgSavingState
                      || props.orgEditorDialogData.organizationId !== null
                      || organizationDraft.parentId !== 0}
                    onChange={enterpriseId => setOrganizationDraft({
                      ...organizationDraft,
                      enterpriseId: Number.isNaN(enterpriseId) ? null : enterpriseId,
                    })}
                  />
                  <p className="mt-2 text-xs text-muted-text">{t('orgManagement.enterpriseHint')}</p>
                </div>
              </details>
            </fieldset>

            {props.orgEditorDialogData.auditDetails && (
              <div className="border-t border-subtle pt-3 text-xs text-muted-text">
                <p>
                  {t('orgManagement.audit.created')}: {props.orgEditorDialogData.auditDetails.createBy}
                  {' · '}
                  {formatDateTime(props.orgEditorDialogData.auditDetails.createTime.replace(' ', 'T') + 'Z')}
                </p>
                <p>
                  {t('orgManagement.audit.updated')}: {props.orgEditorDialogData.auditDetails.updateBy}
                  {' · '}
                  {formatDateTime(props.orgEditorDialogData.auditDetails.updateTime.replace(' ', 'T') + 'Z')}
                </p>
              </div>
            )}
          </form>
        </Modal.Body>

        <Modal.Footer>
          <HrsButton variant="outline" isDisabled={props.isOrgSavingState} onClick={closeEditorDialog}>
            {t('common.cancel')}
          </HrsButton>
          <HrsButton type="submit" form="organization-editor-form" isLoading={props.isOrgSavingState}>
            {t('orgManagement.save')}
          </HrsButton>
        </Modal.Footer>
      </Modal>

      {/* 未保存修改时二次确认，避免误关丢失草稿 */}
      <Modal
        isOpen={isDiscardConfirmationVisible}
        onClose={() => setIsDiscardConfirmationVisible(false)}
        size="sm"
      >
        <Modal.Header><Modal.Heading>{t('orgManagement.discardTitle')}</Modal.Heading></Modal.Header>
        <Modal.Body>{t('orgManagement.discardDescription')}</Modal.Body>
        <Modal.Footer>
          <HrsButton variant="outline" onClick={() => setIsDiscardConfirmationVisible(false)}>
            {t('common.cancel')}
          </HrsButton>
          <HrsButton variant="danger" onClick={props.onCloseOrgEditorDialog}>
            {t('orgManagement.discard')}
          </HrsButton>
        </Modal.Footer>
      </Modal>
    </>
  );
}
