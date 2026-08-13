/**
 * ===================================
 * 分页组件（Pagination）
 * ===================================
 *
 * 【功能介绍】
 * 通用的「分页控件」，用于在长列表 / 表格底部切换页码。采用终端风格（terminal-inspired）的暗色按钮样式，
 * 支持「上一页 / 下一页」与带省略号（…）的页码列表，在页码较多时自动折叠中间页码，保持控件紧凑。
 *
 * 【设计要点】
 * 1. 页码折叠算法：getPageNumbers 以当前页为中心（delta=2），
 *    始终保留首页、尾页与当前页附近的页码，其余以 '...' 占位，避免页码过多撑爆布局。
 * 2. 边界禁用：currentPage=1 时「上一页」禁用，currentPage=totalPages 时「下一页」禁用。
 * 3. 当前页高亮：当前页按钮使用 cyan 主色填充 + 阴影，与常规按钮形成对比。
 * 4. 零页隐藏：totalPages<=1 时直接返回 null，不渲染分页控件。
 * 5. 内部子组件 PageButton：根据 page 是否为 '...' 决定渲染省略号或按钮，统一按钮样式。
 *
 * 【使用方式】
 *   <Pagination currentPage={page} totalPages={total} onPageChange={setPage} />
 */

import type React from 'react';
import { cn } from '../../utils/cn';

/** 单个页码按钮（含省略号）的 Props */
interface PageButtonProps {
  /** 页码数字，或字符串 '...' 表示省略号 */
  page: number | string;
  /** 是否为当前页（高亮） */
  isActive?: boolean;
  /** 是否禁用（如边界页） */
  disabled?: boolean;
  /** 点击回调 */
  onClick?: () => void;
  /** 子节点（一般为箭头图标或页码文本） */
  children?: React.ReactNode;
}

/** 单个页码按钮：省略号渲染为静态文本，否则渲染可点击按钮 */
const PageButton: React.FC<PageButtonProps> = ({ page, isActive, disabled, onClick, children }) => {
  // 省略号：仅作占位展示，不可点击
  const isEllipsis = page === '...';

  if (isEllipsis) {
    return <span className="px-3 py-2 text-muted-text">...</span>;
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'inline-flex h-10 min-w-[2.5rem] items-center justify-center rounded-xl border px-3 text-sm font-medium transition-all duration-200',
        // 当前页：cyan 填充 + 标题色文字 + 发光阴影
        isActive
          ? 'border-cyan/30 bg-cyan text-slate-950 shadow-lg shadow-cyan/20'
          : 'border-border/60 bg-elevated text-secondary-text hover:bg-hover hover:text-foreground',
        disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer',
      )}
    >
      {children || page}
    </button>
  );
};

/** Pagination 组件的 Props 定义 */
interface PaginationProps {
  /** 当前页码（从 1 开始） */
  currentPage: number;
  /** 总页数 */
  totalPages: number;
  /** 页码变化回调 */
  onPageChange: (page: number) => void;
  /** 透传的额外类名 */
  className?: string;
}

/**
 * 分页控件：上一页 / 页码列表（带省略号折叠）/ 下一页。
 *
 * @param props - 组件属性
 * @param props.currentPage - 当前页
 * @param props.totalPages - 总页数
 * @param props.onPageChange - 翻页回调
 * @param props.className - 额外类名
 * @returns 分页控件，总页数 <=1 时返回 null
 */
export const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  onPageChange,
  className = '',
}) => {
  // 单页或无需分页时，不渲染控件
  if (totalPages <= 1) return null;

  // 生成带省略号的页码序列：保留首页/尾页 + 当前页附近（delta=2），中间折叠为 '...'
  const getPageNumbers = (): (number | string)[] => {
    const pages: (number | string)[] = [];
    const delta = 2;

    for (let i = 1; i <= totalPages; i++) {
      if (
        i === 1 ||
        i === totalPages ||
        (i >= currentPage - delta && i <= currentPage + delta)
      ) {
        pages.push(i);
      } else if (pages[pages.length - 1] !== '...') {
        // 仅在尚未插入省略号时插入，避免连续多个 '...'
        pages.push('...');
      }
    }

    return pages;
  };

  return (
    // 整体：居中 + 间距
    <div className={cn('flex items-center justify-center gap-2', className)}>
      {/* 上一页按钮：首页时禁用 */}
      <PageButton
        page="prev"
        disabled={currentPage === 1}
        onClick={() => onPageChange(currentPage - 1)}
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </PageButton>

      {/* 页码列表：数字可点跳转，'...' 为静态占位 */}
      {getPageNumbers().map((page, index) => (
        <PageButton
          key={`${page}-${index}`}
          page={page}
          isActive={page === currentPage}
          onClick={() => typeof page === 'number' && onPageChange(page)}
        />
      ))}

      {/* 下一页按钮：尾页时禁用 */}
      <PageButton
        page="next"
        disabled={currentPage === totalPages}
        onClick={() => onPageChange(currentPage + 1)}
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </PageButton>
    </div>
  );
};
