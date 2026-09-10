/**
 * @file ReportMarkdown.tsx
 * @description ReportMarkdown 兼容包装：以 Drawer 直接挂载 ReportMarkdownPanel 的旧用法入口，
 * 供仍直接引用该组件的页面使用；新代码（HomePage）已改用 ReportMarkdownDrawer 懒加载。
 * @author Lensgcx (GaoCangxiong)
 */
import type React from 'react';
import { useCallback, useState } from 'react';
import type { ReportLanguage } from '../../types/analysis';
import { Drawer } from '../common/Drawer';
import { ReportMarkdownPanel } from './ReportMarkdownPanel';

export interface ReportMarkdownProps {
  recordId: number;
  stockName: string;
  stockCode: string;
  onClose: () => void;
  reportLanguage?: ReportLanguage;
}

/**
 * Compatibility wrapper for direct ReportMarkdown usage.
 * HomePage uses ReportMarkdownDrawer to lazy-load the panel.
 */
export const ReportMarkdown: React.FC<ReportMarkdownProps> = ({
  recordId,
  stockName,
  stockCode,
  onClose,
  reportLanguage = 'zh',
}) => {
  const [isOpen, setIsOpen] = useState(true);

  const handleClose = useCallback(() => {
    setIsOpen(false);
    setTimeout(onClose, 300);
  }, [onClose]);

  return (
    <Drawer
      isOpen={isOpen}
      onClose={handleClose}
      width="max-w-3xl"
      zIndex={100}
      backdropClassName="bg-background/56 backdrop-blur-[2px]"
    >
      <ReportMarkdownPanel
        recordId={recordId}
        stockName={stockName}
        stockCode={stockCode}
        reportLanguage={reportLanguage}
        onRequestClose={handleClose}
      />
    </Drawer>
  );
};
