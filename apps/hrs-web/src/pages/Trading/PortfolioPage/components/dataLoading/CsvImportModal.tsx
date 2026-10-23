/**
 * 券商 CSV 导入弹窗
 *
 * 封装券商列表加载（含回退）、CSV 文件选择、预演解析与提交写入的本地状态与逻辑。
 * 提交成功后通过 onSuccess 回调通知主页面刷新核心数据（持仓/风险），
 * 校验与写入拦截提示通过 onWriteWarning 回传，接口错误通过 onError 回传。
 * 仅在弹窗首次打开且尚未加载过券商列表时拉取，避免重复请求与重置用户已选券商。
 */

import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { Modal, HrsButton, HrsSelect, HrsCheckbox, InlineAlert } from '@components';
import { formatBrokerLabel, getCsvCommitVariant, getCsvParseVariant } from '@utils/portfolioFormat';
import { portfolioApi } from '../../../../../api/portfolio';
import type {
  PortfolioImportBrokerItem,
  PortfolioImportCommitResponse,
  PortfolioImportParseResponse,
} from '../../../../../types/portfolio';

/** 券商 CSV 导入弹窗属性 */
interface CsvImportModalProps {
  /** 是否打开弹窗 */
  isOpen: boolean;
  /** 关闭弹窗回调 */
  onClose: () => void;
  /** 可写账户 ID，为 undefined 时禁用提交并提示先选择账户 */
  writableAccountId?: number;
  /** 是否阻止写入操作（未选择具体账户时为 true） */
  writeBlocked: boolean;
  /** 提交成功后回调（由主页面刷新持仓/风险等核心数据） */
  onSuccess: () => void;
  /** 统一错误回调 */
  onError: (error: unknown) => void;
  /** 写入拦截 / 校验提示回调 */
  onWriteWarning: (message: string | null) => void;
}

/** 券商列表接口不可用时的内置回退券商 */
const FALLBACK_BROKERS: PortfolioImportBrokerItem[] = [
  { broker: 'huatai', aliases: [], displayName: '华泰' },
  { broker: 'citic', aliases: ['zhongxin'], displayName: '中信' },
  { broker: 'cmb', aliases: ['cmbchina', 'zhaoshang'], displayName: '招商' },
];

/** CSV 文件选择器：无基础组件对应，用 Tailwind 复刻输入框外观（不依赖 global.scss） */
const CSV_FILE_PICKER_CLASS =
  'flex h-11 w-full cursor-pointer items-center justify-center rounded-xl border border-white/15 bg-white/5 px-4 text-sm text-foreground transition-all hover:border-cyan/40 hover:bg-white/10 focus-within:border-cyan/45 focus-within:ring-4 focus-within:ring-cyan/15 disabled:cursor-not-allowed disabled:opacity-60';

/** 写入拦截提示文案 */
const WRITE_BLOCKED_MESSAGE = '请先在上方账户视图选择具体账户，再进行录入或导入提交。';

