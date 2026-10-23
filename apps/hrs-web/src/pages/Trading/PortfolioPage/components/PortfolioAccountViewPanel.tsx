/**
 * 账户视图面板（页面左侧栏）
 *
 * 展示账户列表并提供账户切换、新建、编辑、删除；新建与编辑共用同一个账户表单弹窗。
 * 账户数据与操作均来自 useAccountView，本组件只负责渲染与交互转发。
 */

import type React from 'react';
import {
  AnimCard,
  ConfirmDialog,
  HrsButton,
  HrsInput,
  HrsSelect,
  InlineAlert,
  Modal,
  Separator,
} from '@components';
import { ListCard } from '@components/common/Card';
import { Plus, Wallet } from 'lucide-react';

import { useUiLanguage } from '../../../../contexts/UiLanguageContext';
import { formatUiText } from '../../../../i18n/uiText';
import { PORTFOLIO_TEXT } from '../../../../locales/featureText';
import type { PortfolioAccountMarket, PortfolioCostMethod } from '../../../../types/portfolio';
import { ACCOUNT_MARKET_OPTIONS, type UseAccountViewResult } from '../../../../hooks';

interface PortfolioAccountViewPanelProps {
  /** 账户视图数据（列表 / 选中 / 增删改操作） */
  accountView: UseAccountViewResult;
  /** 成本口径：FIFO / 加权平均（页面级状态，决定快照与风险的估值方式） */
  costMethod: PortfolioCostMethod;
  /** 成本口径切换回调 */
  onCostMethodChange: (method: PortfolioCostMethod) => void;
}

export const PortfolioAccountViewPanel: React.FC<PortfolioAccountViewPanelProps> = ({
  accountView,
  costMethod,
  onCostMethodChange,
}) => {
  const { language } = useUiLanguage();
  const text = PORTFOLIO_TEXT[language];
  const {
    accounts,
    selectedAccount,
    positionCounts,
    selectAccount,
    accountFormMode,
    accountForm,
    accountFormError,
    isSubmittingAccount,
    openCreateAccount,
    openEditAccount,
    updateAccountForm,
    submitAccountForm,
    closeAccountForm,
    requestAccountRemoval,
    pendingAccountRemoval,
    confirmAccountRemoval,
    cancelAccountRemoval,
    isDeletingAccount,
  } = accountView;

  const isEditing = accountFormMode === 'edit';

  return (
    <>
      <AnimCard className="flex-col p-4 h-full">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-foreground">
            {text.accountView}
            <span className="ml-1 text-xs font-normal text-foreground-soft">({accounts.length})</span>
          </span>
          <HrsButton variant="primary" size="sm" onClick={openCreateAccount}>
            <Plus className="h-4 w-4 m-0" />
            {text.createAccount}
          </HrsButton>
        </div>
        <Separator className="mt-4 mb-3" />
        <div>
          <span className="mb-1.5 block text-xs font-medium text-foreground-soft">{text.costMethod}</span>
          <HrsSelect
            value={costMethod}
            onChange={(v) => onCostMethodChange(v as PortfolioCostMethod)}
            options={[
              { key: 'fifo', label: text.fifo },
              { key: 'avg', label: text.avg },
            ]}
            className="w-full"
            aria-label={text.costMethod}
          />
        </div>

        <Separator className="mt-5 mb-2" />

        <div className="space-y-1.5 max-h-[70vh] overflow-y-auto pr-1">
          <ListCard
            icon={Wallet}
            title={text.allAccounts}
            isActive={selectedAccount === 'all'}
            count={accounts.length}
            onClick={() => selectAccount('all')}
            ordinal={0}
          />
          {accounts.map((account, index) => (
            <ListCard
              key={account.id}
              icon={Wallet}
              title={account.name}
              isActive={selectedAccount === account.id}
              count={positionCounts.get(account.id) ?? 0}
              onClick={() => selectAccount(account.id)}
              ordinal={index + 1}
              onEdit={() => openEditAccount(account)}
              onDelete={() => requestAccountRemoval(account)}
            />
          ))}
        </div>
      </AnimCard>

      <Modal isOpen={accountFormMode !== null} onClose={closeAccountForm} size="md">
        <Modal.Header>
          <Modal.Heading>{isEditing ? text.editAccount : text.createAccount}</Modal.Heading>
        </Modal.Header>
        <Modal.Body>
          {accountFormError ? (
            <InlineAlert
              variant="danger"
              className="mb-2 rounded-lg px-2 py-1 text-xs shadow-none"
              title={isEditing ? '更新账户失败' : '创建账户失败'}
              message={accountFormError}
            />
          ) : null}
          <form className="space-y-2" onSubmit={submitAccountForm}>
            <HrsInput
              className="w-full"
              placeholder="账户名称（必填）"
              value={accountForm.name}
              onChange={(e) => updateAccountForm({ name: e.target.value })}
            />
            <HrsInput
              className="w-full"
              placeholder="券商（可选，如 Demo/华泰）"
              value={accountForm.broker}
              onChange={(e) => updateAccountForm({ broker: e.target.value })}
            />
            <HrsInput
              className="w-full"
              placeholder="基准币（如 CNY/USD/HKD）"
              value={accountForm.baseCurrency}
              onChange={(e) => updateAccountForm({ baseCurrency: e.target.value.toUpperCase() })}
            />
            <HrsSelect
              value={accountForm.market}
              onChange={(v) => updateAccountForm({ market: v as PortfolioAccountMarket })}
              options={ACCOUNT_MARKET_OPTIONS}
            />
            {!isEditing ? (
              <p className="text-xs text-foreground-soft">创建成功后会自动切换到该账户。</p>
            ) : null}
            <HrsButton
              type="submit"
              variant="primary"
              className="w-full"
              isDisabled={isSubmittingAccount}
            >
              {isSubmittingAccount
                ? (isEditing ? text.updatingAccount : '创建中...')
                : (isEditing ? text.editAccount : text.createAccount)}
            </HrsButton>
          </form>
        </Modal.Body>
      </Modal>

      <ConfirmDialog
        isOpen={Boolean(pendingAccountRemoval)}
        title={text.deleteAccountTitle}
        message={
          pendingAccountRemoval
            ? formatUiText(text.deleteAccountMessage, {
              name: pendingAccountRemoval.accountName,
              id: pendingAccountRemoval.accountId,
            })
            : ''
        }
        confirmText={isDeletingAccount ? text.deletingAccount : text.deleteAccountConfirm}
        isDanger
        onConfirm={confirmAccountRemoval}
        onCancel={cancelAccountRemoval}
      />
    </>
  );
};
