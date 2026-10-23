/**
 * 组合页账户视图 Hook
 *
 * 负责账户列表加载、账户选择（localStorage 持久化）、账户创建 / 编辑 / 删除，
 * 并基于持仓快照派生各账户持仓条数。
 * 主页面只消费账户范围与写入许可，不重复持有账户状态。
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import type React from 'react';

import { getParsedApiError } from '../api/error';
import { portfolioApi } from '../api/portfolio';
import { usePreference } from './usePreference';
import type {
  AccountOption,
  PortfolioAccountItem,
  PortfolioAccountMarket,
  PortfolioSnapshotResponse,
} from '../types/portfolio';

/** 账户表单（新建 / 编辑共用） */
export interface AccountDraft {
  name: string;
  broker: string;
  market: PortfolioAccountMarket;
  baseCurrency: string;
}

/** 待删除账户 */
export interface PendingAccountRemoval {
  accountId: number;
  accountName: string;
}

/** 账户市场选项（与股票市场地区口径一致） */
export const ACCOUNT_MARKET_OPTIONS: Array<{ key: PortfolioAccountMarket; label: string }> = [
  { key: 'cn', label: '市场：A 股（cn）' },
  { key: 'hk', label: '市场：港股（hk）' },
  { key: 'us', label: '市场：美股（us）' },
  { key: 'jp', label: '市场：日股（jp）' },
  { key: 'kr', label: '市场：韩股（kr）' },
  { key: 'tw', label: '市场：台股（tw）' },
];

const INITIAL_ACCOUNT_DRAFT: AccountDraft = {
  name: '',
  broker: 'Demo',
  market: 'cn',
  baseCurrency: 'CNY',
};

interface UseAccountViewOptions {
  snapshot: PortfolioSnapshotResponse | null;
  onError: (error: unknown) => void;
}

