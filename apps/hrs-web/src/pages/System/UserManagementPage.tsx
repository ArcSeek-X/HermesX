/**
 * 用户管理页：当前仅提供页面骨架与标题，后续在此接入用户列表与维护能力。
 */

import React from 'react';
import { AppPage } from '@components/layout/AppPage';
import { PageHeader } from '@components/layout/PageLayout/PageHeader';
import { useUiLanguage } from '../../contexts/UiLanguageContext';

const UserManagementPage: React.FC = () => {
  const { t } = useUiLanguage();

  return (
    <AppPage>
      <PageHeader
        title={t('layout.nav.userManagement.title')}
        description={t('layout.nav.userManagement.description')}
      />
    </AppPage>
  );
};

export default UserManagementPage;
