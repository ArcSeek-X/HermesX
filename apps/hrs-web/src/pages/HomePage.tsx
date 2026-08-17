/**
 * @file HomePage.tsx
 * @description 系统首页
 * @module pages
 */
import React from 'react';
import { History } from 'lucide-react';
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
      <PageHeader
        eyebrow={t('layout.nav.review')}
        title={t('layout.route.review.title')}
        description={t('layout.route.review.description')}
      />
      <Card className="mt-4 flex min-h-[320px] flex-col items-center justify-center p-8 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <History className="h-6 w-6" />
        </div>
        <h2 className="mt-4 text-lg font-semibold text-foreground">{t('layout.route.review.title')}</h2>
        <p className="mt-2 max-w-md text-sm text-secondary-text">{t('layout.route.review.description')}</p>
      </Card>
    </AppPage>
  );
};

export default ReviewPage;
