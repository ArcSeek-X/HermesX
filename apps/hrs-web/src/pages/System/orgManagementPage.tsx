/**
 * 组织管理页：当前仅提供页面骨架与标题，后续在此接入组织列表与维护能力。
 */

import React from 'react';
import { AppPage } from '@components/layout/AppPage';
import { PageHeader } from '@components/layout/PageLayout/PageHeader';
import { useUiLanguage } from '../../contexts/UiLanguageContext';

const OrgManagementPage: React.FC = () => {
  const { t } = useUiLanguage();

  return (
    <AppPage>
      <PageHeader
        title={t('layout.nav.orgManagement.title')}
        description={t('layout.nav.orgManagement.description')}
      />
    </AppPage>
  );
};

export default OrgManagementPage;
