/**
 * @file ScannerPage.tsx
 * @description 扫描页面（ScannerPage）
 *   当前为占位骨架：仅承载页面标题区，后续在此扩展扫描能力。
 * @module pages
 */

import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { PageHeader } from '@components/page-layout';

const ScannerPage: React.FC = () => {
  const { t } = useUiLanguage();
  return (
    <div className="mx-auto w-full space-y-3">
      <PageHeader
        title={t('layout.nav.scanner.title')}
        description={t('layout.nav.scanner.description')}
      />
    </div>
  );
};

export default ScannerPage;
