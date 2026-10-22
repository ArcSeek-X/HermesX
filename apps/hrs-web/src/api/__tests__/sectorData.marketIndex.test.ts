/**
 * sectorData 市场指数字段适配回归测试。
 *
 * 背景：2f12ce50 将前端 MarketIndexItem 的字段统一改名为 changePct / prevClose，
 * 但后端 /market-indices 与 /market-cards 的 index_quote payload 仍返回
 * changePercent / preClose，适配层一度缺失，导致 /market/index 指数卡
 * 涨跌幅/涨跌点数为 '--' 且全部着色为灰色（getChangeColorClass(null)）。
 *
 * 本测试锁定 api 层适配契约，防止回归。
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  fetchMarketCards,
  fetchMarketIndices,
  toMarketIndexItem,
  type MarketCardItem,
} from '../sectorData';

const get = vi.hoisted(() => vi.fn());

vi.mock('../index', () => ({
  default: { get },
}));

describe('sectorData 市场指数字段适配', () => {
  beforeEach(() => {
    get.mockReset();
  });

  it('toMarketIndexItem 将后端 changePercent/preClose 映射为 changePct/prevClose', () => {
    const adapted = toMarketIndexItem({
      name: '上证指数',
      code: '000001',
      price: 3719.93,
      changePercent: -0.41,
      change: -15.44,
      amount: 436396170000,
      high: 3743.08,
      low: 3716.62,
      preClose: 3735.37,
    });

    expect(adapted).toEqual({
      name: '上证指数',
      code: '000001',
      price: 3719.93,
      changePct: -0.41,
      change: -15.44,
      amount: 436396170000,
      high: 3743.08,
      low: 3716.62,
      prevClose: 3735.37,
    });
  });

  it('toMarketIndexItem 对缺失字段归 null，交由消费侧占位渲染', () => {
    const adapted = toMarketIndexItem({
      name: '--',
      code: '',
      price: null,
      changePercent: null,
      change: null,
      amount: null,
      high: null,
      low: null,
      preClose: null,
    });

    expect(adapted.changePct).toBeNull();
    expect(adapted.prevClose).toBeNull();
    expect(adapted.price).toBeNull();
  });

  it('fetchMarketIndices 返回适配后的 MarketIndexItem（而非原始 payload）', async () => {
    get.mockResolvedValueOnce({
      data: {
        indices: [
          {
            name: '上证指数',
            code: '000001',
            price: 3719.93,
            changePercent: -0.41,
            change: -15.44,
            amount: 436396170000,
            high: null,
            low: null,
            preClose: null,
          },
        ],
      },
    });

    const indices = await fetchMarketIndices();

    expect(indices).toHaveLength(1);
    expect(indices[0].changePct).toBe(-0.41);
    expect(indices[0].prevClose).toBeNull();
    // 后端原字段不得残留在适配结果中
    expect(indices[0]).not.toHaveProperty('changePercent');
    expect(indices[0]).not.toHaveProperty('preClose');
  });

  it('fetchMarketCards 仅适配 index_quote payload，其余卡片原样透传', async () => {
    get.mockResolvedValueOnce({
      data: {
        market: 'a',
        cards: [
          {
            cardType: 'index_quote',
            cardKey: 'index_quote:000001',
            payload: {
              name: '上证指数',
              code: '000001',
              price: 3719.93,
              changePercent: -0.41,
              change: -15.44,
              amount: 436396170000,
              high: null,
              low: null,
              preClose: null,
            },
          },
          {
            cardType: 'market_breadth',
            cardKey: 'market_breadth',
            payload: { riseCount: 2624, fallCount: 2723, flatCount: 227 },
          },
          {
            cardType: 'strongest_board',
            cardKey: 'strongest_board',
            payload: {
              rank: 1,
              code: 'BK1295',
              name: '其他数字媒体',
              changePercent: 8.04,
              totalMarketCap: 141.06,
              turnoverRate: 17.18,
              riseCount: 2,
              fallCount: 0,
            },
          },
        ] as MarketCardItem[],
      },
    });

    const response = await fetchMarketCards('a');

    expect(response.market).toBe('a');
    expect(response.cards).toHaveLength(3);

    const indexCard = response.cards[0];
    expect(indexCard.cardType).toBe('index_quote');
    if (indexCard.cardType === 'index_quote') {
      expect(indexCard.payload.changePct).toBe(-0.41);
      expect(indexCard.payload).not.toHaveProperty('changePercent');
    }

    // 非 index_quote 卡片保持后端契约（BoardListItem.changePercent 不在本次改名范围）
    const breadthCard = response.cards[1];
    expect(breadthCard.cardType).toBe('market_breadth');
    if (breadthCard.cardType === 'market_breadth') {
      expect(breadthCard.payload).toEqual({ riseCount: 2624, fallCount: 2723, flatCount: 227 });
    }

    const boardCard = response.cards[2];
    expect(boardCard.cardType).toBe('strongest_board');
    if (boardCard.cardType === 'strongest_board') {
      expect(boardCard.payload?.changePercent).toBe(8.04);
    }
  });
});
