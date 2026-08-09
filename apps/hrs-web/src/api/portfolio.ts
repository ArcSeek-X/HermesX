/**
 * 投资组合（Portfolio）相关 API。
 * 负责账户管理、持仓快照、风险指标、交易记录、资金流水、公司行动、CSV 导入导出等
 * 组合管理能力的后端对接。所有查询参数统一转 snake_case，响应转 camelCase。
 */

import apiClient from './index';
import { toCamelCase } from './utils';
import type { TaskAccepted } from '../types/analysis';
import type {
  PortfolioAccountItem,
  PortfolioAccountCreateRequest,
  PortfolioAccountListResponse,
  PortfolioCashLedgerCreateRequest,
  PortfolioCashLedgerListResponse,
  PortfolioCorporateActionCreateRequest,
  PortfolioCorporateActionListResponse,
  PortfolioCostMethod,
  PortfolioDeleteResponse,
  PortfolioEventCreatedResponse,
  PortfolioFxRefreshResponse,
  PortfolioImportBrokerListResponse,
  PortfolioImportCommitResponse,
  PortfolioImportParseResponse,
  PortfolioPositionAnalysisRequest,
  PortfolioRiskResponse,
  PortfolioSnapshotResponse,
  PortfolioTradeCreateRequest,
  PortfolioTradeListResponse,
} from '../types/portfolio';

/**
 * 投资组合（Portfolio）相关 API。
 * 覆盖账户管理、持仓快照/风险、交易/资金流水/公司行动事件的增删与查询，
 * 以及 CSV 导入（券商解析/提交）。所有请求参数统一转 snake_case，响应转 camelCase。
 */

/** 持仓快照查询条件（账户/时点/计价方法/是否含实时价） */
type SnapshotQuery = {
  accountId?: number;
  asOf?: string;
  costMethod?: PortfolioCostMethod;
  includeRealtime?: boolean;
};

/** 汇率刷新查询条件 */
type FxRefreshQuery = {
  accountId?: number;
  asOf?: string;
};

/** 事件（交易/流水/公司行动）通用查询条件（账户/日期区间/分页） */
type EventQuery = {
  accountId?: number;
  dateFrom?: string;
  dateTo?: string;
  page?: number;
  pageSize?: number;
};

/** 交易列表查询（在 EventQuery 基础上支持按标的/买卖方向过滤） */
type TradeListQuery = EventQuery & {
  symbol?: string;
  side?: 'buy' | 'sell';
};

/** 资金流水列表查询（支持按收支方向过滤） */
type CashListQuery = EventQuery & {
  direction?: 'in' | 'out';
};

/** 公司行动列表查询（支持按标的/行动类型过滤） */
type CorporateListQuery = EventQuery & {
  symbol?: string;
  actionType?: 'cash_dividend' | 'split_adjustment';
};

/** 构造持仓快照查询参数（includeRealtime 转字符串 'true'/'false'） */
function buildSnapshotParams(query: SnapshotQuery): Record<string, string | number> {
  const params: Record<string, string | number> = {};
  if (query.accountId != null) {
    params.account_id = query.accountId;
  }
  if (query.asOf) {
    params.as_of = query.asOf;
  }
  if (query.costMethod) {
    params.cost_method = query.costMethod;
  }
  if (query.includeRealtime !== undefined) {
    params.include_realtime = query.includeRealtime ? 'true' : 'false';
  }
  return params;
}

/** 构造汇率刷新查询参数 */
function buildFxRefreshParams(query: FxRefreshQuery): Record<string, string | number> {
  const params: Record<string, string | number> = {};
  if (query.accountId != null) {
    params.account_id = query.accountId;
  }
  if (query.asOf) {
    params.as_of = query.asOf;
  }
  return params;
}

/** 构造事件类（交易/流水/公司行动）通用查询参数 */
function buildEventParams(query: EventQuery): Record<string, string | number> {
  const params: Record<string, string | number> = {};
  if (query.accountId != null) {
    params.account_id = query.accountId;
  }
  if (query.dateFrom) {
    params.date_from = query.dateFrom;
  }
  if (query.dateTo) {
    params.date_to = query.dateTo;
  }
  if (query.page != null) {
    params.page = query.page;
  }
  if (query.pageSize != null) {
    params.page_size = query.pageSize;
  }
  return params;
}

