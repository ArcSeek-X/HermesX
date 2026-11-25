/**
 * 组织删除确认弹窗：展示组织名称与关联保护提示，确认后由页面 hook 调用删除接口。
 * 是否允许删除（如存在子组织/成员）由服务端判定，错误信息在弹窗内展示。
 */

import { Modal } from '@components/basic/Modal';
import { HrsButton } from '@components/basic/HrsButton';
import { useUiLanguage } from '../../../../contexts/UiLanguageContext';
import type { OrganizationNodeDef } from '../../../../types/systemOrganization';
import { organizationErrorMessage } from '../config/orgMsgMapper';

interface OrgDeleteDialogProps {
  /** 待删除的组织节点 */
  orgDeleteDialogData: OrganizationNodeDef;
  /** 删除进行中：禁用取消按钮、确认按钮显示加载态、弹窗不可点遮罩关闭 */
  isOrgDeletingState: boolean;
  /** 服务端返回的删除错误，在弹窗内展示 */
  organizationActionError: unknown;
  /** 确认删除 */
  onConfirmDeletion: () => void;
  /** 取消删除 */
  onCloseOrgDeletion: () => void;
}

export function OrgDeleteDialog(props: OrgDeleteDialogProps) {
  const { t } = useUiLanguage();

  return (
    <Modal
      isOpen
      onClose={props.onCloseOrgDeletion}
      isDismissable={!props.isOrgDeletingState}
      hideCloseButton={props.isOrgDeletingState}
      size="sm"
    >
      <Modal.Header>
        <Modal.Heading>{t('orgManagement.delete')}</Modal.Heading>
      </Modal.Header>

      <Modal.Body>
        <p>{t('orgManagement.deleteDescription', { name: props.orgDeleteDialogData.name })}</p>
        <p className="mt-2 text-sm text-muted-text">{t('orgManagement.deleteGuard')}</p>
        {props.organizationActionError != null && (
          <p role="alert" className="mt-3 text-sm text-danger">
            {organizationErrorMessage(props.organizationActionError, t)}
          </p>
        )}
      </Modal.Body>

      <Modal.Footer>
        <HrsButton
          variant="outline"
          isDisabled={props.isOrgDeletingState}
          onClick={props.onCloseOrgDeletion}
        >
          {t('common.cancel')}
        </HrsButton>
        <HrsButton
          variant="danger"
          isLoading={props.isOrgDeletingState}
          onClick={props.onConfirmDeletion}
        >
          {t('orgManagement.delete')}
        </HrsButton>
      </Modal.Footer>
    </Modal>
  );
}
