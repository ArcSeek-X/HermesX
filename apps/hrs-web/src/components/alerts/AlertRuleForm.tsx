/**
 * AlertRuleForm.tsx
 * 告警规则创建表单组件。
 * 作用：提供一套可视化的表单，让用户按「标的范围（targetScope）→ 告警类型（alertType）→ 参数（parameters）」
 * 的层次配置并新建一条告警规则。表单会根据所选范围与类型动态渲染不同的参数控件（价格突破、涨跌幅、
 * 成交量放大、均线穿越、RSI / MACD / KDJ / CCI 阈值、组合止损、大盘红绿灯等），并在提交前做前端校验，
 * 最终通过 onSubmit 回调把标准化后的 AlertRuleCreateRequest 交给上层处理。
 * 组件本身不负责网络请求，仅做本地状态管理与参数构造。
 */
import type React from 'react';
import { useEffect, useMemo, useState } from 'react';
import { portfolioApi } from '../../api/portfolio';
import type {
  AlertRuleCreateRequest,
  AlertSeverity,
  AlertTargetScope,
  AlertType,
  MarketLightStatus,
  MarketRegion,
  PortfolioStopLossMode,
} from '../../types/alerts';
import type { PortfolioAccountItem } from '../../types/portfolio';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { formatUiText, type UiLanguage } from '../../i18n/uiText';
import {
  ALERT_CHANGE_DIRECTION_OPTIONS,
  ALERT_CROSS_DIRECTION_OPTIONS,
  ALERT_FORM_TEXT,
  ALERT_MARKET_LIGHT_STATUS_OPTIONS,
  ALERT_MARKET_REGION_OPTIONS,
  ALERT_MARKET_TYPE_OPTIONS,
  ALERT_PORTFOLIO_TYPE_OPTIONS,
  ALERT_PRICE_DIRECTION_OPTIONS,
  ALERT_SEVERITY_OPTIONS,
  ALERT_STOP_LOSS_MODE_OPTIONS,
  ALERT_SYMBOL_TYPE_OPTIONS,
  ALERT_TARGET_SCOPE_OPTIONS,
  ALERT_THRESHOLD_DIRECTION_OPTIONS,
} from '../../locales/featureText';
import { validateStockCode } from '../../utils/validation';
import { Button, Card, Checkbox, Input, Select } from '../common';

// 单标的（个股/指数）类告警类型，中文文案直接写死，英文由 featureText 提供
const SYMBOL_ALERT_TYPE_OPTIONS = [
  { value: 'price_cross', label: '价格突破' },
  { value: 'price_change_percent', label: '涨跌幅' },
  { value: 'volume_spike', label: '成交量放大' },
  { value: 'ma_price_cross', label: '价格均线穿越' },
  { value: 'rsi_threshold', label: 'RSI 阈值' },
  { value: 'macd_cross', label: 'MACD 金叉/死叉' },
  { value: 'kdj_cross', label: 'KDJ 金叉/死叉' },
  { value: 'cci_threshold', label: 'CCI 阈值' },
];

// 组合（持仓）类告警类型
const PORTFOLIO_ALERT_TYPE_OPTIONS = [
  { value: 'portfolio_stop_loss', label: '组合止损' },
  { value: 'portfolio_concentration', label: '组合集中度' },
  { value: 'portfolio_drawdown', label: '组合回撤' },
  { value: 'portfolio_price_stale', label: '组合价格状态' },
];

// 大盘类告警类型
const MARKET_ALERT_TYPE_OPTIONS = [
  { value: 'market_light_status', label: '大盘红绿灯状态' },
  { value: 'market_light_score_drop', label: '大盘红绿灯分数下降' },
];

// 标的范围：决定后续展示哪一类告警类型选项
const TARGET_SCOPE_OPTIONS = [
  { value: 'single_symbol', label: '单标的' },
  { value: 'watchlist', label: '自选股' },
  { value: 'portfolio_holdings', label: '持仓标的' },
  { value: 'portfolio_account', label: '持仓账户' },
  { value: 'market', label: '大盘市场' },
];