export const portfolioApi = {
  /** 获取账户列表（默认不含已停用账户） */
  async getAccounts(includeInactive = false): Promise<PortfolioAccountListResponse> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/portfolio/accounts', {
      params: { include_inactive: includeInactive },
    });
    return toCamelCase<PortfolioAccountListResponse>(response.data);
  },

  /** 创建账户（名称/券商/市场/基础币种/所有者） */
  async createAccount(payload: PortfolioAccountCreateRequest): Promise<PortfolioAccountItem> {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/portfolio/accounts', {
      name: payload.name,
      broker: payload.broker,
      market: payload.market,
      base_currency: payload.baseCurrency,
      owner_id: payload.ownerId,
    });
    return toCamelCase<PortfolioAccountItem>(response.data);
  },

  /** 删除账户 */
  async deleteAccount(accountId: number): Promise<PortfolioDeleteResponse> {
    const response = await apiClient.delete<Record<string, unknown>>(`/api/v1/portfolio/accounts/${accountId}`);
    return toCamelCase<PortfolioDeleteResponse>(response.data);
  },

  /** 获取持仓快照（按账户/时点/计价方法，可含实时价） */
  async getSnapshot(query: SnapshotQuery = {}): Promise<PortfolioSnapshotResponse> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/portfolio/snapshot', {
      params: buildSnapshotParams(query),
    });
    return toCamelCase<PortfolioSnapshotResponse>(response.data);
  },

  /** 提交个股定位分析任务（返回任务受理信息，分析阶段默认 auto） */
  async analyzePosition(symbol: string, payload: PortfolioPositionAnalysisRequest = {}): Promise<TaskAccepted> {
    const response = await apiClient.post<Record<string, unknown>>(
      `/api/v1/portfolio/positions/${encodeURIComponent(symbol)}/analysis`,
      {
        account_id: payload.accountId,
        analysis_phase: payload.analysisPhase ?? 'auto',
        force: payload.force ?? false,
      },
    );
    return toCamelCase<TaskAccepted>(response.data);
  },

  /** 获取持仓风险分析（与快照同源参数） */
  async getRisk(query: SnapshotQuery = {}): Promise<PortfolioRiskResponse> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/portfolio/risk', {
      params: buildSnapshotParams(query),
    });
    return toCamelCase<PortfolioRiskResponse>(response.data);
  },

  /** 刷新汇率（按账户/时点） */
  async refreshFx(query: FxRefreshQuery = {}): Promise<PortfolioFxRefreshResponse> {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/portfolio/fx/refresh', undefined, {
      params: buildFxRefreshParams(query),
    });
    return toCamelCase<PortfolioFxRefreshResponse>(response.data);
  },

  /** 创建一笔交易记录（含费用/税费/市场/币种等） */
  async createTrade(payload: PortfolioTradeCreateRequest): Promise<PortfolioEventCreatedResponse> {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/portfolio/trades', {
      account_id: payload.accountId,
      symbol: payload.symbol,
      trade_date: payload.tradeDate,
      side: payload.side,
      quantity: payload.quantity,
      price: payload.price,
      fee: payload.fee ?? 0,
      tax: payload.tax ?? 0,
      market: payload.market,
      currency: payload.currency,
      trade_uid: payload.tradeUid,
      note: payload.note,
    });
    return toCamelCase<PortfolioEventCreatedResponse>(response.data);
  },

  /** 删除交易记录 */
  async deleteTrade(tradeId: number): Promise<PortfolioDeleteResponse> {
    const response = await apiClient.delete<Record<string, unknown>>(`/api/v1/portfolio/trades/${tradeId}`);
    return toCamelCase<PortfolioDeleteResponse>(response.data);
  },

  /** 创建一条资金流水（入金/出金） */
  async createCashLedger(payload: PortfolioCashLedgerCreateRequest): Promise<PortfolioEventCreatedResponse> {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/portfolio/cash-ledger', {
      account_id: payload.accountId,
      event_date: payload.eventDate,
      direction: payload.direction,
      amount: payload.amount,
      currency: payload.currency,
      note: payload.note,
    });
    return toCamelCase<PortfolioEventCreatedResponse>(response.data);
  },

  /** 删除资金流水 */
  async deleteCashLedger(entryId: number): Promise<PortfolioDeleteResponse> {
    const response = await apiClient.delete<Record<string, unknown>>(`/api/v1/portfolio/cash-ledger/${entryId}`);
    return toCamelCase<PortfolioDeleteResponse>(response.data);
  },

  /** 创建一条公司行动（现金分红/拆股调整） */
  async createCorporateAction(payload: PortfolioCorporateActionCreateRequest): Promise<PortfolioEventCreatedResponse> {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/portfolio/corporate-actions', {
      account_id: payload.accountId,
      symbol: payload.symbol,
      effective_date: payload.effectiveDate,
      action_type: payload.actionType,
      market: payload.market,
      currency: payload.currency,
      cash_dividend_per_share: payload.cashDividendPerShare,
      split_ratio: payload.splitRatio,
      note: payload.note,
    });
    return toCamelCase<PortfolioEventCreatedResponse>(response.data);
  },

  /** 删除公司行动 */
  async deleteCorporateAction(actionId: number): Promise<PortfolioDeleteResponse> {
    const response = await apiClient.delete<Record<string, unknown>>(`/api/v1/portfolio/corporate-actions/${actionId}`);
    return toCamelCase<PortfolioDeleteResponse>(response.data);
  },

  /** 分页查询交易列表（支持按标的/买卖方向过滤） */
  async listTrades(query: TradeListQuery = {}): Promise<PortfolioTradeListResponse> {
    const params = buildEventParams(query);
    if (query.symbol) {
      params.symbol = query.symbol;
    }
    if (query.side) {
      params.side = query.side;
    }
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/portfolio/trades', { params });
    return toCamelCase<PortfolioTradeListResponse>(response.data);
  },

  /** 分页查询资金流水（支持按收支方向过滤） */
  async listCashLedger(query: CashListQuery = {}): Promise<PortfolioCashLedgerListResponse> {
    const params = buildEventParams(query);
    if (query.direction) {
      params.direction = query.direction;
    }
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/portfolio/cash-ledger', { params });
    return toCamelCase<PortfolioCashLedgerListResponse>(response.data);
  },

  /** 分页查询公司行动（支持按标的/行动类型过滤） */
  async listCorporateActions(query: CorporateListQuery = {}): Promise<PortfolioCorporateActionListResponse> {
    const params = buildEventParams(query);
    if (query.symbol) {
      params.symbol = query.symbol;
    }
    if (query.actionType) {
      params.action_type = query.actionType;
    }
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/portfolio/corporate-actions', { params });
    return toCamelCase<PortfolioCorporateActionListResponse>(response.data);
  },

  /** 获取支持的 CSV 导入券商列表 */
  async listImportBrokers(): Promise<PortfolioImportBrokerListResponse> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/portfolio/imports/csv/brokers');
    return toCamelCase<PortfolioImportBrokerListResponse>(response.data);
  },

  /** 解析券商 CSV 文件，返回可预览的解析结果（不入库） */
  async parseCsvImport(broker: string, file: File): Promise<PortfolioImportParseResponse> {
    const formData = new FormData();
    formData.append('broker', broker);
    formData.append('file', file);
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/portfolio/imports/csv/parse', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return toCamelCase<PortfolioImportParseResponse>(response.data);
  },

  /** 提交（导入）券商 CSV 文件到指定账户；dryRun=true 时只校验不写入 */
  async commitCsvImport(
    accountId: number,
    broker: string,
    file: File,
    dryRun = false,
  ): Promise<PortfolioImportCommitResponse> {
    const formData = new FormData();
    formData.append('account_id', String(accountId));
    formData.append('broker', broker);
    formData.append('dry_run', dryRun ? 'true' : 'false');
    formData.append('file', file);
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/portfolio/imports/csv/commit', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return toCamelCase<PortfolioImportCommitResponse>(response.data);
  },
};
