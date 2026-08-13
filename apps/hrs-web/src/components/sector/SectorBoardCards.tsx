/**
 * ===================================
 * 板块卡片列表组件（SectorBoardCards）
 * ===================================
 *
 * 作用：
 * 以卡片网格形式展示 A 股行业板块或概念板块列表，支持：
 * - 行业板块 / 概念板块切换
 * - 关键词搜索（按板块名称过滤）
 * - 每张卡片展示：排名、板块名称、涨跌幅、总市值、换手率、涨跌家数
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
import { Search, Building2, Lightbulb } from 'lucide-react';
import { Card } from '../';
import {
  fetchBoardList,
  type BoardListItem,
} from '../../api/sectorData';
import { STOCK_UP_COLOR, STOCK_DOWN_COLOR } from '../../constants/colors';

/** 板块类型切换选项 */
const BOARD_TYPE_OPTIONS = [
  { key: 'industry' as const, label: '行业板块', icon: Building2 },
  { key: 'concept' as const, label: '概念板块', icon: Lightbulb },
];

/**
 * 板块卡片列表组件
 *
 * 展示行业或概念板块的卡片网格，支持搜索过滤和类型切换。
 * 卡片按涨跌幅降序排列（由后端排序）。
 */
export const SectorBoardCards: React.FC = () => {
  /** 当前板块类型：industry 行业 / concept 概念 */
  const [boardType, setBoardType] = useState<'industry' | 'concept'>('industry');
  /** 搜索关键词 */
  const [searchKeyword, setSearchKeyword] = useState('');
  /** 板块列表数据 */
  const [boards, setBoards] = useState<BoardListItem[]>([]);
  /** 加载状态 */
  const [loading, setLoading] = useState(false);
  /** 错误信息 */
  const [error, setError] = useState<string | null>(null);

  /** 加载板块列表数据 */
  const loadBoards = useCallback(async (type?: 'industry' | 'concept') => {
    const sectorType = type ?? boardType;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchBoardList(sectorType);
      setBoards(data.boards);
    } catch (e) {
      console.error('Failed to load board list:', e);
      setError(e instanceof Error ? e.message : '加载失败');
      setBoards([]);
    } finally {
      setLoading(false);
    }
  }, [boardType]);

  /** 切换板块类型时重新加载数据 */
  const handleTypeChange = useCallback((type: 'industry' | 'concept') => {
    setBoardType(type);
    setSearchKeyword('');
  }, []);

  /** 板块类型切换时触发数据加载 */
  useEffect(() => {
    loadBoards(boardType);
  }, [boardType, loadBoards]);

  /** 根据搜索关键词过滤板块列表 */
  const filteredBoards = useMemo(() => {
    if (!searchKeyword.trim()) return boards;
    const keyword = searchKeyword.toLowerCase();
    return boards.filter((item) =>
      item.name.toLowerCase().includes(keyword)
    );
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
      {/* ===== 控制栏：类型切换 + 搜索框 ===== */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        {/* 板块类型切换按钮组 */}
        <div className="flex items-center gap-1 rounded-lg border border-subtle bg-bg-elevated p-1">
          {BOARD_TYPE_OPTIONS.map((opt) => {
            const Icon = opt.icon;
            const isActive = boardType === opt.key;
            return (
              <button
                key={opt.key}
                type="button"
                onClick={() => handleTypeChange(opt.key)}
                className={`inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  isActive
                    ? 'bg-cyan/15 text-cyan'
                    : 'text-muted-text hover:text-foreground hover:bg-white/5'
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {opt.label}
              </button>
            );
          })}
        </div>

        {/* 搜索框 */}
        <div className="relative w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-text" />
          <input
            type="text"
            placeholder="搜索板块..."
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-subtle bg-bg-elevated text-foreground placeholder:text-muted-text focus:outline-none focus:border-cyan/50 transition-colors"
          />
        </div>
      </div>

      {/* ===== 卡片网格 ===== */}
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
