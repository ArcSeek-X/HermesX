/**
 * UserMenu
 *
 * 右上角「个人设置」入口：齿轮图标按钮 + 下拉菜单，包含
 * 「设置」（跳转 /settings）与「退出登录」（二次确认后调用 useAuth().logout()）。
 * 退出确认复用 common/ConfirmDialog，文案与 SidebarNav 保持一致。
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, Settings2, UserCog } from 'lucide-react';
import { cn } from '../../utils/cn';
import { useAuth } from '../../hooks';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { ConfirmDialog } from '../common';

export const UserMenu = () => {
  const { authEnabled, logout } = useAuth();
  const { t } = useUiLanguage();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // 点击外部 / Esc 关闭
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const menuItemClass = cn(
    'flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-secondary-text transition-colors hover:bg-hover hover:text-foreground'
  );

  return (
    <div className="relative" ref={ref}>
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

      {open && (
        <div
          role="menu"
          aria-label={t('header.userSettings')}
          className="absolute right-0 top-[calc(100%+8px)] z-50 w-44 rounded-xl border border-border/80 bg-card p-1.5 shadow-lg"
        >
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
