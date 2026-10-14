/**
 * @file Discover/ScannerPage/components/ScannerResultRow.tsx
 * @description 技术信号扫描结果列表中的单行组件（从 ScannerPage 抽取，自包含）。
 *   结构：左侧（名称 / 代码）→ 中部（命中信号标签 + 扫描时间）→ 右侧「加自选」按钮。
 *   整行点击跳转个股 K 线页；「加自选」按钮经包裹层阻止冒泡，不触发跳转。
 *   文件比页面深一级，相对导入需 ../../../../ 回到 src/。
 */

import { useNavigate } from 'react-router-dom';
import { Check, Plus } from 'lucide-react';
import { AnimCard, Chip, HrsButton } from '@components';
import { setStorageItem } from '../../../../utils/storage';
import { useUiLanguage } from '../../../../contexts/UiLanguageContext';
import { pureStockCode, type ScannerResultRow as ScannerResultRowData, type ScannerSignalKey } from '../../../../api/scanner';

/** 信号键 -> i18n key（字面量常量，保证 t() 的类型安全） */
const SIGNAL_LABEL_KEYS = {
  ma_golden: 'scanner.signal.ma_golden',
  ma_death: 'scanner.signal.ma_death',
  macd_golden: 'scanner.signal.macd_golden',
  macd_death: 'scanner.signal.macd_death',
  rsi_oversold: 'scanner.signal.rsi_oversold',
  rsi_overbought: 'scanner.signal.rsi_overbought',
  boll_upper: 'scanner.signal.boll_upper',
  boll_lower: 'scanner.signal.boll_lower',
} as const;

/** 结果行 Props */
export type ScannerResultRowProps = {
  /** 单条命中结果，必填 */
  row: ScannerResultRowData;
  /** 列表序号，用于入场动画错位延迟 */
  ordinal: number;
  /** 是否已在默认自选分组中（控制「加自选」按钮态） */
  inWatchlist: boolean;
  /** 是否存在可写入的自选分组；无分组时隐藏「加自选」按钮 */
  canAddWatchlist: boolean;
  /** 点击「加自选」回调，由页面层写入默认分组 */
  onAddToWatchlist: (row: ScannerResultRowData) => void;
};

/** 规范展示代码：'603019' -> '603019.SH' / 北交 -> '.BJ'（与 StockSearch 契约一致）。 */
function buildDisplayCode(code: string): string {
  const pure = code.split('.')[0].trim();
  if (code.includes('.')) return code;
  if (pure.startsWith('6')) return `${pure}.SH`;
  if (/^[489]/.test(pure)) return `${pure}.BJ`;
  return `${pure}.SZ`;
}

/**
 * 扫描结果行：结果列表中的单条展示单元（视觉对齐参考项目 Scanner 的 resultItem）。
 * 整行点击跳转个股 K 线页；「加自选」按钮经包裹层阻止冒泡，不触发跳转。
 */
function ScannerResultRow({
  row,
  ordinal,
  inWatchlist,
  canAddWatchlist,
  onAddToWatchlist,
}: ScannerResultRowProps) {
  const { t } = useUiLanguage();
  const navigate = useNavigate();

  // 点击行跳转个股 K 线页：写入 sessionStorage 共享键（与 ShellHeader/StockKLinePage 同键），
  // K 线页 useEffect([stockCode]) 监听到代码后自动加载；展示标签写入 displayValue 供页内搜索框初始化显示。
  const openInKline = () => {
    const pureCode = pureStockCode(row.code);
    setStorageItem('kline.stockCode', pureCode, 'session');
    try {
      sessionStorage.setItem(
        'hrs-state-kline.displayValue',
        JSON.stringify(`${row.name}（${buildDisplayCode(row.code)}）`),
      );
    } catch {
      /* ignore */
    }
    navigate('/stock/kline');
  };

  return (
    <AnimCard
      ordinal={ordinal}
      onClick={openInKline}
      tooltip={t('scanner.result.openKline')}
      className="flex items-center gap-3 p-3 transition-colors hover:border-[hsl(var(--primary)/0.5)]"
    >
      {/* 名称 + 代码 */}
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-semibold leading-tight">{row.name || row.code}</div>
        <div className="mt-0.5 text-xs text-muted-text">{buildDisplayCode(row.code)}</div>
      </div>

      {/* 命中信号标签 + 扫描时间 */}
      <div className="flex shrink-0 flex-wrap items-center justify-end gap-1">
        {row.signals.map((signal) => (
          <Chip key={signal} variant="soft" size="sm">
            {t(SIGNAL_LABEL_KEYS[signal as ScannerSignalKey] ?? 'scanner.result.title')}
          </Chip>
        ))}
        <span className="ml-1 text-[11px] text-muted-text">{row.scannedAt}</span>
      </div>

      {/* 加自选：包裹层阻止冒泡，避免点击触发整行跳转（HrsButton 的 onClick 桥接 onPress，不可在其中 stopPropagation） */}
      {canAddWatchlist && (
        <div className="shrink-0" onClick={(e) => e.stopPropagation()}>
          <HrsButton
            variant={inWatchlist ? 'success-soft' : 'outline'}
            size="xs"
            className={inWatchlist ? undefined : 'bg-black/[0.03] dark:bg-white/[0.04]'}
            isDisabled={inWatchlist}
            onClick={() => onAddToWatchlist(row)}
          >
            {inWatchlist ? <Check className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
            {inWatchlist ? t('scanner.result.inWatchlist') : t('scanner.result.addWatchlist')}
          </HrsButton>
        </div>
      )}
    </AnimCard>
  );
}

export default ScannerResultRow;
