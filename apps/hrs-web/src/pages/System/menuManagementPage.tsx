/**
 * 菜单管理页：当前仅提供页面骨架与标题，后续在此接入菜单树与维护能力。
 */

import React from 'react';
import { AppPage } from '@components/layout/AppPage';
import { PageHeader } from '@components/layout/PageLayout/PageHeader';
import { useUiLanguage } from '../../contexts/UiLanguageContext';

const MenuManagementPage: React.FC = () => {
  const { t } = useUiLanguage();

  return (
    <AppPage>
      <PageHeader
        title={t('layout.nav.menuManagement.title')}
        description={t('layout.nav.menuManagement.description')}
      />
    </AppPage>
  );
};

export default MenuManagementPage;
