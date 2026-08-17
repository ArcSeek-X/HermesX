/**
 * @file WatchlistPage.tsx
 * @description 自选页面：自选股列表与行情跟踪（当前为占位实现，后续接入自选股数据）
 * @module pages
 */

import type React from 'react';
import { Star } from 'lucide-react';
import { AppPage, Card, EmptyState, PageHeader } from '../components';
import { useUiLanguage } from '../contexts/UiLanguageContext';

/**
 * 自选页面组件
 * 展示用户自选股列表与行情跟踪
 */
const WatchlistPage: React.FC = () => {
  const { t } = useUiLanguage();

  return (
    <AppPage className="space-y-5">
      {/* ===== 页面标题区 ===== */}
      <PageHeader
        eyebrow="Watchlist"
        title={t('layout.route.watchlist.title')}
        description={t('layout.route.watchlist.description')}
      />

      {/* ===== 内容区（占位） ===== */}
      <Card title={t('layout.route.watchlist.title')} variant="bordered" padding="md">
        <EmptyState
          icon={<Star className="h-6 w-6" />}
          title={t('layout.route.watchlist.title')}
          description={t('layout.route.watchlist.description')}
        />
      </Card>
    </AppPage>
  );
};

export default WatchlistPage;
