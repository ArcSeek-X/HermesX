/**
 * @file HomePage.tsx
 * @description 系统首页
 * @module pages
 */
import React from 'react';
import { AppPage, Card, PageHeader } from '../components';
import { useUiLanguage } from '../contexts/UiLanguageContext';

/**
 * 复盘页面组件
 *
 * 复盘工作台骨架：后续在此扩展历史复盘记录、大盘回顾等能力。
 * 当前提供统一页面容器、标题区与占位内容，保证路由 /review 可访问且视觉与全站一致。
 */
const ReviewPage: React.FC = () => {
  const { t } = useUiLanguage();

  return (
    <AppPage>
     首页
    </AppPage>
  );
};

export default ReviewPage;
