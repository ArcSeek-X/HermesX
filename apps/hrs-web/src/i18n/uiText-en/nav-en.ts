/**
 * 英文（en）文案：nav 命名空间。
 * 由 uiText-en.ts 按 uiText-zh/ 分片结构拆分，经 uiText-en/index.ts 聚合；key 与中文分片逐一对齐。
 */

export const navEn = {
  'layout.nav.alerts.title': 'Alerts',
  'layout.nav.alerts.description': 'Rules, triggers, and notification attempts',
  'layout.nav.backtest.title': 'Backtest',
  'layout.nav.backtest.description': 'Backtest jobs and result review',
  'layout.nav.chat.title': 'Ask',
  'layout.nav.chat.description': 'Multi-turn strategy Q&A and sessions',
  'layout.nav.codeTest.title': 'Test',
  'layout.nav.codeTest.description': 'Component showcase and integration test page',
  'layout.nav.index.title': 'Overview',
  'layout.nav.index.description': 'A-shares, HK, US, and Japan/Korea market overview and key indicators',
  'layout.nav.market.title': 'Markets',
  'layout.nav.market.description': 'Market quotes, index overview, and sector analysis',
  'layout.nav.emotion.title': 'Sentiment',
  'layout.nav.emotion.description': 'Market sentiment and gainers/losers boards',
  'layout.nav.boardlist.title': 'Gainers & Losers',
  'layout.nav.boardlist.description': 'Limit-up and limit-down boards overview',
  'emotion.board.limitUp': 'Limit-Up Board',
  'emotion.board.limitDown': 'Limit-Down Board',
  'emotion.board.switch': 'Board switch',
  'emotion.board.col.code': 'Code',
  'emotion.board.col.name': 'Name',
  'emotion.board.col.price': 'Price',
  'emotion.board.col.changePercent': 'Change %',
  'emotion.board.col.limitTime': 'Limit Time',
  'emotion.board.col.boards': 'Boards',
  'emotion.board.col.sealAmount': 'Seal (亿)',
  'emotion.board.col.amount': 'Turnover (亿)',
  'emotion.board.col.turnoverRate': 'Turnover Rate',
  'emotion.board.col.industry': 'Industry',
  'emotion.board.col.limitDownTime': 'Limit-Down Time',
  'emotion.board.kpi.limitUpCount': 'Limit-Ups', // Limit-up board KPI: limit-up count
  'emotion.board.kpi.maxBoards': 'Max Boards', // Limit-up board KPI: highest consecutive boards
  'emotion.board.kpi.sealAmount': 'Seal Orders', // Limit-up board KPI: total seal amount
  'emotion.board.kpi.breakRate': 'Break Rate', // Limit-up board KPI: broken-board rate (pending data)
  'emotion.board.kpi.previousPremium': 'Prev. Day Premium', // Limit-up board KPI: previous-day premium (pending data)
  'emotion.board.kpi.limitDownCount': 'Limit-Downs', // Limit-down board KPI: limit-down count
  'emotion.board.kpi.maxDownBoards': 'Max Down Boards', // Limit-down board KPI: highest consecutive down boards
  'emotion.board.kpi.downSealAmount': 'Down Seal Orders', // Limit-down board KPI: total seal amount
  'emotion.board.kpi.downTurnoverAmount': 'Down Turnover', // Limit-down board KPI: total turnover of limit-down stocks
  'emotion.board.kpi.avgTurnoverRate': 'Avg Turnover Rate', // Limit-down board KPI: average turnover rate
  'emotion.board.kpi.liquidityNote': 'Liquidity ref.', // Limit-down board KPI: avg turnover rate note
  'emotion.board.kpi.boardsValue': '{count} boards', // Limit board KPI: max boards value
  'emotion.board.kpi.prevDayDelta': '{delta} vs prev. day', // Limit board KPI: change vs previous trading day
  'emotion.board.kpi.topBoardStock': 'Top: {name}', // Limit board KPI: highest-board stock name
  'emotion.board.kpi.sealRatio': '{ratio} of turnover', // Limit board KPI: seal amount as share of turnover
  'emotion.board.openKline': 'View K-line', // Limit board: code/name column click hint to jump to K-line
  'layout.nav.stock.title': 'Stocks',
  'layout.nav.stock.description': 'Individual stock quotes, K-line, and multi-period analysis',
  'dashboard.tab.a': 'A-Shares', // Dashboard market TAB: A-Shares
  'dashboard.tab.hkUs': 'HK & US', // Dashboard market TAB: HK & US
  'dashboard.tab.jpKr': 'Japan & Korea', // Dashboard market TAB: Japan & Korea
  'dashboard.marketSwitch': 'Market switch', // Dashboard market TAB switch aria label
  'layout.nav.decisionSignals.title': 'AI signals',
  'layout.nav.decisionSignals.description': 'AI recommendations, risks, and watch conditions',
  'layout.nav.home.title': 'Home',
  'layout.nav.home.description': 'Stock analysis and report workspace',
  'layout.nav.kline.title': 'K-Line',
  'layout.nav.kline.description': 'Stock K-line trends, technical indicators, and multi-period analysis',
  'layout.nav.stockMetricView.title': 'Stock Metric View',
  'layout.nav.stockMetricView.description': 'Browse market-wide stock metrics with filtering, sorting, and CSV export',
  'layout.nav.liveCalendar.title': 'Calendar',
  'layout.nav.liveCalendar.description': 'Calendar of macro, earnings, IPO, and event items',
  'layout.nav.liveNews.title': 'Newsflash',
  'layout.nav.liveNews.description': '24/7 financial newsflash with channel and importance filters',
  'layout.nav.news.title': 'News', // News top-level group
  'layout.nav.news.description': 'Market news & financial calendar', // News top-level group description
  'layout.nav.choose.title': 'Stock Picking',
  'layout.nav.choose.description': 'AI chat-based stock picking and smart decision signals',
  'layout.nav.trading.title': 'Trading',
  'layout.nav.trading.description': 'Portfolio positions and trade management',
  'layout.nav.portfolio.title': 'Portfolio',
  'layout.nav.portfolio.description': 'Portfolio snapshots, manual entries, and risk analysis',
  'layout.nav.review.title': 'Review',
  'layout.nav.review.description': 'Historical reviews and market recap',
  'layout.nav.screening.title': 'Screening',
  'layout.nav.screening.description': 'AlphaSift strategy screening and candidate research',
  'layout.nav.sectorAnalysis.title': 'Sector',
  'layout.nav.sectorAnalysis.description': 'Sector performance, capital flow, and hotspot tracking',
  'layout.nav.settings.title': 'Settings',
  'layout.nav.settings.description': 'System config, models, and authentication',
  'layout.nav.stockCloud.title': 'Stock Cloud',
  'layout.nav.stockCloud.description': 'Stock cloud map and sector distribution visualization',
  'layout.nav.usage.title': 'Usage',
  'layout.nav.usage.description': 'LLM token consumption and model call details',
  'layout.nav.watchlist.title': 'Watchlist',
  'layout.nav.watchlist.description': 'Watchlist stocks and market tracking',
  'layout.nav.discover.title': 'Discover',
  'layout.nav.discover.description': 'Stock selection and scanning',
  'layout.nav.eodPicker.title': 'EOD Picker',
  'layout.nav.eodPicker.description': 'One-day holding analysis tool · screen intraday strong stocks',
  'layout.nav.scanner.title': 'Scanner',
  'layout.nav.scanner.description': 'Technical signal scanner with unified concurrency control and cancellation',
  'layout.nav.userManagement.title': 'Users',
  'layout.nav.userManagement.description': 'Manage system users and account information',
  'layout.nav.orgManagement.title': 'Organizations',
  'layout.nav.orgManagement.description': 'Manage departments and organization hierarchy',
  'layout.nav.menuManagement.title': 'Menus',
  'layout.nav.menuManagement.description': 'Maintain system menus and page entries',
  'layout.nav.development.docsCheckbox.title': 'Checkbox',
  'layout.nav.development.docsCheckbox.description': 'HrsCheckbox component demo and usage',
  'layout.nav.development.docsDrawer.title': 'Drawer',
  'layout.nav.development.docsDrawer.description': 'HrsDrawer side drawer component demo and usage',
  'layout.nav.development.docsButton.title': 'Button',
  'layout.nav.development.docsButton.description': 'HrsButton button component demo and usage',
  'layout.nav.development.docsSelect.title': 'Select',
  'layout.nav.development.docsSelect.description': 'HrsSelect dropdown select component demo and usage',
  'layout.nav.development.docsSeparator.title': 'Separator',
  'layout.nav.development.docsSeparator.description': 'Separator divider component demo and usage',
  'layout.nav.development.docsTable.title': 'Table',
  'layout.nav.development.docsTable.description': 'Table data table component demo and usage',
  'layout.nav.development.docsToast.title': 'Toast',
  'layout.nav.development.docsToast.description': 'Toast command-style toast component demo and usage',
  'layout.nav.development.docsInlineToast.title': 'Inline Toast',
  'layout.nav.development.docsInlineToast.description': 'InlineToast inline toast component demo and usage',
  'layout.nav.development.docsModal.title': 'Modal',
  'layout.nav.development.docsModal.description': 'Modal dialog component demo and usage',
  'layout.nav.development.docsAnimCard.title': 'Anim Card',
  'layout.nav.development.docsAnimCard.description': 'AnimCard animated card component demo and usage',
  'layout.nav.development.docsNewsCard.title': 'News Card',
  'layout.nav.development.docsNewsCard.description': 'NewsCard live news card component demo and usage',
  'layout.nav.development.docsListCard.title': 'List Card',
  'layout.nav.development.docsListCard.description': 'ListCard list card component demo and usage',
  'layout.nav.development.docsTabNav.title': 'Tabs',
  'layout.nav.development.docsTabNav.description': 'TabNav tabs navigation component demo and usage',
  'layout.nav.development.docsSideBar.title': 'Sidebar',
  'layout.nav.development.docsSideBar.description': 'SidebarNav sidebar navigation component demo and usage',
  'layout.nav.development.docsInput.title': 'Input',
  'layout.nav.development.docsInput.description': 'Input form input component demo and usage',
  'layout.nav.development.docsTextArea.title': 'Text Area',
  'layout.nav.development.docsTextArea.description': 'TextArea multiline text input component demo and usage',
  'layout.nav.development.docsNumberField.title': 'Number Field',
  'layout.nav.development.docsNumberField.description': 'NumberField numeric input component demo and usage',
  'layout.nav.development.docsCountryMarketSelect.title': 'Country / Market Select',
  'layout.nav.development.docsCountryMarketSelect.description': 'CountryMarketSelect single & multiple country/market dropdown component demo and usage',
  'layout.nav.development.docsChip.title': 'Chip',
  'layout.nav.development.docsChip.description': 'Chip rounded capsule tag component demo and usage',
  'layout.nav.development.docsEmptyState.title': 'Empty State',
  'layout.nav.development.docsEmptyState.description': 'EmptyState empty-state component demo and usage',
} as const;
