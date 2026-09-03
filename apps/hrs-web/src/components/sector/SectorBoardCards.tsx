/**
 * ===================================
 * 板块卡片列表组件（SectorBoardCards）
 * ===================================
 *
 * 作用：
 * 以卡片网格形式展示 A 股行业板块或概念板块列表，支持：
 * - 行业板块 / 概念板块切换（由父组件通过二级 TAB 控制，组件本身不再维护切换器）
 * - 关键词搜索（按「板块名称 / 名称全拼 / 拼音首字母缩写」综合匹配，由父组件通过搜索框传入，
 *   搜索框 UI 嵌入二级 TAB 右侧插槽；匹配逻辑见下方 filteredBoards）
 * - 每张卡片展示：排名、板块名称、涨跌幅、总市值、换手率、涨跌家数
 *
 * 设计说明：
 * 板块类型（industry/concept）改为受控：由父页面统一经「板块」一级 TAB 下的
 * 二级 TAB 驱动，组件仅消费 `boardType`。
 * 搜索关键词同样上提到父页面，搜索框 UI 由父页面渲染到二级 TAB 右侧插槽，
 * 保证全局交互一致；本组件只负责消费关键词做过滤。
 *
 * 数据来源：
 * 通过 fetchBoardList API 从后端获取，后端代理东财 push2.eastmoney.com clist 接口。
 *
 * 视觉风格：
 * 采用项目统一的暗色终端风格，卡片使用 Card variant="bordered"，
 * 涨跌幅红涨绿跌配色与 K 线图保持一致。
 */
import type React from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
// 前端拼音工具：用于把板块中文名动态转换为全拼 / 首字母缩写，
// 从而支撑「板块名称 / 全拼 / 拼音缩写」的综合搜索（后端 BoardListItem 仅含 name，无预存拼音字段）。
import { pinyin } from 'pinyin-pro';
import { Card } from '../';
import {
  fetchBoardList,
  type BoardListItem,
} from '../../api/sectorData';
import { STOCK_UP_COLOR, STOCK_DOWN_COLOR } from '../../constants/stockColor';

/** 板块类型：industry 行业 / concept 概念 */
export type BoardType = 'industry' | 'concept';

interface SectorBoardCardsProps {
  /** 当前板块类型（受控，由父页面二级 TAB 驱动） */
  boardType: BoardType;
  /** 搜索关键词（由父页面通过二级 TAB 右侧插槽输入，本组件据此过滤） */
  searchKeyword?: string;
  /** 刷新序号：变化时强制重新拉取后端数据，用于父页面的无感刷新 */
  refreshKey?: number;
}

/**
 * 板块卡片列表组件（受控）
 *
 * 展示行业或概念板块的卡片网格，支持搜索过滤。板块类型（行业/概念）
 * 由父页面的二级 TAB 控制，搜索框 UI 也由父页面渲染在二级 TAB 右侧插槽；
 * 本组件仅消费类型与搜索词。卡片按涨跌幅降序排列（由后端排序）。
 */
