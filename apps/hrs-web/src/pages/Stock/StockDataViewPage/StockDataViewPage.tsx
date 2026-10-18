/**
 * @file Stock/StockDataViewPage/StockDataViewPage.tsx
 * @description 股票数据视图页面：仅承载页面标题区。
 * 原行情头 / K 线图 / 周期与复权切换等功能内容已下线，相关能力由个股 K 线页提供。
 * @module pages
 * @author Lensgcx (GaoCangxiong)
 */
import type React from 'react';
import { useEffect } from 'react';
import { AppPage } from '@components/layout/AppPage';
import { PageHeader } from '@components/layout/PageLayout/PageHeader';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';

const StockDataViewPage: React.FC = () => {
  const { t } = useUiLanguage();

  useEffect(() => {
    document.title = t('layout.nav.stockDataView.title');
  }, [t]);

  return (
    <AppPage>
      <PageHeader
        title={t('layout.nav.stockDataView.title')}
        description={t('layout.nav.stockDataView.description')}
      />
    </AppPage>
  );
};

export default StockDataViewPage;
