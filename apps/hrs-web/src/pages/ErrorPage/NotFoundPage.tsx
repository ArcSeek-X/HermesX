/**
 * @file NotFoundPage.tsx
 * @description 404 页面未找到页面，在用户访问不存在的路由时展示提示信息及返回首页入口
 * @module pages
 */
import type React from 'react';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { useAuth } from '../../hooks';
import { Home, LogIn } from 'lucide-react';
import { HrsButton } from '@components';
/**
 * 404 页面未找到组件
 * 当用户访问的 URL 不匹配任何已注册路由时，渲染该页面，展示 404 提示并提供返回首页按钮
 * @returns 404 页面的 JSX 元素
 */
const NotFoundPage: React.FC = () => {
  /** 路由导航函数，用于编程式跳转 */
  const navigate = useNavigate();
  const { logout } = useAuth();
  const { t } = useUiLanguage();

  // 设置页面标题：走 i18n 字典，禁止硬编码用户可见文案（见 I18N_NAMING 总则第 1 条）
  useEffect(() => {
    document.title = t('notFound.documentTitle');
  }, [t]);

  // 重新登录：先登出当前会话（清登录态），再回到登录页重建动态路由
  const handleRelogin = async () => {
    try {
      await logout();
    } finally {
      navigate('/login', { replace: true });
    }
  };

  return (
    <div className=" h-full flex flex-col items-center justify-center text-center px-4 pb-20">
      {/* ===== 404 标识区 ===== */}
      <div className="relative mb-3">
        <span className="bg-gradient-to-b from-[var(--color-cyan)] to-[var(--color-purple)] bg-clip-text text-10xl font-bold text-transparent">
          404
        </span>
      </div>

      {/* ===== 提示文案区 ===== */}
      <h1 className="text-2xl font-bold text-foreground mb-2">{t('notFound.title')}</h1>
      <p className="text-muted-text mb-8">{t('notFound.description')}</p>

      {/* ===== 操作按钮区：返回首页 / 重新登录 ===== */}
      <div className="flex items-center gap-3">
        <HrsButton variant="primary" size="md" onClick={() => navigate('/home')}>
          {/* 主页图标（lucide-react 统一图标库）*/}
          <Home className="w-4 h-4 mr-1" />
          {t('notFound.backHome')}
        </HrsButton>
        <HrsButton variant="secondary" size="md" onClick={handleRelogin}>
          <LogIn className="w-4 h-4 mr-1" />
          {t('notFound.relogin')}
        </HrsButton>
         <HrsButton variant="primary" size="md" onClick={() => navigate('/home123123')}>
          {/* 主页图标（lucide-react 统一图标库）*/}
          <Home className="w-4 h-4 mr-1" />
          测试
        </HrsButton>
      </div>
    </div>
  );
};

export default NotFoundPage;