export const SectorBoardCards: React.FC<SectorBoardCardsProps> = ({
  boardType,
  searchKeyword = '',
  refreshKey = 0,
}) => {
  /** 板块列表数据 */
  const [boards, setBoards] = useState<BoardListItem[]>([]);
  /** 加载状态 */
  const [loading, setLoading] = useState(false);
  /** 错误信息 */
  const [error, setError] = useState<string | null>(null);

  /** 加载板块列表数据（类型以受控 prop 为准） */
  const loadBoards = useCallback(async (type: BoardType) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchBoardList(type);
      setBoards(data.boards);
    } catch (e) {
      console.error('Failed to load board list:', e);
      setError(e instanceof Error ? e.message : '加载失败');
      setBoards([]);
    } finally {
      setLoading(false);
    }
  }, []);

  /** 受控类型 / 刷新序号变化时触发数据加载（类型与刷新由父页面二级 TAB 驱动） */
  useEffect(() => {
    loadBoards(boardType);
  }, [boardType, refreshKey, loadBoards]);

  /**
   * 按搜索关键词综合匹配板块列表。
   *
   * 匹配维度（均不区分大小写）：
   * - 板块名称（中文 contains）
   * - 名称全拼（如「电子」→ dianzi）
   * - 名称拼音首字母缩写（如「电子」→ dz）
   * 命中任一维度即保留，因此搜出 N 个就渲染 N 个卡片（不去重、不截断）。
   */
  const filteredBoards = useMemo(() => {
    const keyword = searchKeyword.trim().toLowerCase();
    if (!keyword) return boards;

    return boards.filter((item) => {
      const name = item.name.toLowerCase();
      // 1. 名称直接包含
      if (name.includes(keyword)) return true;

      // 2. 全拼 / 首字母缩写（仅当输入为纯字母时才转换，避免中文/混合输入下的无意义开销）
      if (/^[a-z]+$/.test(keyword)) {
        // 全拼：逐字转写为无声调拼音后拼接，如「电子」→ "dianzi"
        const full = pinyin(item.name, { toneType: 'none', type: 'array' })
          .join('')
          .toLowerCase();
        if (full.includes(keyword)) return true;

        // 首字母缩写：取每个字的首字母拼接，如「电子」→ "dz"
        const abbr = pinyin(item.name, { pattern: 'first', toneType: 'none', type: 'array' })
          .join('')
          .toLowerCase();
        if (abbr.includes(keyword)) return true;
      }
      return false;
    });
  }, [boards, searchKeyword]);

  /** 格式化涨跌幅文本（带正负号） */
  const formatPercent = (value: number): string => {
    const sign = value > 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  /** 获取涨跌幅颜色 */
  const getChangeColor = (value: number): string => {
    if (value > 0) return STOCK_UP_COLOR;
    if (value < 0) return STOCK_DOWN_COLOR;
    return '#999999';
  };

  /** 格式化总市值（亿） */
  const formatMarketCap = (value: number): string => {
    if (value >= 10000) {
      return `${(value / 10000).toFixed(2)}万亿`;
    }
    return `${value.toFixed(2)}亿`;
  };

  return (
    <div className="space-y-4">
      {/* ===== 卡片网格（搜索框与类型切换器由父页面统一渲染在二级 TAB 与其右侧插槽）===== */}
      {loading && boards.length === 0 ? (
        <div className="flex items-center justify-center py-24">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
        </div>
      ) : error ? (
        <div className="py-12 text-center text-sm" style={{ color: STOCK_UP_COLOR }}>
          {error}
        </div>
      ) : filteredBoards.length === 0 ? (
        <div className="py-12 text-center text-muted-text text-sm">
          {searchKeyword ? '未找到匹配的板块' : '暂无数据'}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {filteredBoards.map((item) => (
            <Card key={item.code} variant="bordered" padding="sm" className="hover:border-cyan/30 transition-colors">
              {/* 卡片头部：排名 + 板块名称 */}
              <div className="flex items-center gap-2 mb-2">
                <span className="inline-flex items-center justify-center h-5 w-5 rounded text-[10px] font-medium bg-muted/20 text-muted-text">
                  {item.rank}
                </span>
                <h4 className="text-sm font-semibold text-foreground truncate">{item.name}</h4>
              </div>

              {/* 涨跌幅（大号显示，红涨绿跌） */}
              <div
                className="text-xl font-bold font-mono mb-3"
                style={{ color: getChangeColor(item.changePercent) }}
              >
                {formatPercent(item.changePercent)}
              </div>

              {/* 总市值 + 换手率 */}
              <div className="flex items-center gap-6 mb-2">
                <div>
                  <div className="text-[10px] text-muted-text">总市值</div>
                  <div className="text-xs font-medium text-foreground">{formatMarketCap(item.totalMarketCap)}</div>
                </div>
                <div>
                  <div className="text-[10px] text-muted-text">换手率</div>
                  <div className="text-xs font-medium text-foreground">{item.turnoverRate.toFixed(2)}%</div>
                </div>
              </div>

              {/* 涨跌家数 */}
              <div className="flex items-center gap-3 text-xs">
                <span style={{ color: STOCK_UP_COLOR }}>{item.riseCount} 涨</span>
                <span style={{ color: STOCK_DOWN_COLOR }}>{item.fallCount} 跌</span>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