export const CsvImportModal: React.FC<CsvImportModalProps> = ({
  isOpen,
  onClose,
  writableAccountId,
  writeBlocked,
  onSuccess,
  onError,
  onWriteWarning,
}) => {
  const [brokers, setBrokers] = useState<PortfolioImportBrokerItem[]>([]);
  const [selectedBroker, setSelectedBroker] = useState('huatai');
  const [brokerLoadWarning, setBrokerLoadWarning] = useState<string | null>(null);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  // 仅预演解析，不实际写入
  const [csvDryRun, setCsvDryRun] = useState(true);
  const [csvParsing, setCsvParsing] = useState(false);
  const [csvCommitting, setCsvCommitting] = useState(false);
  const [csvParseResult, setCsvParseResult] = useState<PortfolioImportParseResponse | null>(null);
  const [csvCommitResult, setCsvCommitResult] = useState<PortfolioImportCommitResponse | null>(null);

  /**
   * 加载可用券商列表
   * 接口返回为空或不可用时回退到内置券商列表（华泰/中信/招商），并重置已选券商
   */
  const loadBrokers = useCallback(async () => {
    try {
      const response = await portfolioApi.listImportBrokers();
      const brokerItems = response.brokers || [];
      if (brokerItems.length === 0) {
        setBrokers(FALLBACK_BROKERS);
        setBrokerLoadWarning('券商列表接口返回为空，已回退为内置券商列表（华泰/中信/招商）。');
        setSelectedBroker((prev) => (FALLBACK_BROKERS.some((item) => item.broker === prev) ? prev : FALLBACK_BROKERS[0].broker));
        return;
      }
      setBrokers(brokerItems);
      setBrokerLoadWarning(null);
      setSelectedBroker((prev) => (brokerItems.some((item) => item.broker === prev) ? prev : brokerItems[0].broker));
    } catch {
      setBrokers(FALLBACK_BROKERS);
      setBrokerLoadWarning('券商列表接口不可用，已回退为内置券商列表（华泰/中信/招商）。');
      setSelectedBroker((prev) => (FALLBACK_BROKERS.some((item) => item.broker === prev) ? prev : FALLBACK_BROKERS[0].broker));
    }
  }, []);

  // 仅在弹窗首次打开且尚未加载过券商列表时拉取，避免重复请求与重置已选券商
  useEffect(() => {
    if (isOpen && brokers.length === 0) {
      // 数据加载型副作用，按仓库约定关闭该规则
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void loadBrokers();
    }
  }, [isOpen, brokers.length, loadBrokers]);

  /** 解析 CSV 文件（预演模式）：调用后端解析接口预览文件内容，不实际写入 */
  const handleParseCsv = async () => {
    if (!csvFile) return;
    try {
      setCsvParsing(true);
      const parsed = await portfolioApi.parseCsvImport(selectedBroker, csvFile);
      setCsvParseResult(parsed);
      setCsvCommitResult(null);
    } catch (err) {
      onError(err);
    } finally {
      setCsvParsing(false);
    }
  };

  /** 提交 CSV 导入：按预演开关决定是否实际写入，非预演模式下成功后刷新持仓数据 */
  const handleCommitCsv = async () => {
    if (!csvFile) return;
    if (!writableAccountId) {
      onWriteWarning(WRITE_BLOCKED_MESSAGE);
      return;
    }
    try {
      onWriteWarning(null);
      setCsvCommitting(true);
      const committed = await portfolioApi.commitCsvImport(writableAccountId, selectedBroker, csvFile, csvDryRun);
      setCsvCommitResult(committed);
      if (!csvDryRun) {
        await onSuccess();
      }
    } catch (err) {
      onError(err);
    } finally {
      setCsvCommitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md">
      <Modal.Header>
        <Modal.Heading>券商 CSV 导入</Modal.Heading>
      </Modal.Header>
      <Modal.Body>
        <div className="space-y-2">
          {brokerLoadWarning ? (
            <InlineAlert
              variant="warning"
              className="rounded-lg px-2 py-1 text-xs shadow-none"
              message={brokerLoadWarning}
            />
          ) : null}
          <div className="grid grid-cols-2 gap-2">
            <HrsSelect
              value={selectedBroker}
              onChange={(v) => setSelectedBroker(v as string)}
              options={brokers.length > 0
                ? brokers.map((broker) => ({ key: broker.broker, label: formatBrokerLabel(broker.broker, broker.displayName) }))
                : [{ key: 'huatai', label: 'huatai（华泰）' }]}
            />
            <label className={CSV_FILE_PICKER_CLASS}>
              选择 CSV
              <input type="file" accept=".csv" className="hidden"
                onChange={(e) => setCsvFile(e.target.files && e.target.files[0] ? e.target.files[0] : null)} />
            </label>
          </div>
          <div className="flex items-center gap-2 text-xs text-secondary">
            <HrsCheckbox isSelected={csvDryRun} onChange={(checked) => setCsvDryRun(checked as boolean)} label="仅预演（不写入）" />
          </div>
          <div className="flex gap-2">
            <HrsButton variant="primary" className="flex-1" isDisabled={!csvFile || csvParsing} onClick={() => void handleParseCsv()}>
              {csvParsing ? '解析中...' : '解析文件'}
            </HrsButton>
            <HrsButton variant="primary" className="flex-1"
              isDisabled={!csvFile || writeBlocked || csvCommitting} onClick={() => void handleCommitCsv()}>
              {csvCommitting ? '提交中...' : '提交导入'}
            </HrsButton>
          </div>
          {csvParseResult ? (
            <InlineAlert
              variant={getCsvParseVariant(csvParseResult)}
              title="CSV 解析结果"
              message={`有效 ${csvParseResult.recordCount} 条，跳过 ${csvParseResult.skippedCount} 条，错误 ${csvParseResult.errorCount} 条。`}
              className="rounded-lg px-3 py-2 text-xs shadow-none"
            />
          ) : null}
          {csvCommitResult ? (
            <InlineAlert
              variant={getCsvCommitVariant(csvCommitResult, csvDryRun)}
              title={csvDryRun ? 'CSV 预演结果' : 'CSV 提交结果'}
              message={`${csvDryRun ? '预演检查' : '实际写入'}：写入 ${csvCommitResult.insertedCount} 条，重复 ${csvCommitResult.duplicateCount} 条，失败 ${csvCommitResult.failedCount} 条。`}
              className="rounded-lg px-3 py-2 text-xs shadow-none"
            />
          ) : null}
        </div>
      </Modal.Body>
    </Modal>
  );
};