// 严重级别：提示 / 警告 / 严重
const SEVERITY_OPTIONS = [
  { value: 'info', label: '提示' },
  { value: 'warning', label: '警告' },
  { value: 'critical', label: '严重' },
];

// 价格突破方向：上破 / 下破
const PRICE_DIRECTION_OPTIONS = [
  { value: 'above', label: '上破' },
  { value: 'below', label: '下破' },
];

// 涨跌幅方向：上涨达到 / 下跌达到
const CHANGE_DIRECTION_OPTIONS = [
  { value: 'up', label: '上涨达到' },
  { value: 'down', label: '下跌达到' },
];

// 阈值穿越方向：上穿 / 下穿（MA/RSI/CCI 等通用）
const THRESHOLD_DIRECTION_OPTIONS = [
  { value: 'above', label: '上穿' },
  { value: 'below', label: '下穿' },
];

// 交叉方向：金叉 / 死叉（MACD/KDJ 使用）
const CROSS_DIRECTION_OPTIONS = [
  { value: 'bullish_cross', label: '金叉' },
  { value: 'bearish_cross', label: '死叉' },
];

// 组合止损模式：接近止损 / 已触发止损
const STOP_LOSS_MODE_OPTIONS = [
  { value: 'near', label: '接近止损' },
  { value: 'breach', label: '已触发止损' },
];


// 大盘红绿灯可触发状态：红灯 / 黄灯（多选）
const MARKET_LIGHT_STATUS_OPTIONS: Array<{ value: MarketLightStatus; label: string }> = [
  { value: 'red', label: '红灯' },
  { value: 'yellow', label: '黄灯' },
];

// 指标类告警所需的历史 K 线最大天数限制（用于校验参数不会请求过多历史数据）
const MAX_REQUESTED_DAYS = 365;

interface AlertRuleFormProps {
  // 提交回调：返回 false 表示提交被上层拒绝（例如后端校验失败），此时不清空表单
  onSubmit: (payload: AlertRuleCreateRequest) => Promise<boolean | void> | boolean | void;
  isSubmitting?: boolean;
}

// 判断范围是否属于组合（持仓）类，组合类需要从后端拉取账户列表
function isPortfolioScope(scope: AlertTargetScope): boolean {
  return scope === 'portfolio_holdings' || scope === 'portfolio_account';
}

// 范围切换时的默认告警类型：市场→红绿灯状态，账户→组合止损，其余→价格突破
function defaultAlertTypeForScope(scope: AlertTargetScope): AlertType {
  if (scope === 'market') return 'market_light_status';
  return scope === 'portfolio_account' ? 'portfolio_stop_loss' : 'price_cross';
}

// 根据范围与语言返回告警类型下拉选项；中文用本地常量，英文/i18n 用 featureText
function optionsForScope(scope: AlertTargetScope, language: UiLanguage) {
  if (language === 'zh') {
    if (scope === 'market') return MARKET_ALERT_TYPE_OPTIONS;
    return scope === 'portfolio_account' ? PORTFOLIO_ALERT_TYPE_OPTIONS : SYMBOL_ALERT_TYPE_OPTIONS;
  }
  if (scope === 'market') return ALERT_MARKET_TYPE_OPTIONS[language];
  return scope === 'portfolio_account' ? ALERT_PORTFOLIO_TYPE_OPTIONS[language] : ALERT_SYMBOL_TYPE_OPTIONS[language];
}

