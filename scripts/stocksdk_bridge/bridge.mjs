#!/usr/bin/env node

import process from 'node:process';

process.env.NODE_NO_WARNINGS = process.env.NODE_NO_WARNINGS || '1';

let cachedSdk = null;
let cachedSdkSignature = '';
const A_INDEX_CODES = [
  '000001.SH',
  '399001.SZ',
  '399006.SZ',
  '000688.SH',
  '000016.SH',
  '000300.SH',
  '399905.SZ',
  '399303.SZ',
  '899050.BJ',
];
const HK_INDEX_CODES = ['HSI', 'HSCEI', 'HSTECH'];
const US_INDEX_CODES = ['DJI', 'INX', 'IXIC'];

function stripUndefined(value) {
  if (Array.isArray(value)) {
    return value
      .filter((item) => item !== undefined)
      .map((item) => (item && typeof item === 'object' ? stripUndefined(item) : item));
  }
  if (!value || typeof value !== 'object') {
    return value;
  }
  return Object.fromEntries(
    Object.entries(value)
      .filter(([, item]) => item !== undefined && item !== null && item !== '')
      .map(([key, item]) => [
        key,
        item && typeof item === 'object' && !Array.isArray(item) ? stripUndefined(item) : item,
      ]),
  );
}

async function readStdin() {
  let chunks = '';
  for await (const chunk of process.stdin) {
    chunks += chunk;
  }
  return chunks.trim();
}

async function loadStockSdk(options) {
  const signature = JSON.stringify(stripUndefined(options || {}));
  if (cachedSdk && cachedSdkSignature === signature) {
    return cachedSdk;
  }
  const module = await import('stock-sdk');
  const StockSDK = module.StockSDK || module.default?.StockSDK || module.default;
  if (typeof StockSDK !== 'function') {
    throw new Error('stock-sdk does not export StockSDK');
  }
  cachedSdk = new StockSDK(stripUndefined(options || {}));
  cachedSdkSignature = signature;
  return cachedSdk;
}

function isMinutePeriod(period) {
  return ['1m', '5m', '15m', '30m', '60m', '120m'].includes(period);
}

function toLegacyPeriod(period) {
  if (period === 'yearly') {
    return 'monthly';
  }
  if (period === '5d') {
    return 'daily';
  }
  if (period === '120m') {
    return '60m';
  }
  return period || 'daily';
}

