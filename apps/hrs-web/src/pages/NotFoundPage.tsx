/**
 * @file NotFoundPage.tsx
 * @description 404 页面未找到页面，在用户访问不存在的路由时展示提示信息及返回首页入口
 * @module pages
 */
import type React from 'react';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * 404 页面未找到组件
 * 当用户访问的 URL 不匹配任何已注册路由时，渲染该页面，展示 404 提示并提供返回首页按钮
 * @returns 404 页面的 JSX 元素
 */
const NotFoundPage: React.FC = () => {
  /** 路由导航函数，用于编程式跳转 */
  const navigate = useNavigate();

  // 设置页面标题
  useEffect(() => {
    document.title = '页面未找到 - HRS';
  }, []);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center text-center px-4">
      {/* ===== 404 标识区 ===== */}
      <div className="relative mb-8">
        {/* 渐变文字效果：青色到紫色的 135 度线性渐变 */}
        <span
          className="text-8xl font-bold text-transparent bg-clip-text"
          style={{
            backgroundImage: 'linear-gradient(135deg, #00d4ff 0%, #a855f7 100%)',
          }}
        >
          404
        </span>
      </div>

      {/* ===== 提示文案区 ===== */}
      <h1 className="text-2xl font-bold text-foreground mb-2">页面未找到</h1>
      <p className="text-muted-text mb-8">抱歉，您访问的页面不存在或已被移动</p>

      {/* ===== 操作按钮区：返回首页 ===== */}
      <button
        type="button"
        className="btn-primary flex items-center gap-2"
        onClick={() => navigate('/home')}
      >
        {/* 主页图标 SVG */}
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
        返回首页
      </button>
    </div>
  );
};

export default NotFoundPage;