export const AlertRuleForm: React.FC<AlertRuleFormProps> = ({ onSubmit, isSubmitting = false }) => {
  const { language } = useUiLanguage();
  const text = ALERT_FORM_TEXT[language];
  const [name, setName] = useState('');
  const [targetScope, setTargetScope] = useState<AlertTargetScope>('single_symbol');
  const [target, setTarget] = useState('');
  const [portfolioTarget, setPortfolioTarget] = useState('all');
  const [marketRegion, setMarketRegion] = useState<MarketRegion>('cn');
  const [accounts, setAccounts] = useState<PortfolioAccountItem[]>([]);
  const [accountsError, setAccountsError] = useState<string | null>(null);
  const [alertType, setAlertType] = useState<AlertType>('price_cross');
  const [severity, setSeverity] = useState<AlertSeverity>('warning');
  const [enabled, setEnabled] = useState(true);
  const [priceDirection, setPriceDirection] = useState<'above' | 'below'>('above');
  const [changeDirection, setChangeDirection] = useState<'up' | 'down'>('up');
  const [thresholdDirection, setThresholdDirection] = useState<'above' | 'below'>('above');
  const [crossDirection, setCrossDirection] = useState<'bullish_cross' | 'bearish_cross'>('bullish_cross');
  const [stopLossMode, setStopLossMode] = useState<PortfolioStopLossMode>('near');
  const [price, setPrice] = useState('');
  const [changePct, setChangePct] = useState('');
  const [multiplier, setMultiplier] = useState('');
  const [window, setWindow] = useState('20');
  const [period, setPeriod] = useState('12');
  const [threshold, setThreshold] = useState('');
  const [fastPeriod, setFastPeriod] = useState('12');
  const [slowPeriod, setSlowPeriod] = useState('26');
  const [signalPeriod, setSignalPeriod] = useState('9');
  const [kPeriod, setKPeriod] = useState('3');
  const [dPeriod, setDPeriod] = useState('3');
  const [marketLightStatuses, setMarketLightStatuses] = useState<MarketLightStatus[]>(['red', 'yellow']);
  const [minDrop, setMinDrop] = useState('10');
  const [formError, setFormError] = useState<string | null>(null);

  // 当选中组合类范围时，异步拉取账户列表用于「账户」下拉；切换范围或文案变化时重新拉取
  useEffect(() => {
    if (!isPortfolioScope(targetScope)) return undefined;
    let cancelled = false;
    void portfolioApi.getAccounts(false)
      .then((response) => {
        if (cancelled) return;
        setAccounts(response.accounts ?? []);
        setAccountsError(null);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setAccounts([]);
        setAccountsError(error instanceof Error ? error.message : text.accountLoadFailed);
      });
    return () => {
      // 卸载或依赖变化时取消，避免竞态写入
      cancelled = true;
    };
  }, [targetScope, text.accountLoadFailed]);

  // 告警类型下拉选项随语言与范围变化重算
  const alertTypeOptions = useMemo(() => optionsForScope(targetScope, language), [language, targetScope]);
  // 账户下拉选项：固定「全部账户」+ 拉取到的各账户
  const portfolioTargetOptions = useMemo(() => [
    { value: 'all', label: text.allAccounts },
    ...accounts.map((account) => ({
      value: String(account.id),
      label: `${account.name} #${account.id}`,
    })),
  ], [accounts, text.allAccounts]);

  // 切换告警类型时，把该类型相关的参数状态重置为默认值
  const resetParameters = (nextType: AlertType) => {
    if (nextType === 'price_cross') {
      setPriceDirection('above');
      setPrice('');
    } else if (nextType === 'price_change_percent') {
      setChangeDirection('up');
      setChangePct('');
    } else if (nextType === 'volume_spike') {
      setMultiplier('');
    } else if (nextType === 'ma_price_cross') {
      setThresholdDirection('above');
      setWindow('20');
    } else if (nextType === 'rsi_threshold') {
      setThresholdDirection('above');
      setPeriod('12');
      setThreshold('');
    } else if (nextType === 'macd_cross') {
      setCrossDirection('bullish_cross');
      setFastPeriod('12');
      setSlowPeriod('26');
      setSignalPeriod('9');
    } else if (nextType === 'kdj_cross') {
      setCrossDirection('bullish_cross');
      setPeriod('9');
      setKPeriod('3');
      setDPeriod('3');
    } else if (nextType === 'cci_threshold') {
      setThresholdDirection('above');
      setPeriod('14');
      setThreshold('');
    } else if (nextType === 'portfolio_stop_loss') {
      setStopLossMode('near');
    } else if (nextType === 'market_light_status') {
      setMarketLightStatuses(['red', 'yellow']);
    } else if (nextType === 'market_light_score_drop') {
      setMinDrop('10');
    }
  };

  const toggleMarketLightStatus = (status: MarketLightStatus) => {
    setMarketLightStatuses((current) => (
      current.includes(status)
        ? current.filter((item) => item !== status)
        : [...current, status]
    ));
  };

  // 解析强制为正的数值（如价格、倍数、涨跌幅），非法则写入表单错误并返回 null
  const parsePositiveNumber = (value: string, label: string): number | null => {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      setFormError(formatUiText(text.positiveNumber, { label }));
      return null;
    }
    return parsed;
  };

  // 解析落在 [min, max] 区间内的整数（如周期、窗口）
  const parseIntegerInRange = (value: string, label: string, min = 2, max = 250): number | null => {
    const parsed = Number(value);
    if (!Number.isInteger(parsed) || parsed < min || parsed > max) {
      setFormError(formatUiText(text.integerRange, { label, min, max }));
      return null;
    }
    return parsed;
  };

  // 解析必填的有限数值，空值或非数字均视为非法
  const parseFiniteNumber = (value: string, label: string): number | null => {
    if (value.trim() === '') {
      setFormError(formatUiText(text.required, { label }));
      return null;
    }
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      setFormError(formatUiText(text.finiteNumber, { label }));
      return null;
    }
    return parsed;
  };

  // RSI 阈值额外约束在 [0,100]
  const parseRsiThreshold = (value: string): number | null => {
    const parsed = parseFiniteNumber(value, text.rsiThreshold);
    if (parsed == null) return null;
    if (parsed < 0 || parsed > 100) {
      setFormError(text.rsiRange);
      return null;
    }
    return parsed;
  };

  // 校验指标类告警所需的历史 K 线数不超过上限（MAX_REQUESTED_DAYS）
  const ensureRequiredBarsWithinLimit = (label: string, requiredBars: number): boolean => {
    if (requiredBars > MAX_REQUESTED_DAYS) {
      setFormError(formatUiText(text.requiredBarsLimit, { label, requiredBars, max: MAX_REQUESTED_DAYS }));
      return false;
    }
    return true;
  };

  // 根据当前告警类型，把各控件值构造成后端所需的 parameters 对象；任一参数非法即返回 null（中止提交）
  const buildParameters = (): AlertRuleCreateRequest['parameters'] | null => {
    if (alertType === 'price_cross') {
      const parsedPrice = parsePositiveNumber(price, text.priceThreshold);
      if (parsedPrice == null) return null;
      return { direction: priceDirection, price: parsedPrice };
    }
    if (alertType === 'price_change_percent') {
      const parsedChangePct = parsePositiveNumber(changePct, text.changePctThreshold);
      if (parsedChangePct == null) return null;
      return { direction: changeDirection, changePct: parsedChangePct };
    }
    if (alertType === 'volume_spike') {
      const parsedMultiplier = parsePositiveNumber(multiplier, text.volumeMultiplier);
      if (parsedMultiplier == null) return null;
      return { multiplier: parsedMultiplier };
    }
    if (alertType === 'ma_price_cross') {
      const parsedWindow = parseIntegerInRange(window, text.maWindow);
      if (parsedWindow == null) return null;
      return { direction: thresholdDirection, window: parsedWindow };
    }
    if (alertType === 'rsi_threshold') {
      const parsedPeriod = parseIntegerInRange(period, text.rsiPeriod);
      const parsedThreshold = parseRsiThreshold(threshold);
      if (parsedPeriod == null || parsedThreshold == null) return null;
      return { direction: thresholdDirection, period: parsedPeriod, threshold: parsedThreshold };
    }
    if (alertType === 'macd_cross') {
      const parsedFast = parseIntegerInRange(fastPeriod, text.fastPeriod);
      const parsedSlow = parseIntegerInRange(slowPeriod, text.slowPeriod);
      const parsedSignal = parseIntegerInRange(signalPeriod, text.signalPeriod);
      if (parsedFast == null || parsedSlow == null || parsedSignal == null) return null;
      if (parsedFast >= parsedSlow) {
        setFormError(text.fastLessThanSlow);
        return null;
      }
      if (!ensureRequiredBarsWithinLimit('MACD', parsedSlow + parsedSignal + 1)) return null;
      return {
        direction: crossDirection,
        fastPeriod: parsedFast,
        slowPeriod: parsedSlow,
        signalPeriod: parsedSignal,
      };
    }
    if (alertType === 'kdj_cross') {
      const parsedPeriod = parseIntegerInRange(period, text.kdjPeriod);
      const parsedK = parseIntegerInRange(kPeriod, text.kPeriod);
      const parsedD = parseIntegerInRange(dPeriod, text.dPeriod);
      if (parsedPeriod == null || parsedK == null || parsedD == null) return null;
      if (!ensureRequiredBarsWithinLimit('KDJ', parsedPeriod + parsedK + parsedD + 1)) return null;
      return { direction: crossDirection, period: parsedPeriod, kPeriod: parsedK, dPeriod: parsedD };
    }
    if (alertType === 'cci_threshold') {
      const parsedPeriod = parseIntegerInRange(period, text.cciPeriod);
      const parsedThreshold = parseFiniteNumber(threshold, text.cciThreshold);
      if (parsedPeriod == null || parsedThreshold == null) return null;
      return { direction: thresholdDirection, period: parsedPeriod, threshold: parsedThreshold };
    }
    if (alertType === 'portfolio_stop_loss') {
      return { mode: stopLossMode };
    }
    if (alertType === 'market_light_status') {
      if (marketLightStatuses.length === 0) {
        setFormError(text.noMarketStatus);
        return null;
      }
      return { statuses: marketLightStatuses };
    }
    if (alertType === 'market_light_score_drop') {
      const parsedMinDrop = parsePositiveNumber(minDrop, text.scoreDropThreshold);
      if (parsedMinDrop == null) return null;
      return { minDrop: parsedMinDrop };
    }
    return {};
  };

  // 范围下拉变化：切换默认类型、重置相关的目标与参数，并清掉表单错误
  const handleScopeChange = (value: string) => {
    const nextScope = value as AlertTargetScope;
    const nextType = defaultAlertTypeForScope(nextScope);
    setTargetScope(nextScope);
    setAlertType(nextType);
    setPortfolioTarget('all');
    setMarketRegion('cn');
    resetParameters(nextType);
    setFormError(null);
  };

  // 提交：先按范围解析并标准化 target；单标的会做股票代码校验并归一化
  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    let resolvedTarget = target.trim();
    if (targetScope === 'single_symbol') {
      const targetValidation = validateStockCode(target);
      if (!targetValidation.valid) {
        setFormError(language === 'en' ? text.invalidStockCode : (targetValidation.message ?? text.invalidStockCode));
        return;
      }
      resolvedTarget = targetValidation.normalized;
    } else if (targetScope === 'watchlist') {
      resolvedTarget = 'default';
    } else if (targetScope === 'market') {
      resolvedTarget = marketRegion;
    } else {
      resolvedTarget = portfolioTarget;
    }

    const parameters = buildParameters();
    if (parameters == null) return;

    setFormError(null);
    // 交还上层执行实际创建；返回 false 时不清空表单，便于用户修改
    const submitted = await onSubmit({
      name: name.trim() || undefined,
      targetScope,
      target: resolvedTarget,
      alertType,
      parameters,
      severity,
      enabled,
    });
    if (submitted === false) return;
    setName('');
    setTarget('');
    setPortfolioTarget('all');
    setMarketRegion('cn');
    setPrice('');
    setChangePct('');
    setMultiplier('');
    setWindow('20');
    setPeriod('12');
    setThreshold('');
    setFastPeriod('12');
    setSlowPeriod('26');
    setSignalPeriod('9');
    setKPeriod('3');
    setDPeriod('3');
    setMarketLightStatuses(['red', 'yellow']);
    setMinDrop('10');
    resetParameters(alertType);
    setEnabled(true);
  };

  // 根据范围渲染「目标」控件：单标的=代码输入框，自选股=只读 default，大盘=区域下拉，组合=账户下拉
  const renderTargetControl = () => {
    if (targetScope === 'single_symbol') {
      return (
        <Input
          label={text.targetCode}
          value={target}
          onChange={(event) => setTarget(event.target.value)}
          placeholder="600519 / AAPL / hk00700"
          disabled={isSubmitting}
        />
      );
    }
    if (targetScope === 'watchlist') {
      return (
        <Input
          label={text.target}
          value="default"
          onChange={() => undefined}
          disabled
        />
      );
    }
    if (targetScope === 'market') {
      return (
        <Select
          label={text.marketRegion}
          value={marketRegion}
          options={ALERT_MARKET_REGION_OPTIONS[language]}
          disabled={isSubmitting}
          onChange={(value) => setMarketRegion(value as MarketRegion)}
        />
      );
    }
    return (
      <div className="space-y-2">
        <Select
          label={text.account}
          value={portfolioTarget}
          options={portfolioTargetOptions}
          disabled={isSubmitting}
          onChange={setPortfolioTarget}
        />
        {accountsError ? <p role="alert" className="text-xs text-warning">{accountsError}</p> : null}
      </div>
    );
  };

  return (
    // 外层卡片容器，表单整体禁用在提交中状态
    <Card title={text.cardTitle} subtitle={text.cardSubtitle} variant="bordered" padding="md">
      <form className="space-y-4" noValidate onSubmit={(event) => void handleSubmit(event)}>
        <div className="grid gap-4 md:grid-cols-2">
          <Input
            label={text.ruleName}
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder={text.ruleNamePlaceholder}
            disabled={isSubmitting}
          />
          <Select
            label={text.targetScope}
            value={targetScope}
            options={language === 'zh' ? TARGET_SCOPE_OPTIONS : ALERT_TARGET_SCOPE_OPTIONS[language]}
            disabled={isSubmitting}
            onChange={handleScopeChange}
          />
          {renderTargetControl()}
          <Select
            label={text.ruleType}
            value={alertType}
            options={alertTypeOptions}
            disabled={isSubmitting}
            onChange={(value) => {
              const nextType = value as AlertType;
              setAlertType(nextType);
              resetParameters(nextType);
            }}
          />
          <Select
            label={text.severity}
            value={severity}
            options={language === 'zh' ? SEVERITY_OPTIONS : ALERT_SEVERITY_OPTIONS[language]}
            disabled={isSubmitting}
            onChange={(value) => setSeverity(value as AlertSeverity)}
          />
        </div>

        {alertType === 'price_cross' ? (
          <div className="grid gap-4 md:grid-cols-2">
            <Select
              label={text.direction}
              value={priceDirection}
              options={language === 'zh' ? PRICE_DIRECTION_OPTIONS : ALERT_PRICE_DIRECTION_OPTIONS[language]}
              disabled={isSubmitting}
              onChange={(value) => setPriceDirection(value as 'above' | 'below')}
            />
            <Input
              label={text.priceThreshold}
              type="number"
              min="0"
              step="0.0001"
              value={price}
              onChange={(event) => setPrice(event.target.value)}
              disabled={isSubmitting}
            />
          </div>
        ) : null}

        {alertType === 'price_change_percent' ? (
          <div className="grid gap-4 md:grid-cols-2">
            <Select
              label={text.direction}
              value={changeDirection}
              options={language === 'zh' ? CHANGE_DIRECTION_OPTIONS : ALERT_CHANGE_DIRECTION_OPTIONS[language]}
              disabled={isSubmitting}
              onChange={(value) => setChangeDirection(value as 'up' | 'down')}
            />
            <Input
              label={text.changePctThreshold}
              type="number"
              min="0"
              step="0.01"
              value={changePct}
              onChange={(event) => setChangePct(event.target.value)}
              disabled={isSubmitting}
            />
          </div>
        ) : null}

        {alertType === 'volume_spike' ? (
          <Input
            label={text.volumeMultiplier}
            type="number"
            min="0"
            step="0.01"
            value={multiplier}
            onChange={(event) => setMultiplier(event.target.value)}
            disabled={isSubmitting}
          />
        ) : null}

        {alertType === 'ma_price_cross' ? (
          <div className="grid gap-4 md:grid-cols-2">
            <Select
              label={text.maDirection}
              value={thresholdDirection}
              options={language === 'zh' ? THRESHOLD_DIRECTION_OPTIONS : ALERT_THRESHOLD_DIRECTION_OPTIONS[language]}
              disabled={isSubmitting}
              onChange={(value) => setThresholdDirection(value as 'above' | 'below')}
            />
            <Input
              label={text.maWindow}
              type="number"
              min="2"
              max="250"
              step="1"
              value={window}
              onChange={(event) => setWindow(event.target.value)}
              disabled={isSubmitting}
            />
          </div>
        ) : null}

        {alertType === 'rsi_threshold' ? (
          <div className="grid gap-4 md:grid-cols-3">
            <Select
              label={text.thresholdDirection}
              value={thresholdDirection}
              options={language === 'zh' ? THRESHOLD_DIRECTION_OPTIONS : ALERT_THRESHOLD_DIRECTION_OPTIONS[language]}
              disabled={isSubmitting}
              onChange={(value) => setThresholdDirection(value as 'above' | 'below')}
            />
            <Input
              label={text.rsiPeriod}
              type="number"
              min="2"
              max="250"
              step="1"
              value={period}
              onChange={(event) => setPeriod(event.target.value)}
              disabled={isSubmitting}
            />
            <Input
              label={text.rsiThreshold}
              type="number"
              min="0"
              max="100"
              step="0.01"
              value={threshold}
              onChange={(event) => setThreshold(event.target.value)}
              disabled={isSubmitting}
            />
          </div>
        ) : null}

        {alertType === 'macd_cross' ? (
          <div className="grid gap-4 md:grid-cols-4">
            <Select
              label={text.crossDirection}
              value={crossDirection}
              options={language === 'zh' ? CROSS_DIRECTION_OPTIONS : ALERT_CROSS_DIRECTION_OPTIONS[language]}
              disabled={isSubmitting}
              onChange={(value) => setCrossDirection(value as 'bullish_cross' | 'bearish_cross')}
            />
            <Input
              label={text.fastPeriod}
              type="number"
              min="2"
              max="250"
              step="1"
              value={fastPeriod}
              onChange={(event) => setFastPeriod(event.target.value)}
              disabled={isSubmitting}
            />
            <Input
              label={text.slowPeriod}
              type="number"
              min="2"
              max="250"
              step="1"
              value={slowPeriod}
              onChange={(event) => setSlowPeriod(event.target.value)}
              disabled={isSubmitting}
            />
            <Input
              label={text.signalPeriod}
              type="number"
              min="2"
              max="250"
              step="1"
              value={signalPeriod}
              onChange={(event) => setSignalPeriod(event.target.value)}
              disabled={isSubmitting}
            />
          </div>
        ) : null}

        {alertType === 'kdj_cross' ? (
          <div className="grid gap-4 md:grid-cols-4">
            <Select
              label={text.crossDirection}
              value={crossDirection}
              options={language === 'zh' ? CROSS_DIRECTION_OPTIONS : ALERT_CROSS_DIRECTION_OPTIONS[language]}
              disabled={isSubmitting}
              onChange={(value) => setCrossDirection(value as 'bullish_cross' | 'bearish_cross')}
            />
            <Input
              label={text.kdjPeriod}
              type="number"
              min="2"
              max="250"
              step="1"
              value={period}
              onChange={(event) => setPeriod(event.target.value)}
              disabled={isSubmitting}
            />
            <Input
              label={text.kPeriod}
              type="number"
              min="2"
              max="250"
              step="1"
              value={kPeriod}
              onChange={(event) => setKPeriod(event.target.value)}
              disabled={isSubmitting}
            />
            <Input
              label={text.dPeriod}
              type="number"
              min="2"
              max="250"
              step="1"
              value={dPeriod}
              onChange={(event) => setDPeriod(event.target.value)}
              disabled={isSubmitting}
            />
          </div>
        ) : null}

        {alertType === 'cci_threshold' ? (
          <div className="grid gap-4 md:grid-cols-3">
            <Select
              label={text.thresholdDirection}
              value={thresholdDirection}
              options={language === 'zh' ? THRESHOLD_DIRECTION_OPTIONS : ALERT_THRESHOLD_DIRECTION_OPTIONS[language]}
              disabled={isSubmitting}
              onChange={(value) => setThresholdDirection(value as 'above' | 'below')}
            />
            <Input
              label={text.cciPeriod}
              type="number"
              min="2"
              max="250"
              step="1"
              value={period}
              onChange={(event) => setPeriod(event.target.value)}
              disabled={isSubmitting}
            />
            <Input
              label={text.cciThreshold}
              type="number"
              step="0.01"
              value={threshold}
              onChange={(event) => setThreshold(event.target.value)}
              disabled={isSubmitting}
            />
          </div>
        ) : null}

        {alertType === 'portfolio_stop_loss' ? (
          <Select
            label={text.stopLossMode}
            value={stopLossMode}
            options={language === 'zh' ? STOP_LOSS_MODE_OPTIONS : ALERT_STOP_LOSS_MODE_OPTIONS[language]}
            disabled={isSubmitting}
            onChange={(value) => setStopLossMode(value as PortfolioStopLossMode)}
          />
        ) : null}

        {alertType === 'market_light_status' ? (
          <div className="space-y-2">
            <div className="text-sm font-medium text-foreground">{text.triggerStatus}</div>
            <div className="grid gap-3 sm:grid-cols-2">
              {(language === 'zh' ? MARKET_LIGHT_STATUS_OPTIONS : ALERT_MARKET_LIGHT_STATUS_OPTIONS[language]).map((option) => (
                <Checkbox
                  key={option.value}
                  label={option.label}
                  checked={marketLightStatuses.includes(option.value)}
                  disabled={isSubmitting}
                  onChange={() => toggleMarketLightStatus(option.value)}
                />
              ))}
            </div>
          </div>
        ) : null}

        {alertType === 'market_light_score_drop' ? (
          <Input
            label={text.scoreDropThreshold}
            type="number"
            min="0"
            max="100"
            step="1"
            value={minDrop}
            onChange={(event) => setMinDrop(event.target.value)}
            disabled={isSubmitting}
          />
        ) : null}

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Checkbox
            label={text.enableAfterCreate}
            checked={enabled}
            onChange={(event) => setEnabled(event.target.checked)}
            disabled={isSubmitting}
          />
          <Button type="submit" isLoading={isSubmitting} loadingText={text.creating}>
            {text.create}
          </Button>
        </div>
        {formError ? <p role="alert" className="text-sm text-danger">{formError}</p> : null}
      </form>
    </Card>
  );
};
