/**
 * 手工录入弹窗
 *
 * 封装交易 / 资金流水 / 公司行为三类录入表单的本地状态、子页签切换与提交逻辑。
 * 提交成功后通过 onSuccess 回调通知主页面刷新核心数据（持仓/风险），
 * 校验与写入拦截提示通过 onWriteWarning 回传，接口错误通过 onError 回传，
 * 自身不感知账户列表与页面级刷新细节（账户范围由 writableAccountId 决定）。
 */

import type React from 'react';
import { useState } from 'react';
import { Modal, HrsButton, HrsInput, HrsSelect, HrsNumberField, TabNav } from '@components';
import { StockSearch } from '@components/StockSearch/StockSearch';
import { getTodayIso } from '@utils/portfolioFormat';
import { portfolioApi } from '../../../../../api/portfolio';
import type { ManualEntryTab } from '../../types';
import type {
  PortfolioCashDirection,
  PortfolioCorporateActionType,
  PortfolioSide,
} from '../../../../../types/portfolio';

/** 手工录入弹窗属性 */
interface ManualEntryModalProps {
  /** 是否打开弹窗 */
  isOpen: boolean;
  /** 关闭弹窗回调 */
  onClose: () => void;
  /** 可写账户 ID，为 undefined 时禁用提交并提示先选择账户 */
  writableAccountId?: number;
  /** 可写账户基准币，用于资金流水币种占位提示 */
  accountBaseCurrency?: string;
  /** 提交成功后回调（由主页面刷新持仓/风险等核心数据） */
  onSuccess: () => void;
  /** 统一错误回调 */
  onError: (error: unknown) => void;
  /** 写入拦截 / 校验提示回调 */
  onWriteWarning: (message: string | null) => void;
}

/** 手工录入子表单页签选项 */
const MANUAL_ENTRY_TABS = [
  { value: 'trade' as ManualEntryTab, label: '交易数据' },
  { value: 'cash' as ManualEntryTab, label: '资金流水' },
  { value: 'corporate' as ManualEntryTab, label: '公司行为' },
];

/** 写入拦截提示文案 */
const WRITE_BLOCKED_MESSAGE = '请先在上方账户视图选择具体账户，再进行录入或导入提交。';

