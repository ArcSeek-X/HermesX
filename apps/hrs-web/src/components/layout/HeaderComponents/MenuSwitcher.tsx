/**
 * MenuSwitcher
 *
 * 桌面端侧边栏折叠/展开按钮（>= lg 断点显示）：点击按 offcanvas → collapsed → fully 循环切换。
 * 折叠态图标与无障碍提示直接订阅 useLayoutStore（menuCollapsedState），与 ShellHeader 同源，无需外部传入。
 *
 * @author Lensgcx (GaoCangxiong)
 */
import { ChevronsLeft, IndentDecrease, IndentIncrease } from 'lucide-react';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { useLayoutStore } from '../../../stores';

type MenuSwitcherProps = {
  /** 切换侧边栏折叠状态（按 offcanvas → collapsed → fully 循环） */
  onToggleSidebar: () => void;
};

export const MenuSwitcher = ({ onToggleSidebar }: MenuSwitcherProps) => {
  const { t } = useUiLanguage();
  // 折叠态直接订阅 store（决定折叠按钮的图标与无障碍提示），无需外部传入
  const menuCollapsedState = useLayoutStore((state) => state.menuCollapsedState);
  return (
    <button
      type="button"
      onClick={onToggleSidebar}
      className="hidden h-10 w-6 items-center  border-r border-border/50 text-foreground-soft transition-colors hover:text-foreground lg:inline-flex cursor-pointer"
      aria-label={
        menuCollapsedState === 'fully' ? t('layout.expandSidebar') : t('layout.collapseSidebar')
      }
    >
      {/* 三态图标（线条+箭头风格）：fully 显示展开（箭头向右）；collapsed 显示「继续完全收起」；offcanvas 显示收起（箭头向左） */}
      {menuCollapsedState === 'fully' ? (
        <IndentIncrease className="h-4 w-4" />
      ) : menuCollapsedState === 'collapsed' ? (
        <ChevronsLeft className="h-4 w-4" />
      ) : (
        <IndentDecrease className="h-4 w-4" />
      )}
    </button>
  );
};