export function useAccountView({ snapshot, onError }: UseAccountViewOptions) {
  const [accounts, setAccounts] = useState<PortfolioAccountItem[]>([]);
  const [selectedAccount, setSelectedAccount] = usePreference<AccountOption>('portfolio-selected-account', 'all');
  const [pendingAccountRemoval, setPendingAccountRemoval] = useState<PendingAccountRemoval | null>(null);
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);

  // 账户表单（新建 / 编辑共用）：mode 为 null 表示弹窗关闭
  const [accountFormMode, setAccountFormMode] = useState<'create' | 'edit' | null>(null);
  const [accountForm, setAccountForm] = useState<AccountDraft>(INITIAL_ACCOUNT_DRAFT);
  const [accountFormError, setAccountFormError] = useState<string | null>(null);
  const [isSubmittingAccount, setIsSubmittingAccount] = useState(false);
  const [editingAccountId, setEditingAccountId] = useState<number | null>(null);

  const reloadAccounts = useCallback(async () => {
    try {
      const { accounts: accountList = [] } = await portfolioApi.getAccounts(false);
      setAccounts(accountList);
      setSelectedAccount((previous) => {
        if (accountList.length === 0) return 'all';
        if (previous !== 'all' && !accountList.some((account) => account.id === previous)) {
          return accountList[0].id;
        }
        return previous;
      });
    } catch (err) {
      onError(getParsedApiError(err));
    }
  }, [setSelectedAccount, onError]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void reloadAccounts();
  }, [reloadAccounts]);

  // 选中账户在删除后、账户列表重新拉取前的瞬间可能仍指向已删除的 id；
  // 此时回落为 undefined（与「全部账户」视图一致），避免对已删除账户发起快照 / 风险 / 事件等查询。
  // 列表尚未加载（accounts 为空）时不回落，保持首屏按持久化选中项查询。
  const queryAccountId = selectedAccount === 'all'
    ? undefined
    : (accounts.length > 0 && !accounts.some((account) => account.id === selectedAccount)
        ? undefined
        : selectedAccount);
  const writableAccount = selectedAccount === 'all'
    ? undefined
    : accounts.find((item) => item.id === selectedAccount);
  const writeBlocked = !writableAccount;

  const positionCounts = useMemo(() => {
    const counts = new Map<number, number>();
    for (const account of snapshot?.accounts ?? []) {
      counts.set(account.accountId, account.positions?.length ?? 0);
    }
    return counts;
  }, [snapshot]);

  const updateAccountForm = useCallback((patch: Partial<AccountDraft>) => {
    setAccountForm((previous) => ({ ...previous, ...patch }));
  }, []);

  const openCreateAccount = useCallback(() => {
    setAccountForm(INITIAL_ACCOUNT_DRAFT);
    setAccountFormError(null);
    setAccountFormMode('create');
  }, []);

  const openEditAccount = useCallback((account: PortfolioAccountItem) => {
    setEditingAccountId(account.id);
    setAccountForm({
      name: account.name,
      broker: account.broker ?? '',
      market: account.market,
      baseCurrency: account.baseCurrency,
    });
    setAccountFormError(null);
    setAccountFormMode('edit');
  }, []);

  const closeAccountForm = useCallback(() => {
    setAccountFormMode(null);
    setEditingAccountId(null);
    setAccountFormError(null);
  }, []);

  const submitAccountForm = useCallback(async (event: React.FormEvent) => {
    event.preventDefault();
    const name = accountForm.name.trim();
    if (!name) {
      setAccountFormError('账户名称不能为空。');
      return;
    }
    const payload = {
      name,
      broker: accountForm.broker.trim() || undefined,
      market: accountForm.market,
      baseCurrency: accountForm.baseCurrency.trim() || 'CNY',
    };
    try {
      setIsSubmittingAccount(true);
      setAccountFormError(null);
      if (accountFormMode === 'edit' && editingAccountId !== null) {
        await portfolioApi.updateAccount(editingAccountId, payload);
        setAccountFormMode(null);
        setEditingAccountId(null);
      } else {
        const created = await portfolioApi.createAccount(payload);
        setSelectedAccount(created.id);
        // 连续创建：保留弹窗并仅清空名称与券商，市场与币种沿用
        setAccountForm((previous) => ({ ...previous, name: '', broker: 'Demo' }));
      }
      await reloadAccounts();
    } catch (err) {
      setAccountFormError(
        getParsedApiError(err).message
        || (accountFormMode === 'edit' ? '更新账户失败，请稍后重试。' : '创建账户失败，请稍后重试。'),
      );
    } finally {
      setIsSubmittingAccount(false);
    }
  }, [accountForm, accountFormMode, editingAccountId, reloadAccounts, setSelectedAccount]);

  const requestAccountRemoval = useCallback((account: PortfolioAccountItem) => {
    if (isDeletingAccount) return;
    setPendingAccountRemoval({ accountId: account.id, accountName: account.name });
  }, [isDeletingAccount]);

  const confirmAccountRemoval = useCallback(async () => {
    if (!pendingAccountRemoval || isDeletingAccount) return;
    try {
      setIsDeletingAccount(true);
      await portfolioApi.deleteAccount(pendingAccountRemoval.accountId);
      const nextAccount = accounts.find((account) => account.id !== pendingAccountRemoval.accountId);
      setSelectedAccount(nextAccount?.id ?? 'all');
      setPendingAccountRemoval(null);
      await reloadAccounts();
    } catch (err) {
      onError(getParsedApiError(err));
    } finally {
      setIsDeletingAccount(false);
    }
  }, [pendingAccountRemoval, isDeletingAccount, accounts, setSelectedAccount, reloadAccounts, onError]);

  const cancelAccountRemoval = useCallback(() => {
    if (isDeletingAccount) return;
    setPendingAccountRemoval(null);
  }, [isDeletingAccount]);

  return {
    accounts,
    selectedAccount,
    queryAccountId,
    writableAccount,
    writeBlocked,
    positionCounts,
    reloadAccounts,
    selectAccount: setSelectedAccount,
    accountFormMode,
    accountForm,
    accountFormError,
    isSubmittingAccount,
    editingAccountId,
    openCreateAccount,
    openEditAccount,
    updateAccountForm,
    submitAccountForm,
    closeAccountForm,
    pendingAccountRemoval,
    requestAccountRemoval,
    confirmAccountRemoval,
    cancelAccountRemoval,
    isDeletingAccount,
  };
}

export type UseAccountViewResult = ReturnType<typeof useAccountView>;