export const ManualEntryModal: React.FC<ManualEntryModalProps> = ({
  isOpen,
  onClose,
  writableAccountId,
  accountBaseCurrency,
  onSuccess,
  onError,
  onWriteWarning,
}) => {
  const [manualEntryTab, setManualEntryTab] = useState<ManualEntryTab>('trade');

  // 三个子表单各自独立持有状态，切换互不干扰
  const [tradeForm, setTradeForm] = useState({
    symbol: '',
    tradeDate: getTodayIso(),
    side: 'buy' as PortfolioSide,
    quantity: '',
    price: '',
    fee: '',
    tax: '',
    tradeUid: '',
    note: '',
  });
  const [cashForm, setCashForm] = useState({
    eventDate: getTodayIso(),
    direction: 'in' as PortfolioCashDirection,
    amount: '',
    currency: '',
    note: '',
  });
  const [corpForm, setCorpForm] = useState({
    symbol: '',
    effectiveDate: getTodayIso(),
    actionType: 'cash_dividend' as PortfolioCorporateActionType,
    cashDividendPerShare: '',
    splitRatio: '',
    note: '',
  });
  // 股票搜索框选中后的展示文案（"名称（代码）"），提交成功后随 symbol 一并清空
  const [tradeDisplay, setTradeDisplay] = useState('');
  const [corpDisplay, setCorpDisplay] = useState('');

  /** 提交交易录入表单：验证账户与必填项后调用创建交易 API，成功后刷新并清空部分字段 */
  const handleTradeSubmit = async () => {
    if (!writableAccountId) {
      onWriteWarning(WRITE_BLOCKED_MESSAGE);
      return;
    }
    if (!tradeForm.symbol.trim() || !tradeForm.quantity || !tradeForm.price) {
      onWriteWarning('股票代码、数量、成交价为必填项。');
      return;
    }
    try {
      onWriteWarning(null);
      await portfolioApi.createTrade({
        accountId: writableAccountId,
        symbol: tradeForm.symbol,
        tradeDate: tradeForm.tradeDate,
        side: tradeForm.side,
        quantity: Number(tradeForm.quantity),
        price: Number(tradeForm.price),
        fee: Number(tradeForm.fee || 0),
        tax: Number(tradeForm.tax || 0),
        tradeUid: tradeForm.tradeUid || undefined,
        note: tradeForm.note || undefined,
      });
      await onSuccess();
      setTradeForm((prev) => ({ ...prev, symbol: '', tradeUid: '', note: '' }));
      setTradeDisplay('');
    } catch (err) {
      onError(err);
    }
  };

  /** 提交资金流水录入表单：验证账户与必填项后调用创建资金流水 API */
  const handleCashSubmit = async () => {
    if (!writableAccountId) {
      onWriteWarning(WRITE_BLOCKED_MESSAGE);
      return;
    }
    if (!cashForm.eventDate || !cashForm.amount) {
      onWriteWarning('交易日期与金额为必填项。');
      return;
    }
    try {
      onWriteWarning(null);
      await portfolioApi.createCashLedger({
        accountId: writableAccountId,
        eventDate: cashForm.eventDate,
        direction: cashForm.direction,
        amount: Number(cashForm.amount),
        currency: cashForm.currency || undefined,
        note: cashForm.note || undefined,
      });
      await onSuccess();
      setCashForm((prev) => ({ ...prev, note: '' }));
    } catch (err) {
      onError(err);
    }
  };

  /** 提交公司行为录入表单：按行为类型调用创建 API，成功后刷新并清空部分字段 */
  const handleCorporateSubmit = async () => {
    if (!writableAccountId) {
      onWriteWarning(WRITE_BLOCKED_MESSAGE);
      return;
    }
    const hasCorpValue = corpForm.cashDividendPerShare || corpForm.splitRatio;
    if (!corpForm.symbol.trim() || !corpForm.effectiveDate || !hasCorpValue) {
      onWriteWarning('股票代码、生效日期与分红/拆股比例为必填项。');
      return;
    }
    try {
      onWriteWarning(null);
      await portfolioApi.createCorporateAction({
        accountId: writableAccountId,
        symbol: corpForm.symbol,
        effectiveDate: corpForm.effectiveDate,
        actionType: corpForm.actionType,
        cashDividendPerShare: corpForm.cashDividendPerShare ? Number(corpForm.cashDividendPerShare) : undefined,
        splitRatio: corpForm.splitRatio ? Number(corpForm.splitRatio) : undefined,
        note: corpForm.note || undefined,
      });
      await onSuccess();
      setCorpForm((prev) => ({ ...prev, symbol: '', note: '' }));
      setCorpDisplay('');
    } catch (err) {
      onError(err);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <Modal.Header>
        <Modal.Heading>手工录入</Modal.Heading>
      </Modal.Header>
      <Modal.Body>
        <TabNav
          items={MANUAL_ENTRY_TABS}
          value={manualEntryTab}
          onChange={setManualEntryTab}
          variant="secondary"
          size="sm"
          ariaLabel="手工录入类型切换"
        />
        <div className="mt-3 grid">
          <form
            className={`space-y-2 col-start-1 row-start-1 ${manualEntryTab === 'trade' ? '' : 'invisible'}`}
            onSubmit={(e) => { e.preventDefault(); void handleTradeSubmit(); }}
          >
              <StockSearch
                value={tradeForm.symbol}
                displayValue={tradeDisplay || undefined}
                size="sm"
                originalRender
                onChange={(v) => setTradeForm((prev) => ({ ...prev, symbol: v }))}
                onSubmit={(_code, _name, source, meta) => {
                  if (source === 'autocomplete') setTradeDisplay(meta?.displayLabel ?? '');
                }}
              />
              <div className="grid grid-cols-2 gap-2">
                <HrsInput
                  type="date"
                  clearable={false}
                  className="w-full"
                  value={tradeForm.tradeDate}
                  onChange={(e) => setTradeForm((prev) => ({ ...prev, tradeDate: e.target.value }))}
                />
                <HrsSelect
                  value={tradeForm.side}
                  onChange={(v) => setTradeForm((prev) => ({ ...prev, side: v as PortfolioSide }))}
                  options={[
                    { key: 'buy', label: '买入' },
                    { key: 'sell', label: '卖出' },
                  ]}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <HrsNumberField
                  className="max-w-none"
                  minValue={0}
                  step={0.0001}
                  placeholder="数量（必填）"
                  value={tradeForm.quantity === '' ? undefined : Number(tradeForm.quantity)}
                  onChange={(v) => setTradeForm((prev) => ({ ...prev, quantity: v == null ? '' : String(v) }))}
                />
                <HrsNumberField
                  className="max-w-none"
                  minValue={0}
                  step={0.0001}
                  placeholder="成交价（必填）"
                  value={tradeForm.price === '' ? undefined : Number(tradeForm.price)}
                  onChange={(v) => setTradeForm((prev) => ({ ...prev, price: v == null ? '' : String(v) }))}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <HrsNumberField
                  className="max-w-none"
                  minValue={0}
                  step={0.0001}
                  placeholder="手续费（可选）"
                  value={tradeForm.fee === '' ? undefined : Number(tradeForm.fee)}
                  onChange={(v) => setTradeForm((prev) => ({ ...prev, fee: v == null ? '' : String(v) }))}
                />
                <HrsNumberField
                  className="max-w-none"
                  minValue={0}
                  step={0.0001}
                  placeholder="税费（可选）"
                  value={tradeForm.tax === '' ? undefined : Number(tradeForm.tax)}
                  onChange={(v) => setTradeForm((prev) => ({ ...prev, tax: v == null ? '' : String(v) }))}
                />
              </div>
              <p className="text-xs text-foreground-soft mt-4">手续费和税费可留空，系统将按 0 处理。</p>
            </form>

          <form
            className={`space-y-2 col-start-1 row-start-1 ${manualEntryTab === 'cash' ? '' : 'invisible'}`}
            onSubmit={(e) => { e.preventDefault(); void handleCashSubmit(); }}
          >
              <div className="grid grid-cols-2 gap-2">
                <HrsInput
                  type="date"
                  clearable={false}
                  className="w-full"
                  value={cashForm.eventDate}
                  onChange={(e) => setCashForm((prev) => ({ ...prev, eventDate: e.target.value }))}
                />
                <HrsSelect
                  value={cashForm.direction}
                  onChange={(v) => setCashForm((prev) => ({ ...prev, direction: v as PortfolioCashDirection }))}
                  options={[
                    { key: 'in', label: '流入' },
                    { key: 'out', label: '流出' },
                  ]}
                />
              </div>
              <HrsNumberField
                className="max-w-none"
                minValue={0}
                step={0.0001}
                placeholder="金额"
                value={cashForm.amount === '' ? undefined : Number(cashForm.amount)}
                onChange={(v) => setCashForm((prev) => ({ ...prev, amount: v == null ? '' : String(v) }))}
              />
              <HrsInput
                placeholder={`币种（可选，默认 ${accountBaseCurrency || '账户基准币'}）`}
                value={cashForm.currency}
                onChange={(e) => setCashForm((prev) => ({ ...prev, currency: e.target.value }))}
              />
            </form>

          <form
            className={`space-y-2 col-start-1 row-start-1 ${manualEntryTab === 'corporate' ? '' : 'invisible'}`}
            onSubmit={(e) => { e.preventDefault(); void handleCorporateSubmit(); }}
          >
              <StockSearch
                value={corpForm.symbol}
                displayValue={corpDisplay || undefined}
                originalRender
                onChange={(v) => setCorpForm((prev) => ({ ...prev, symbol: v }))}
                onSubmit={(_code, _name, source, meta) => {
                  if (source === 'autocomplete') setCorpDisplay(meta?.displayLabel ?? '');
                }}
              />
              <div className="grid grid-cols-2 gap-2">
                <HrsInput
                  type="date"
                  clearable={false}
                  className="w-full"
                  value={corpForm.effectiveDate}
                  onChange={(e) => setCorpForm((prev) => ({ ...prev, effectiveDate: e.target.value }))}
                />
                <HrsSelect
                  value={corpForm.actionType}
                  onChange={(v) => setCorpForm((prev) => ({ ...prev, actionType: v as PortfolioCorporateActionType }))}
                  options={[
                    { key: 'cash_dividend', label: '现金分红' },
                    { key: 'split_adjustment', label: '拆并股调整' },
                  ]}
                />
              </div>
              {corpForm.actionType === 'cash_dividend' ? (
                <HrsNumberField
                  className="max-w-none"
                  minValue={0}
                  step={0.000001}
                  placeholder="每股分红"
                  value={corpForm.cashDividendPerShare === '' ? undefined : Number(corpForm.cashDividendPerShare)}
                  onChange={(v) => setCorpForm((prev) => ({ ...prev, cashDividendPerShare: v == null ? '' : String(v), splitRatio: '' }))}
                />
              ) : (
                <HrsNumberField
                  className="max-w-none"
                  minValue={0}
                  step={0.000001}
                  placeholder="拆并股比例"
                  value={corpForm.splitRatio === '' ? undefined : Number(corpForm.splitRatio)}
                  onChange={(v) => setCorpForm((prev) => ({ ...prev, splitRatio: v == null ? '' : String(v), cashDividendPerShare: '' }))}
                />
              )}
            </form>
        </div>
      </Modal.Body>
      <Modal.Footer>
        <HrsButton
          type="button"
          variant="primary"
          className="w-full"
          isDisabled={!writableAccountId}
          onClick={() => {
            if (manualEntryTab === 'trade') void handleTradeSubmit();
            else if (manualEntryTab === 'cash') void handleCashSubmit();
            else void handleCorporateSubmit();
          }}
        >
          {manualEntryTab === 'trade' ? '提交交易' : manualEntryTab === 'cash' ? '提交资金流水' : '提交企业行为'}
        </HrsButton>
      </Modal.Footer>
    </Modal>
  );
};