function toFiniteNumber(value) {
  if (value === null || value === undefined || value === '' || value === '-') {
    return null;
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function sumNumbers(values) {
  let total = 0;
  let found = false;
  for (const value of values) {
    const numeric = toFiniteNumber(value);
    if (numeric === null) {
      continue;
    }
    total += numeric;
    found = true;
  }
  return found ? total : null;
}

function isCloseToTarget(value, target) {
  const current = toFiniteNumber(value);
  const expected = toFiniteNumber(target);
  if (current === null || expected === null || expected <= 0) {
    return false;
  }
  const tolerance = Math.max(0.01, Math.abs(expected) * 0.001);
  return Math.abs(current - expected) <= tolerance;
}

function normalizeIndexRow(row, market) {
  const high = toFiniteNumber(row?.high);
  const low = toFiniteNumber(row?.low);
  const preClose = toFiniteNumber(row?.prevClose ?? row?.preClose);
  const rawAmount = toFiniteNumber(row?.amount);
  return {
    name: String(row?.name || '').trim(),
    code: String(row?.code || '').trim(),
    price: toFiniteNumber(row?.price),
    changePercent: toFiniteNumber(row?.changePercent),
    change: toFiniteNumber(row?.change),
    amount: market === 'a' && rawAmount !== null ? rawAmount * 10000 : null,
    high,
    low,
    preClose,
  };
}

async function runPing(sdk) {
  if (typeof sdk.clearCaches === 'function') {
    return { ok: true, supportsCacheClear: true };
  }
  return { ok: true };
}

async function runSearch(sdk, payload) {
  const keyword = String(payload.query || '').trim();
  if (!keyword) {
    return [];
  }
  const results = await sdk.search(keyword);
  const limit = Math.max(Number(payload.limit || 10), 1);
  return Array.isArray(results) ? results.slice(0, limit) : [];
}

async function runQuote(sdk, payload) {
  const market = String(payload.market || 'cn').toLowerCase();
  const symbol = String(payload.symbol || '').trim();
  if (!symbol) {
    throw new Error('quote symbol is required');
  }

  if (sdk.quotes && typeof sdk.quotes[market] === 'function') {
    const rows = await sdk.quotes[market]([symbol]);
    return Array.isArray(rows) ? rows[0] || null : rows || null;
  }

  if (market === 'cn') {
    if (typeof sdk.getFullQuotes === 'function') {
      const rows = await sdk.getFullQuotes([symbol]);
      return Array.isArray(rows) ? rows[0] || null : rows || null;
    }
    if (typeof sdk.getSimpleQuotes === 'function') {
      const rows = await sdk.getSimpleQuotes([symbol]);
      return Array.isArray(rows) ? rows[0] || null : rows || null;
    }
  }

  throw new Error(`quote market not supported by bridge: ${market}`);
}

async function runKline(sdk, payload) {
  const market = String(payload.market || 'cn').toLowerCase();
  const symbol = String(payload.symbol || '').trim();
  const requestedPeriod = String(payload.period || 'daily').toLowerCase();
  const period = toLegacyPeriod(requestedPeriod);
  const limit = Math.max(Number(payload.limit || 1), 1);
  const adjust = payload.adjust === undefined ? 'qfq' : payload.adjust;
  const options = stripUndefined({
    period,
    adjust,
    limit,
    endDate: payload.beforeDate,
  });

  const normalize = (rows) => (Array.isArray(rows) ? rows.slice(-limit) : rows);

  if (market === 'cn' && isMinutePeriod(requestedPeriod) && sdk.kline && typeof sdk.kline.cnMinute === 'function') {
    return normalize(await sdk.kline.cnMinute(symbol, options));
  }
  if (sdk.kline && typeof sdk.kline[market] === 'function') {
    return normalize(await sdk.kline[market](symbol, options));
  }

  if (market === 'cn') {
    if (isMinutePeriod(period) && typeof sdk.getMinuteKline === 'function') {
      return normalize(await sdk.getMinuteKline(symbol, options));
    }
    if (typeof sdk.getHistoryKline === 'function') {
      return normalize(await sdk.getHistoryKline(symbol, options));
    }
  }
  if (market === 'hk' && typeof sdk.getHKHistoryKline === 'function') {
    return normalize(await sdk.getHKHistoryKline(symbol, options));
  }
  if (market === 'us' && typeof sdk.getUSHistoryKline === 'function') {
    return normalize(await sdk.getUSHistoryKline(symbol, options));
  }

  throw new Error(`kline market not supported by bridge: ${market}`);
}

async function runMarketIndices(sdk, payload) {
  const market = String(payload.market || 'a').toLowerCase();
  if (market === 'a') {
    const rows = await sdk.quotes.cnSimple(A_INDEX_CODES);
    return Array.isArray(rows) ? rows.map((row) => normalizeIndexRow(row, market)) : [];
  }
  if (market === 'us') {
    const [hkRows, usRows] = await Promise.all([
      sdk.quotes.hk(HK_INDEX_CODES),
      sdk.quotes.us(US_INDEX_CODES),
    ]);
    return [
      ...(Array.isArray(hkRows) ? hkRows.map((row) => normalizeIndexRow(row, market)) : []),
      ...(Array.isArray(usRows) ? usRows.map((row) => normalizeIndexRow(row, market)) : []),
    ];
  }
  throw new Error(`market indices not supported by bridge: ${market}`);
}

async function runMarketOverview(sdk) {
  const rows = await sdk.batch.cn({ batchSize: 500, concurrency: 4 });
  if (!Array.isArray(rows) || rows.length === 0) {
    return null;
  }

  let riseCount = 0;
  let fallCount = 0;
  let flatCount = 0;
  let limitUpCount = 0;
  let limitDownCount = 0;
  let totalAmount = 0;
  let weightedVolumeRatio = 0;
  let weightAmount = 0;

  for (const row of rows) {
    const changePercent = toFiniteNumber(row?.changePercent);
    const amountWan = toFiniteNumber(row?.amount);
    const amount = amountWan !== null ? amountWan * 10000 : null;
    const price = toFiniteNumber(row?.price);

    if (changePercent !== null) {
      if (changePercent > 0) {
        riseCount += 1;
      } else if (changePercent < 0) {
        fallCount += 1;
      } else {
        flatCount += 1;
      }
    }

    if (isCloseToTarget(price, row?.limitUp)) {
      limitUpCount += 1;
    } else if (isCloseToTarget(price, row?.limitDown)) {
      limitDownCount += 1;
    }

    if (amount !== null && amount > 0) {
      totalAmount += amount;
      const volumeRatio = toFiniteNumber(row?.volumeRatio);
      if (volumeRatio !== null) {
        weightedVolumeRatio += volumeRatio * amount;
        weightAmount += amount;
      }
    }
  }

  return {
    riseCount,
    fallCount,
    flatCount,
    totalAmount,
    volumeRatio: weightAmount > 0 ? Math.round((weightedVolumeRatio / weightAmount) * 100) / 100 : null,
    limitUpCount,
    limitDownCount,
  };
}

async function runNorthboundSummary(sdk) {
  const rows = await sdk.northbound.summary();
  if (!Array.isArray(rows) || rows.length === 0) {
    return null;
  }

  const northRows = rows.filter((row) => {
    const direction = String(row?.direction || '');
    const boardName = String(row?.boardName || '');
    return direction.includes('北') || boardName === '沪股通' || boardName === '深股通';
  });
  if (northRows.length === 0) {
    return null;
  }

  const netInflow = sumNumbers(northRows.map((row) => row?.netInflow));
  const netBuyAmount = sumNumbers(northRows.map((row) => row?.netBuyAmount));
  const riseCount = sumNumbers(northRows.map((row) => row?.upCount));
  const fallCount = sumNumbers(northRows.map((row) => row?.downCount));
  const dates = northRows
    .map((row) => String(row?.date || '').trim())
    .filter(Boolean)
    .sort();

  return {
    netInflow: netInflow && netInflow !== 0 ? netInflow : netBuyAmount && netBuyAmount !== 0 ? netBuyAmount : null,
    name: '北向资金',
    date: dates.length > 0 ? dates[dates.length - 1] : null,
    riseCount: riseCount ?? null,
    fallCount: fallCount ?? null,
  };
}

async function runMarketFundFlow(sdk) {
  const rows = await sdk.fundFlow.market();
  if (!Array.isArray(rows) || rows.length === 0) {
    return null;
  }
  const latest = rows[rows.length - 1];
  return {
    mainNetInflow: toFiniteNumber(latest?.mainNetInflow),
    mainNetInflowPercent: toFiniteNumber(latest?.mainNetInflowPercent),
    date: String(latest?.date || '').trim() || null,
  };
}

function normalizeBoardItem(row, index) {
  const totalMarketCap = toFiniteNumber(row?.totalMarketCap);
  return {
    rank: Number.isFinite(Number(row?.rank)) ? Number(row.rank) : index + 1,
    code: String(row?.code || '').trim(),
    name: String(row?.name || '').trim(),
    changePercent: toFiniteNumber(row?.changePercent) ?? 0,
    totalMarketCap,
    turnoverRate: toFiniteNumber(row?.turnoverRate) ?? 0,
    riseCount: toFiniteNumber(row?.riseCount) ?? 0,
    fallCount: toFiniteNumber(row?.fallCount) ?? 0,
    leadingStock: row?.leadingStock ? String(row.leadingStock) : null,
    leadingStockChangePercent: toFiniteNumber(row?.leadingStockChangePercent),
  };
}

async function runBoardList(sdk, payload) {
  const sectorType = String(payload.sectorType || 'industry').toLowerCase();
  if (!sdk.board || !sdk.board[sectorType] || typeof sdk.board[sectorType].list !== 'function') {
    throw new Error(`board list not supported by bridge: ${sectorType}`);
  }
  const rows = await sdk.board[sectorType].list();
  return Array.isArray(rows) ? rows.map((row, index) => normalizeBoardItem(row, index)) : [];
}

async function runSectorFundFlowRank(sdk, payload) {
  const sectorType = String(payload.sectorType || 'industry').toLowerCase();
  const limit = Math.max(Number(payload.limit || 10), 1);
  const rows = await sdk.fundFlow.sectorRank({ sectorType });
  return Array.isArray(rows) ? rows.slice(0, limit) : [];
}

async function runSectorFundFlowHistoryBatch(sdk, payload) {
  const codes = Array.isArray(payload.codes)
    ? payload.codes.map((item) => String(item || '').trim()).filter(Boolean)
    : [];
  const limit = Math.max(Number(payload.limit || 30), 1);
  const entries = await Promise.all(
    codes.map(async (code) => [code, await sdk.fundFlow.sectorHistory(code, { limit })]),
  );
  return Object.fromEntries(entries);
}

async function main() {
  const rawInput = (process.argv[2] || '').trim() || (await readStdin());
  if (!rawInput) {
    throw new Error('bridge request payload is empty');
  }

  const request = JSON.parse(rawInput);
  const sdk = await loadStockSdk(request.sdkOptions || {});
  const action = String(request.action || '').trim();
  const payload = request.payload || {};

  let data;
  switch (action) {
    case 'ping':
      data = await runPing(sdk, payload);
      break;
    case 'search':
      data = await runSearch(sdk, payload);
      break;
    case 'quote':
      data = await runQuote(sdk, payload);
      break;
    case 'kline':
      data = await runKline(sdk, payload);
      break;
    case 'market_indices':
      data = await runMarketIndices(sdk, payload);
      break;
    case 'market_overview':
      data = await runMarketOverview(sdk, payload);
      break;
    case 'northbound_summary':
      data = await runNorthboundSummary(sdk, payload);
      break;
    case 'market_fund_flow':
      data = await runMarketFundFlow(sdk, payload);
      break;
    case 'board_list':
      data = await runBoardList(sdk, payload);
      break;
    case 'sector_fund_flow_rank':
      data = await runSectorFundFlowRank(sdk, payload);
      break;
    case 'sector_fund_flow_history_batch':
      data = await runSectorFundFlowHistoryBatch(sdk, payload);
      break;
    default:
      throw new Error(`unsupported bridge action: ${action}`);
  }

  process.stdout.write(JSON.stringify({ ok: true, data }));
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  process.stdout.write(
    JSON.stringify({
      ok: false,
      error: {
        code: 'stocksdk_bridge_error',
        message,
      },
    }),
  );
  process.exitCode = 1;
});
