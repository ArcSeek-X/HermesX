/**
 * @file Discover/ScannerPage/ScannerPage.tsx
 * @title 信号扫描（Scanner）
 * @author AI 复刻自 stock-dashboard 的 Scanner 页面
 *
 * 技术信号扫描页：左栏配置（股票池来源 + 信号模板 + 开始/取消），右栏增量结果。
 * 后端为异步任务（/api/v1/scanner/*），轮询即返回已命中结果，离开页面自动取消。
 * 组件全部复用本仓库 @components，不新增组件；信号判定口径对齐参考项目。
 */

import type React from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Play, ScanLine, SquareX } from 'lucide-react';
import { AnimCard, HrsButton, TabNav } from '@components';
import { EmptyState, PageHeader } from '@components/page-layout';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import type { UiTextKey } from '../../../i18n/uiText';
import {
  pureStockCode,
  scannerApi,
  type ScannerPoolSource,
  type ScannerRankingField,
  type ScannerResultRow as ScannerResultRowData,
  type ScannerSignalKey,
  type ScannerWatchlistItem,
} from '../../../api/scanner';
import { toApiErrorMessage } from '../../../api/error';
import {
  createWatchlistItem,
  getAllWatchlistItems,
  getWatchlistGroups,
} from '../../../api/watchlist';
import ScannerResultRow from './components/ScannerResultRow';

/** 页面阶段：idle 配置态 / running 任务轮询中 / finished 任务结束（结果保留） */
type ScanPhase = 'idle' | 'running' | 'finished';

/** 股票池来源选项（后端 /options 为准，此处为接口未就绪时的兜底） */
const POOL_SOURCE_OPTIONS: ScannerPoolSource[] = ['watchlist', 'ranking', 'limit_up'];
/** 榜单排序字段 */
const RANKING_FIELD_OPTIONS: ScannerRankingField[] = ['amount', 'change_percent', 'turnover_rate'];
/** TopN 档位 */
const TOP_N_CHOICES = [20, 50, 100];

/** 信号模板：key 与后端一致，labelKey / descKey 走 i18n */
const SIGNAL_TEMPLATES: ReadonlyArray<{
  key: ScannerSignalKey;
  labelKey: UiTextKey;
  descKey: UiTextKey;
}> = [
  { key: 'ma_golden', labelKey: 'scanner.signal.ma_golden', descKey: 'scanner.signal.ma_golden_desc' },
  { key: 'ma_death', labelKey: 'scanner.signal.ma_death', descKey: 'scanner.signal.ma_death_desc' },
  { key: 'macd_golden', labelKey: 'scanner.signal.macd_golden', descKey: 'scanner.signal.macd_golden_desc' },
  { key: 'macd_death', labelKey: 'scanner.signal.macd_death', descKey: 'scanner.signal.macd_death_desc' },
  { key: 'rsi_oversold', labelKey: 'scanner.signal.rsi_oversold', descKey: 'scanner.signal.rsi_oversold_desc' },
  { key: 'rsi_overbought', labelKey: 'scanner.signal.rsi_overbought', descKey: 'scanner.signal.rsi_overbought_desc' },
  { key: 'boll_upper', labelKey: 'scanner.signal.boll_upper', descKey: 'scanner.signal.boll_upper_desc' },
  { key: 'boll_lower', labelKey: 'scanner.signal.boll_lower', descKey: 'scanner.signal.boll_lower_desc' },
];

/** 股票池来源 -> i18n 标签 */
const POOL_SOURCE_LABELS: Record<ScannerPoolSource, UiTextKey> = {
  watchlist: 'scanner.pool.watchlist',
  ranking: 'scanner.pool.ranking',
  limit_up: 'scanner.pool.limitUp',
};
/** 榜单排序字段 -> i18n 标签 */
const RANKING_FIELD_LABELS: Record<ScannerRankingField, UiTextKey> = {
  amount: 'scanner.rankingField.amount',
  change_percent: 'scanner.rankingField.changePercent',
  turnover_rate: 'scanner.rankingField.turnoverRate',
};

/** TopN 档位选择：榜单与涨停池共用，避免重复渲染 */
function TopNSelector({
  value,
  onSelect,
}: {
  value: number;
  onSelect: (n: number) => void;
}) {
  const { t } = useUiLanguage();
  return (
    <div className="flex items-center gap-2">
      {TOP_N_CHOICES.map((choice) => (
        <HrsButton
          key={choice}
          size="xs"
          variant={value === choice ? 'primary-soft' : 'outline'}
          className={value === choice ? undefined : 'bg-black/[0.04] dark:bg-white/[0.05]'}
          onClick={() => onSelect(choice)}
        >
          {t('scanner.topN', { n: choice })}
        </HrsButton>
      ))}
    </div>
  );
}

