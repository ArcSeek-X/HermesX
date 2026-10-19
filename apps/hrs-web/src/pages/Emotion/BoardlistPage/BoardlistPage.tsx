/**
 * @file Emotion/BoardlistPage/BoardlistPage.tsx
 * @description 涨跌榜页面：涨停 / 跌停两个 TAB，各自独立面板（指标卡 + 明细表）。
 *   当前 TAB 经 useCachedState 持久化到 localStorage，刷新后保持。
 */

import type React from 'react';
import { TabNav } from '@components';
import { AppPage } from '@components/layout/AppPage';
import { PageHeader } from '@components/layout/PageLayout/PageHeader';
import { useCachedState } from '../../../hooks/useCachedState';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { LimitUpBoardPanel } from './components/LimitUpBoardPanel';
import { LimitDownBoardPanel } from './components/LimitDownBoardPanel';

/** 涨跌榜 TAB：涨停榜单 / 跌停榜单 */
type BoardTab = 'limit-up' | 'limit-down';

/** 涨跌榜 TAB 配置（顺序即展示顺序），labelKey 指向 emotion.board.* */
const BOARD_TABS: { value: BoardTab; labelKey: 'emotion.board.limitUp' | 'emotion.board.limitDown' }[] = [
  { value: 'limit-up', labelKey: 'emotion.board.limitUp' },
  { value: 'limit-down', labelKey: 'emotion.board.limitDown' },
];

/** 涨跌榜主页面：标题 + TAB 切换 + 涨跌停榜单面板 */
const BoardlistPage: React.FC = () => {
  const { t } = useUiLanguage();

  /** 当前激活的涨跌榜 TAB（localStorage 持久化用户偏好） */
  const [boardTab, setBoardTab] = useCachedState<BoardTab>(
    'emotion.boardTab',
    'limit-up',
    { storage: 'local' }
  );

  return (
    // fill：本页需要「页头 + TAB + 指标卡 + 表格」贴底适配，转 flex 列让面板以 flex-1 填充剩余高度
    <AppPage fill>
      <div className="flex flex-1 min-h-0 flex-col gap-3">
        <PageHeader title={t('layout.nav.boardlist.title')} description={t('layout.nav.boardlist.description')} />
        <TabNav<BoardTab>
          ariaLabel={t('emotion.board.switch')}
          variant="secondary"
          items={BOARD_TABS.map(({ value, labelKey }) => ({ value, label: t(labelKey) }))}
          value={boardTab}
          onChange={setBoardTab}
        />
        {boardTab === 'limit-up' ? <LimitUpBoardPanel /> : <LimitDownBoardPanel />}
      </div>
    </AppPage>
  );
};

export default BoardlistPage;
