/**
 * UserSetting —— 右上角「个人设置」入口组件
 * =====================================================================
 * 【功能介绍】
 * 渲染在页面头部（ShellHeader）右上角的用户操作入口，提供两类能力：
 *   1. 一个齿轮图标按钮，点击后展开下拉菜单（popover）；
 *   2. 下拉菜单包含：
 *        - 「设置」：跳转到 /settings 设置页；
 *        - 「退出登录」：仅当系统开启登录鉴权（authEnabled）时显示，
 *          点击后弹出二次确认对话框，确认后调用 useAuth().logout() 退出。
 *
 * 【设计要点】
 * - 退出登录的二次确认复用通用组件 common/ConfirmDialog，
 *   相关文案（标题、提示、确认/取消按钮）与侧边栏、国际化文件保持一致。
 * - 下拉菜单的打开/关闭通过 open 状态控制；
 *   点击按钮自身切换 open，点击菜单外部或按 Esc 自动收起。
 * - 退出确认框的显示由独立的 showLogoutConfirm 状态控制，
 *   与下拉菜单的 open 解耦，避免相互干扰。
 * - 组件内部持有 ref，用于判断点击事件是否发生在组件之外（点外关闭）。
 * =====================================================================
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, Settings2, UserCog } from 'lucide-react';
import { cn } from '../../../utils/cn';
import { useAuth } from '../../../hooks';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { ConfirmDialog } from '../..';

export const UserSetting = () => {
  // 是否开启登录鉴权（未开启则不显示「退出登录」）
  const { authEnabled, logout } = useAuth();
  // 国际化文案 hook
  const { t } = useUiLanguage();
  // 路由跳转 hook
  const navigate = useNavigate();
  // 下拉菜单的开关状态
  const [open, setOpen] = useState(false);
  // 退出登录「二次确认」弹窗的开关状态
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  // 组件根节点引用，用于「点击外部关闭」判断
  const ref = useRef<HTMLDivElement>(null);

  // 下拉菜单打开时，挂载全局监听：点击外部 / 按下 Esc 收起菜单
  useEffect(() => {
    if (!open) return;
    // 鼠标按下时，若目标不在组件内部，则关闭菜单
    const onPointerDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    // 按下 Esc 键关闭菜单
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKey);
    // 卸载时移除监听，避免内存泄漏
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  // 下拉菜单中每一项按钮的统一样式（Flex 行布局 + 悬停高亮）
  const menuItemClass = cn(
    'flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-secondary-text transition-colors hover:bg-hover hover:text-foreground'
  );

  return (
    // 根容器：relative 定位，作为下拉菜单（absolute）的参照锚点
    <div className="relative" ref={ref}>
      {/* 触发按钮：齿轮图标 + 无障碍属性，点击切换菜单开关 */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={t('header.userSettings')}
        title={t('header.userSettings')}
        aria-haspopup="menu"
        aria-expanded={open}
        className="inline-flex h-9 w-9 items-center justify-center rounded-[10px] border border-border/70 bg-card/80 text-secondary-text shadow-soft-card transition-colors hover:bg-hover hover:text-foreground"
      >
        <UserCog className="h-4 w-4" />
      </button>

      {/* 下拉菜单：仅在 open 为 true 时渲染，右对齐贴在按钮下方 */}
      {open && (
        <div
          role="menu"
          aria-label={t('header.userSettings')}
          className="absolute right-0 top-[calc(100%+8px)] z-50 w-44 rounded-xl border border-border/80 bg-card p-1.5 shadow-lg"
        >
          {/* 菜单项：跳转设置页，点击后先关闭菜单再跳转 */}
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              navigate('/settings');
            }}
            className={menuItemClass}
          >
            <Settings2 className="h-4 w-4 shrink-0" />
            {t('layout.nav.settings')}
          </button>

          {/* 菜单项：退出登录（仅开启鉴权时显示），点击后关闭菜单并弹出二次确认 */}
          {authEnabled && (
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                setShowLogoutConfirm(true);
              }}
              className={menuItemClass}
            >
              <LogOut className="h-4 w-4 shrink-0" />
              {t('layout.logout')}
            </button>
          )}
        </div>
      )}

      {/* 退出登录的二次确认对话框：危险样式 + 确认即退出 */}
      <ConfirmDialog
        isOpen={showLogoutConfirm}
        title={t('layout.logoutTitle')}
        message={t('layout.logoutMessage')}
        confirmText={t('layout.logoutConfirm')}
        cancelText={t('common.cancel')}
        isDanger
        onConfirm={() => {
          setShowLogoutConfirm(false);
          void logout();
        }}
        onCancel={() => setShowLogoutConfirm(false)}
      />
    </div>
  );
};