/** 信号模板网格：双行结构（标签 + 说明），点击切换选中 */
function SignalTemplateGrid({
  selectedKeys,
  onToggle,
}: {
  selectedKeys: Set<ScannerSignalKey>;
  onToggle: (key: ScannerSignalKey) => void;
}) {
  const { t } = useUiLanguage();
  return (
    <div className="grid grid-cols-2 gap-2">
      {SIGNAL_TEMPLATES.map((signal) => {
        const active = selectedKeys.has(signal.key);
        return (
          <button
            key={signal.key}
            type="button"
            onClick={() => onToggle(signal.key)}
            className={`flex flex-col items-start gap-0.5 rounded-lg border px-3 py-2 text-left transition-colors ${
              active
                ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.08)]'
                : 'border-subtle bg-black/[0.03] hover:border-[hsl(var(--primary)/0.5)] dark:bg-white/[0.04]'
            }`}
          >
            <span className={`text-xs font-medium ${active ? 'text-[hsl(var(--primary))]' : 'text-foreground'}`}>
              {t(signal.labelKey)}
            </span>
            <span className="text-[11px] leading-tight text-muted-text">{t(signal.descKey)}</span>
          </button>
        );
      })}
    </div>
  );
}

const ScannerPage: React.FC = () => {
  const { t } = useUiLanguage();

  // ----------------------------- 扫描配置 -----------------------------
  const [poolSource, setPoolSource] = useState<ScannerPoolSource>('watchlist');
  const [rankingField, setRankingField] = useState<ScannerRankingField>('amount');
  const [topN, setTopN] = useState<number>(20);
  const [selectedSignals, setSelectedSignals] = useState<ScannerSignalKey[]>(['ma_golden']);

  // ----------------------------- 任务与结果 -----------------------------
  const [phase, setPhase] = useState<ScanPhase>('idle');
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const [poolCount, setPoolCount] = useState(0);
  const [scanned, setScanned] = useState(0);
  const [results, setResults] = useState<ScannerResultRowData[]>([]);
  const [error, setError] = useState<string | null>(null);

  // ----------------------------- 自选股 -----------------------------
  /** 参与扫描的个股：全部自选分组去重后的股票池（对齐参考项目的「全部自选分组」语义） */
  const [watchlistStocks, setWatchlistStocks] = useState<ScannerWatchlistItem[]>([]);
  /** 全部分组去重后的代码集合，用于结果行展示「已自选」 */
  const [watchlistCodes, setWatchlistCodes] = useState<Set<string>>(new Set());
  /** 默认写入分组（按 sortOrder 取首个），无分组时隐藏加自选按钮 */
  const [defaultWatchlistGroupId, setDefaultWatchlistGroupId] = useState<number | null>(null);

  // 卸载时取消仍在运行的扫描：taskId / phase 用 ref 读取，避免依赖变化触发误取消
  const taskIdRef = useRef<string | null>(null);
  const phaseRef = useRef<ScanPhase>('idle');
  useEffect(() => {
    taskIdRef.current = taskId;
    phaseRef.current = phase;
  }, [taskId, phase]);

  // 扫描选项契约：加载失败时沿用本地兜底常量，不阻断页面使用
  useEffect(() => {
    let active = true;
    const loadScannerOptions = async () => {
      try {
        const options = await scannerApi.getOptions();
        if (!active) return;
        if (options.topNOptions?.length) setTopN(options.defaults?.topN ?? options.topNOptions[0]);
      } catch {
        /* 选项加载失败不阻断页面：沿用本地兜底常量 */
      }
    };
    void loadScannerOptions();
    return () => {
      active = false;
    };
  }, []);

  // 加载全部自选分组的个股，去重后作为「自选股」股票池；取首个分组作为加自选目标
  useEffect(() => {
    let active = true;
    const loadWatchlistStocks = async () => {
      try {
        const groups = await getWatchlistGroups();
        if (!active) return;
        if (groups.length === 0) {
          setDefaultWatchlistGroupId(null);
          setWatchlistStocks([]);
          setWatchlistCodes(new Set());
          return;
        }
        const sortedGroups = [...groups].sort((a, b) => a.sortOrder - b.sortOrder || a.id - b.id);
        const perGroup = await Promise.all(
          sortedGroups.map((group) => getAllWatchlistItems(group.id).catch(() => [])),
        );
        if (!active) return;
        const byCode = new Map<string, ScannerWatchlistItem>();
        for (const items of perGroup) {
          for (const item of items) {
            const code = pureStockCode(item.stockCode);
            if (!code || byCode.has(code)) continue;
            byCode.set(code, { code, name: item.stockName ?? '' });
          }
        }
        const merged = [...byCode.values()];
        setDefaultWatchlistGroupId(sortedGroups[0].id);
        setWatchlistStocks(merged);
        setWatchlistCodes(new Set(merged.map((stock) => stock.code)));
      } catch {
        if (!active) return;
        setDefaultWatchlistGroupId(null);
        setWatchlistStocks([]);
        setWatchlistCodes(new Set());
      }
    };
    void loadWatchlistStocks();
    return () => {
      active = false;
    };
  }, []);

  // 轮询任务进度与增量结果（递归 setTimeout，绕过 GET 缓存）
  useEffect(() => {
    if (!taskId || phase !== 'running') return undefined;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const pollTask = async () => {
      try {
        const task = await scannerApi.getTask(taskId);
        if (!active) return;
        setProgress(task.progress ?? 0);
        setStatusMessage(task.message ?? '');
        setPoolCount(task.poolCount ?? 0);
        setScanned(task.scanned ?? 0);
        setResults(task.results ?? []);
        if (task.status === 'completed') {
          setPhase('finished');
        } else if (task.status === 'failed') {
          setError(`${t('scanner.error.failed')}${task.error ? `：${task.error}` : ''}`);
          setPhase('finished');
        } else {
          timer = setTimeout(pollTask, 2000);
        }
      } catch {
        if (!active) return;
        timer = setTimeout(pollTask, 2000);
      }
    };
    void pollTask();
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [taskId, phase, t]);

  // 离开页面即中止扫描：扫描池可达上百只股票，不中止会在后台跑完
  useEffect(
    () => () => {
      if (phaseRef.current === 'running' && taskIdRef.current) {
        void scannerApi.cancel(taskIdRef.current).catch(() => undefined);
      }
    },
    [],
  );

  /** 切换信号模板选中态 */
  const toggleSignalKey = useCallback((key: ScannerSignalKey) => {
    setSelectedSignals((prev) =>
      prev.includes(key) ? prev.filter((item) => item !== key) : [...prev, key],
    );
  }, []);

  /** 提交扫描任务 */
  const startScan = useCallback(async () => {
    setError(null);
    if (selectedSignals.length === 0) {
      setError(t('scanner.signals.empty'));
      return;
    }
    if (poolSource === 'watchlist' && watchlistStocks.length === 0) {
      setError(t('scanner.pool.emptyWatchlist'));
      return;
    }
    try {
      const accepted = await scannerApi.start({
        poolSource,
        rankingField,
        topN,
        signals: selectedSignals,
        watchlist: poolSource === 'watchlist' ? watchlistStocks : [],
      });
      setTaskId(accepted.taskId);
      setResults([]);
      setProgress(0);
      setPoolCount(0);
      setScanned(0);
      setStatusMessage(t('scanner.progress.preparing'));
      setPhase('running');
    } catch (err) {
      setError(toApiErrorMessage(err));
    }
  }, [poolSource, rankingField, topN, selectedSignals, watchlistStocks, t]);

  /** 取消扫描：后端协作式停止，已命中结果保留并继续轮询至任务结束 */
  const cancelScan = useCallback(async () => {
    if (!taskId) return;
    try {
      await scannerApi.cancel(taskId);
    } catch (err) {
      setError(toApiErrorMessage(err));
    }
  }, [taskId]);

  /** 加自选：写入默认分组；后端 409（分组内已存在）按成功处理，同步「已自选」状态 */
  const addToWatchlist = useCallback(
    async (row: ScannerResultRowData) => {
      if (defaultWatchlistGroupId === null) return;
      const code = pureStockCode(row.code);
      try {
        await createWatchlistItem(defaultWatchlistGroupId, { stockCode: code, stockName: row.name });
        setWatchlistCodes((prev) => new Set(prev).add(code));
      } catch (err) {
        const status = (err as { response?: { status?: number } })?.response?.status;
        if (status === 409) {
          setWatchlistCodes((prev) => new Set(prev).add(code));
          return;
        }
        setError(toApiErrorMessage(err));
      }
    },
    [defaultWatchlistGroupId],
  );

  const poolSourceTabs = useMemo(
    () => POOL_SOURCE_OPTIONS.map((source) => ({ value: source, label: t(POOL_SOURCE_LABELS[source]) })),
    [t],
  );

  const rankingFieldTabs = useMemo(
    () => RANKING_FIELD_OPTIONS.map((field) => ({ value: field, label: t(RANKING_FIELD_LABELS[field]) })),
    [t],
  );

  /** 运行中按钮文案：优先后端阶段文案（如「技术信号扫描 30/100」） */
  const runningStatusText = statusMessage || t('scanner.progress.preparing');

  return (
    <div className="mx-auto w-full space-y-3">
      <PageHeader title={t('layout.nav.scanner.title')} description={t('layout.nav.scanner.description')} />

      {error && (
        <div className="rounded-lg border border-[hsl(var(--danger)/0.4)] bg-[hsl(var(--danger)/0.08)] px-4 py-2 text-sm text-[hsl(var(--danger))]">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
        {/* ----------------------------- 左栏：扫描配置 ----------------------------- */}
        <div className="space-y-3">
          <AnimCard className="p-4">
            <div className="space-y-3">
              <div className="text-sm font-semibold">{t('scanner.pool.title')}</div>

              <TabNav
                items={poolSourceTabs}
                value={poolSource}
                onChange={(value) => setPoolSource(value as ScannerPoolSource)}
                size="sm"
                ariaLabel={t('scanner.pool.title')}
              />

              {poolSource === 'watchlist' && (
                <p className="text-xs text-muted-text">
                  {watchlistStocks.length > 0
                    ? `${t('scanner.pool.watchlistHint')} · ${t('scanner.pool.count', { n: watchlistStocks.length })}`
                    : t('scanner.pool.watchlistHint')}
                </p>
              )}

              {poolSource === 'ranking' && (
                <div className="space-y-2">
                  <TabNav
                    items={rankingFieldTabs}
                    value={rankingField}
                    onChange={(value) => setRankingField(value as ScannerRankingField)}
                    size="xs"
                    variant="secondary"
                    ariaLabel={t('scanner.rankingField.label')}
                  />
                  <TopNSelector value={topN} onSelect={setTopN} />
                  <p className="text-xs text-muted-text">{t('scanner.pool.rankingHint')}</p>
                </div>
              )}

              {poolSource === 'limit_up' && (
                <div className="space-y-2">
                  <TopNSelector value={topN} onSelect={setTopN} />
                  <p className="text-xs text-muted-text">{t('scanner.pool.limitUpHint')}</p>
                </div>
              )}
            </div>
          </AnimCard>

          <AnimCard className="p-4">
            <div className="space-y-3">
              <div className="text-sm font-semibold">{t('scanner.signals.title')}</div>
              <SignalTemplateGrid selectedKeys={new Set(selectedSignals)} onToggle={toggleSignalKey} />
            </div>
          </AnimCard>

          <div className="space-y-2">
            {phase === 'running' ? (
              <>
                <HrsButton
                  variant="primary"
                  size="lg"
                  className="w-full"
                  isLoading
                  loadingText={runningStatusText}
                  isDisabled
                >
                  {runningStatusText}
                </HrsButton>
                <HrsButton
                  variant="danger-soft"
                  size="lg"
                  className="w-full"
                  onClick={cancelScan}
                >
                  <SquareX className="h-4 w-4" />
                  {t('scanner.cancel')}
                </HrsButton>
              </>
            ) : (
              <HrsButton
                variant="primary"
                size="lg"
                className="w-full"
                onClick={startScan}
                isDisabled={selectedSignals.length === 0}
              >
                <Play className="h-4 w-4" />
                {phase === 'finished' ? t('scanner.restart') : t('scanner.start')}
              </HrsButton>
            )}
          </div>
        </div>

        {/* ----------------------------- 右栏：扫描结果 ----------------------------- */}
        <AnimCard className="flex min-h-[320px] flex-col p-4">
          <div className="flex flex-1 flex-col space-y-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-semibold">{t('scanner.result.title')}</span>
              <span className="text-xs text-secondary-text">
                {t('scanner.result.count', { n: results.length })}
                {scanned > 0 && ` · ${scanned}/${poolCount}`}
                {phase === 'running' && ` · ${progress}%`}
              </span>
            </div>

            {results.length === 0 ? (
              <div className="flex flex-1 items-center justify-center">
                <EmptyState
                  title={phase === 'running' ? runningStatusText : t('scanner.result.empty')}
                  description={phase === 'running' ? undefined : t('scanner.result.emptyDesc')}
                  icon={<ScanLine className="h-10 w-10" />}
                />
              </div>
            ) : (
              <div className="space-y-2">
                {results.map((row, index) => (
                  <ScannerResultRow
                    key={`${row.code}-${row.signals.join('-')}`}
                    row={row}
                    ordinal={index}
                    inWatchlist={watchlistCodes.has(pureStockCode(row.code))}
                    canAddWatchlist={defaultWatchlistGroupId !== null}
                    onAddToWatchlist={addToWatchlist}
                  />
                ))}
              </div>
            )}
          </div>
        </AnimCard>
      </div>
    </div>
  );
};

export default ScannerPage;
