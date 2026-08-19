/**
 * Pagination.tsx
 * ------------------------------------------------------------
 * 文件作用：
 *   通用分页组件。基于 HeroUI Pagination 复合组件封装，提供页码导航与数据统计。
 *   采用受控模式：调用方管理当前页码，通过 onPageChange 接收翻页事件。
 *
 * 核心功能：
 *   1. 页码导航：上一页 / 下一页按钮、数字页码链接；
 *   2. 智能省略：页数较多时自动折叠中间页码，显示省略号；
 *   3. 数据统计：显示当前范围与总条数（如 "1 - 20 / 共 100 条"）；
 *   4. 受控模式：pageNum 与 onPageChange 由调用方管理状态。
 *
 * 使用示例：
 *   <Pagination
 *     total={100}
 *     pageSize={20}
 *     pages={5}
 *     pageNum={1}
 *     onPageChange={(page) => setPage(page)}
 *     size="sm"
 *     className="mt-2"
 *   />
 * ------------------------------------------------------------
 */

import { useMemo } from 'react';
import { Pagination } from '@heroui/react';

/**
 * 分页组件属性接口。
 * 采用受控模式：调用方负责维护页码状态，组件通过 onPageChange 通知翻页。
 */
export interface PaginationProps {
  /** 总条数 */
  total: number;
  /** 每页显示的行数，默认 10 */
  pageSize?: number;
  /** 总页数 */
  pages: number;
  /** 当前页码（从 1 开始），默认 1 */
  pageNum?: number;
  /** 页码变化时的回调 */
  onPageChange: (pageNum: number) => void;
  /** 分页组件尺寸，默认 'md' */
  size?: 'xs' | 'sm' | 'md' | 'lg';
  /** 外层容器自定义类名 */
  className?: string;
}

/**
 * 通用分页组件。
 *
 * 负责渲染分页导航控件，包括上一页/下一页、页码链接、省略号和数据统计。
 * 当总页数超过 7 页时，自动折叠中间页码并用省略号替代。
 */
export default function PaginationBar({
  total,
  pageSize = 2,
  pages,
  pageNum = 1,
  onPageChange,
  size = 'xs',
  className = '',
}: PaginationProps) {
  /** 选中页码的样式：无背景 + 主题色文字 + 最粗字重 */
  const activeClass = 'bg-transparent text-primary !font-bold hover:bg-transparent';

  /** 安全页码：限制在 [1, pages] 范围内 */
  const safePage = Math.min(Math.max(1, pageNum), Math.max(1, pages));

  /** 根据 size 映射文字字号，与 HeroUI 按钮尺寸对齐 */
  const paginationTextSize: Record<string, string> = {
    xs: '!text-xs',
    sm: '!text-sm',
    md: '!text-md',
    lg: '!text-lg',
  };
  const paginationTextClass = paginationTextSize[size] || 'text-sm';

  /** 当前页起止位置 */
  const start = (safePage - 1) * pageSize + 1;
  const end = Math.min(safePage * pageSize, total);

  /**
   * 生成页码列表。
   * 页数 ≤ 7 时显示全部页码；否则显示首尾页 + 当前页邻居 + 省略号。
   */
  const pageList = useMemo((): (number | 'ellipsis')[] => {
    if (pages <= 0) return [];
    if (pages <= 7) {
      return Array.from({ length: pages }, (_, i) => i + 1);
    }

    const result: (number | 'ellipsis')[] = [1];

    if (safePage > 3) {
      result.push('ellipsis');
    }

    const rangeStart = Math.max(2, safePage - 1);
    const rangeEnd = Math.min(pages - 1, safePage + 1);
    for (let i = rangeStart; i <= rangeEnd; i++) {
      result.push(i);
    }

    if (safePage < pages - 2) {
      result.push('ellipsis');
    }

    result.push(pages);
    return result;
  }, [pages, safePage]);

  return (
    <div className={`flex items-center justify-between px-3 py-2 border-t border-subtle !text-text-secondary ${className}`}> 
      <Pagination size={size}>
        <Pagination.Summary className={paginationTextClass}>
          {total === 0 ? '暂无数据' : `显示 ${start} - ${end} 条 / 共 ${total} 条`}
        </Pagination.Summary>
        <Pagination.Content>
          {/* 上一页 */}
          <Pagination.Item>
            <Pagination.Previous
              isDisabled={safePage === 1}
              onPress={() => onPageChange(Math.max(1, safePage - 1))}
            >
              <Pagination.PreviousIcon />
              <span className={paginationTextClass}>上一页</span>
            </Pagination.Previous>
          </Pagination.Item>

          {/* 页码链接 / 省略号 */}
          {pageList.map((p, i) =>
            p === 'ellipsis' ? (
              <Pagination.Item key={`ellipsis-${i}`}>
                <Pagination.Ellipsis />
              </Pagination.Item>
            ) : (
              <Pagination.Item key={p}>
                <Pagination.Link
                  isActive={p === safePage}
                  onPress={() => onPageChange(p)}
                  className={`bg-transparent hover:bg-transparent !text-text-secondary hover:text-primary ${paginationTextClass} ${p === safePage && activeClass ? activeClass : ''}`}
                >
                  {p}
                </Pagination.Link>
              </Pagination.Item>
            ),
          )}

          {/* 下一页 */}
          <Pagination.Item>
            <Pagination.Next
              isDisabled={safePage === pages || pages === 0}
              onPress={() => onPageChange(Math.min(pages, safePage + 1))}
            >
              <span className={paginationTextClass}>下一页</span>
              <Pagination.NextIcon />
            </Pagination.Next>
          </Pagination.Item>
        </Pagination.Content>
      </Pagination>
    </div>
  );
}
