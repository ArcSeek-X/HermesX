/**
 * BackToHome
 *
 * 头部「回到主页」图标按钮：点击跳转 /home。
 * 样式与 LanguageMenu 等头部小按钮保持一致（h-9 w-9 / rounded-[10px] / bg-card/80 / shadow-soft-card / select-none）。
 *
 * @author Lensgcx (GaoCangxiong)
 */
import { Home } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';

export const BackToHome = () => {
  const { t } = useUiLanguage();
  const navigate = useNavigate();
  return (
    <button
      type="button"
      onClick={() => navigate('/home')}
      className="inline-flex h-9 w-9 select-none items-center justify-center rounded-[10px] border border-border/70 bg-card/80 text-secondary-text shadow-soft-card transition-colors hover:bg-hover hover:text-foreground"
      aria-label={t('layout.header.goHome')}
      title={t('layout.header.goHome')}
    >
      <Home className="h-4 w-4" />
    </button>
  );
};
