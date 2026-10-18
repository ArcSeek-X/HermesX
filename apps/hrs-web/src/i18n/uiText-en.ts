/**
 * @file uiText-en.ts
 * @description 英文（en）界面文案配置，镜像 zh 的键值
 * @module i18n
 */

import type { UiTextKey } from './uiText-zh';


const en: Record<UiTextKey, string> = {

  // ---- 第 1 类 全局 common ----
  'common.cancel': 'Cancel',
  'common.clear': 'Clear',
  'common.close': 'Close',
  'common.closeDrawer': 'Close drawer',
  'common.confirm': 'OK',
  'common.copied': 'Copied!',
  'common.copy': 'Copy',
  'common.datetime.day': 'Day', // Calendar view granularity: day
  'common.datetime.list': 'List', // Calendar view granularity: list
  'common.datetime.month': 'Month', // Calendar view granularity: month
  'common.datetime.today': 'Today', // Calendar back-to-today button
  'common.datetime.week': 'Week', // Calendar view granularity: week
  'common.delete': 'Delete',
  'common.deleting': 'Deleting',
  'common.details': 'View details',
  'common.disabled': 'Disabled',
  'common.enabled': 'Enabled',
  'common.failure': 'Failed',
  'common.hideContent': 'Hide content',
  'common.itemsCount': '{count}',
  'common.loading': 'Loading',
  'common.noData': 'No data',
  'common.processing': 'Processing...',
  'common.readOnly': 'Read-only',
  'common.retry': 'Retry',
  'common.selectAllCurrent': 'Select current',
  'common.selectPlaceholder': 'Select',
  'common.selectedCount': '{count} selected',
  'common.sensitive': 'Sensitive',
  'common.showContent': 'Show content',
  'common.success': 'Success',

  // ---- 第 2 类 语言 language ----
  'language.chineseSimplified': 'Simplified Chinese',
  'language.chineseTraditional': 'Traditional Chinese',
  'language.english': 'English',
  'language.short.en': 'EN',
  'language.short.zh': '中',
  'language.short.zhHant': '繁',
  'language.toggle': 'Switch UI language',

  // ---- 第 3 类 主题 theme ----
  'theme.themeMode.dark': 'Dark',
  'theme.themeMode.light': 'Light',
  'theme.themeMode.settingTitle': 'Theme mode',
  'theme.themeColor.settingTitle': 'Primary color',
  'theme.reset': 'Reset',
  'theme.save': 'Save',
  'theme.themeMode.system': 'System',
  'theme.sidebarTheme.settingTitle': 'Sidebar style',
  'theme.sidebarTheme.pill': 'Rounded (pill)',
  'theme.sidebarTheme.square': 'Square',

  // ---- 第 4 类 布局与菜单 layout ----
  // 布局直属 layout.*
  'layout.appFallbackDescription': 'Web workspace',
  'layout.appFallbackTitle': 'HermesX',
  'layout.collapseSidebar': 'Collapse sidebar',
  'layout.desktopSidebar': 'Desktop sidebar navigation',
  'layout.expandSidebar': 'Expand sidebar',
  'layout.logout': 'Log out',
  'layout.logoutConfirm': 'Log out',
  'layout.logoutMessage': 'Confirm logging out of the current session? After logging out, you will need to re-enter your password to log in.',
  'layout.logoutTitle': 'Log out',
  'layout.mainNav': 'Main navigation',
  'layout.newChatMessage': 'New Ask update',
  'layout.openNav': 'Open navigation',
  // 头部操作区 layout.header.*
  'layout.header.goHome': 'Go home',
  'layout.header.language': 'UI language',
  'layout.header.myApps': 'My apps',
  'layout.header.themeSettings': 'Theme settings',
  'layout.header.userSettings': 'User settings',
  'layout.header.fullscreen': 'Full screen',
  'layout.header.exitFullscreen': 'Exit full screen',
  // 导航菜单 layout.nav.*
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
  'layout.nav.stockDataView.title': 'Stock Data View',
  'layout.nav.stockDataView.description': 'Inspect individual stock quotes, K-line, and multi-period data view',
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
  'layout.nav.development.docsChip.title': 'Chip',
  'layout.nav.development.docsChip.description': 'Chip rounded capsule tag component demo and usage',
  'layout.nav.development.docsEmptyState.title': 'Empty State',
  'layout.nav.development.docsEmptyState.description': 'EmptyState empty-state component demo and usage',

  // ---- 第 5 类 组件 component ----
  // component.LiveCalendar.*
  'component.LiveCalendar.allDay': 'All day', // calendar event all-day marker
  'component.LiveCalendar.calendarType.FD': 'Economic Data', // event type: economic indicator
  'component.LiveCalendar.calendarType.FE': 'Event', // event type: financial event
  'component.LiveCalendar.country': 'Country', // List view column header: country
  'component.LiveCalendar.drawer.actual': 'Actual', // detail drawer: actual value
  'component.LiveCalendar.drawer.forecast': 'Forecast', // detail drawer: forecast value
  'component.LiveCalendar.drawer.previous': 'Previous', // detail drawer: previous value
  'component.LiveCalendar.drawer.source': 'Source', // detail drawer: source
  'component.LiveCalendar.drawer.sourceName': 'Wallstreetcn', // detail drawer: data source name (link text)
  'component.LiveCalendar.drawer.noSummary': 'No details available', // detail drawer: placeholder when event has no summary/foresight
  'component.LiveCalendar.empty': 'No calendar events this month', // empty: no events this month
  'component.LiveCalendar.emptyImportance': 'No events matching the importance filter, try lowering it', // empty: importance filter has no results
  'component.LiveCalendar.filter.apply': 'Apply', // filter panel: apply button
  'component.LiveCalendar.filter.button': 'Filter', // filter toggle button
  'component.LiveCalendar.filter.country': 'Country/Region', // filter panel: country / region
  'component.LiveCalendar.filter.country.all': 'All countries/regions', // filter panel: "all" option of country select
  'component.LiveCalendar.filter.importance': 'Importance', // filter panel: multi-select importance
  'component.LiveCalendar.filter.importance.none': 'None', // filter panel: importance 0 (source provides no level)
  'component.LiveCalendar.filter.keyword': 'Keyword', // filter panel: title keyword
  'component.LiveCalendar.filter.keywordPlaceholder': 'Search news title', // filter panel: keyword input placeholder
  'component.LiveCalendar.filter.reset': 'Reset', // filter panel: reset button
  'component.LiveCalendar.filter.type': 'Type', // filter panel: event type tri-state
  'component.LiveCalendar.filter.type.all': 'All', // filter panel: event type "all"
  'component.LiveCalendar.importance': 'Importance', // List view column header: importance
  'component.LiveCalendar.includeEconomicData': 'Show economic data', // toggle: show FD economic data
  'component.LiveCalendar.list.columns.time': 'Time', // List view column header: time
  'component.LiveCalendar.list.columns.title': 'Title', // List view column header: news title
  'component.LiveCalendar.loading': 'Loading…', // loading copy during internal month navigation
  'component.LiveCalendar.more': 'More info', // calendar cell overflow "+N" label
  'component.LiveCalendar.nextMonth': 'Next month', // List view nav: next
  'component.LiveCalendar.prevMonth': 'Previous month', // List view nav: previous
  'component.LiveCalendar.today': 'Today', // month switch: back to today
  // component.runFlow.*
  'component.runFlow.drawerTitle': 'Run Flow',
  'component.runFlow.durationMinutes': '{value} min',
  'component.runFlow.durationMs': '{value} ms',
  'component.runFlow.durationSeconds': '{value} sec',
  'component.runFlow.edge.control': 'Control',
  'component.runFlow.edge.data': 'Data',
  'component.runFlow.edge.fallback': 'Fallback',
  'component.runFlow.edge.retry': 'Retry',
  'component.runFlow.edgeLabel.details': 'Details',
  'component.runFlow.edgeLabel.invoke': 'Invoke',
  'component.runFlow.emptyDescription': 'Select an active task or historical report to inspect its run flow.',
  'component.runFlow.emptySnapshotDescription': 'This snapshot has no nodes or events; missing diagnostics show as a skeleton or empty state.',
  'component.runFlow.emptySnapshotTitle': 'No run-flow details yet',
  'component.runFlow.emptyTitle': 'No run flow',
  'component.runFlow.errorTitle': 'Run flow failed to load',
  'component.runFlow.events.count': '{count} events',
  'component.runFlow.events.empty': 'No events match this filter.',
  'component.runFlow.events.filter.all': 'All',
  'component.runFlow.events.filter.cancelled': 'Cancel',
  'component.runFlow.events.filter.fallback': 'Fallback/retry',
  'component.runFlow.events.filter.important': 'Key',
  'component.runFlow.events.filter.problems': 'Failures/warnings',
  'component.runFlow.events.filters': 'Event filters',
  'component.runFlow.events.openNode': 'View node linked to event {title}',
  'component.runFlow.events.title': 'Event stream',
  'component.runFlow.eyebrow': 'RUN FLOW',
  'component.runFlow.graph.collapse': 'Collapse',
  'component.runFlow.graph.collapseNode': 'Collapse {label} attempts',
  'component.runFlow.graph.description': 'Auto-layered lanes show entry, data sources, analysis engines, and artifact paths.',
  'component.runFlow.graph.expand': 'Expand',
  'component.runFlow.graph.expandNode': 'Expand {label} attempts',
  'component.runFlow.graph.nodeAria': '{label} node, status {status}',
  'component.runFlow.graph.startedAt': 'Start',
  'component.runFlow.graph.title': 'Run topology',
  'component.runFlow.historyDrawerTitle': '{stock} history run flow',
  'component.runFlow.loadingDescription': 'Reading the task snapshot, run diagnostics, and event path.',
  'component.runFlow.loadingTitle': 'Loading run flow',
  'component.runFlow.nodeDetails.attemptList': 'Run attempts',
  'component.runFlow.nodeDetails.attempts': 'Attempts',
  'component.runFlow.nodeDetails.blockScores': 'Block scores',
  'component.runFlow.nodeDetails.close': 'Close node details',
  'component.runFlow.nodeDetails.collapseAttempts': 'Collapse attempts',
  'component.runFlow.nodeDetails.column.duration': 'Duration',
  'component.runFlow.nodeDetails.column.name': 'Name',
  'component.runFlow.nodeDetails.column.records': 'Records',
  'component.runFlow.nodeDetails.column.status': 'Status',
  'component.runFlow.nodeDetails.column.time': 'Time',
  'component.runFlow.nodeDetails.contextBlocks': 'Context inputs',
  'component.runFlow.nodeDetails.contextQuality': 'Context quality',
  'component.runFlow.nodeDetails.count.available': 'Available',
  'component.runFlow.nodeDetails.count.degraded': 'Degraded',
  'component.runFlow.nodeDetails.count.fallback': 'Fallback',
  'component.runFlow.nodeDetails.count.missing': 'Missing',
  'component.runFlow.nodeDetails.count.partial': 'Partial',
  'component.runFlow.nodeDetails.count.skipped': 'Skipped',
  'component.runFlow.nodeDetails.duration': 'Duration',
  'component.runFlow.nodeDetails.empty': 'Select a node to inspect details.',
  'component.runFlow.nodeDetails.endedAt': 'Ended',
  'component.runFlow.nodeDetails.expandAttempts': 'Expand attempts',
  'component.runFlow.nodeDetails.kind': 'Kind',
  'component.runFlow.nodeDetails.metadata': 'Metadata',
  'component.runFlow.nodeDetails.overallScore': 'Overall score',
  'component.runFlow.nodeDetails.provider': 'Provider',
  'component.runFlow.nodeDetails.qualityLevel': 'Level',
  'component.runFlow.nodeDetails.recordCount': 'Records',
  'component.runFlow.nodeDetails.startedAt': 'Started',
  'component.runFlow.nodeDetails.title': 'Node details',
  'component.runFlow.nodeDetails.version': 'Version',
  'component.runFlow.nodeKind.analysis': 'Analysis',
  'component.runFlow.nodeKind.artifact': 'Artifact',
  'component.runFlow.nodeKind.dataSource': 'Data source',
  'component.runFlow.nodeKind.entry': 'Entry',
  'component.runFlow.nodeKind.model': 'Model',
  'component.runFlow.nodeKind.notification': 'Notification',
  'component.runFlow.nodeKind.queue': 'Queue',
  'component.runFlow.open': 'View run flow',
  'component.runFlow.openHistoryAria': 'View run flow for history record {recordId}',
  'component.runFlow.refresh': 'Refresh',
  'component.runFlow.refreshing': 'Refreshing',
  'component.runFlow.retry': 'Reload',
  'component.runFlow.severity.danger': 'Danger',
  'component.runFlow.severity.info': 'Info',
  'component.runFlow.severity.success': 'Success',
  'component.runFlow.severity.warning': 'Warning',
  'component.runFlow.status.cancelRequested': 'Cancel requested',
  'component.runFlow.status.cancelled': 'Cancelled',
  'component.runFlow.status.degraded': 'Degraded',
  'component.runFlow.status.failed': 'Failed',
  'component.runFlow.status.fallback': 'Fallback',
  'component.runFlow.status.pending': 'Pending',
  'component.runFlow.status.running': 'Running',
  'component.runFlow.status.skipped': 'Skipped',
  'component.runFlow.status.success': 'Success',
  'component.runFlow.status.timeout': 'Timeout',
  'component.runFlow.status.unknown': 'Unknown',
  'component.runFlow.summary.dataSources': 'Data sources',
  'component.runFlow.summary.elapsed': 'Elapsed',
  'component.runFlow.summary.failedAttempts': 'Failed attempts',
  'component.runFlow.summary.fallbackCount': 'Fallback/retry',
  'component.runFlow.summary.generatedAt': 'Generated',
  'component.runFlow.summary.model': 'Model',
  'component.runFlow.summary.task': 'Task',
  'component.runFlow.summary.trace': 'Trace',
  'component.runFlow.taskDrawerTitle': '{stock} run flow',
  'component.runFlow.title': 'Data and information flow',
  'component.runFlow.valueUnavailable': 'Not recorded',
  // component.stockSearch.*
  'component.stockSearch.placeholder': 'Enter a stock code or name',
  // component.taskPanel.*
  'component.taskPanel.cancelRequested': 'Cancel requested',
  'component.taskPanel.cancelRequestedAria': 'Task cancel requested',
  'component.taskPanel.cancelled': 'Cancelled',
  'component.taskPanel.diagnostics': 'Diagnostics',
  'component.taskPanel.openRunFlow': 'View run flow',
  'component.taskPanel.openRunFlowAria': 'View {stock} run flow',
  'component.taskPanel.pending': 'Pending',
  'component.taskPanel.pendingAria': 'Task pending',
  'component.taskPanel.pendingTasks': '{count} pending',
  'component.taskPanel.processing': 'Processing',
  'component.taskPanel.processingAria': 'Task processing',
  'component.taskPanel.processingTasks': '{count} processing',
  'component.taskPanel.statusAria': 'Task status: {status}',
  'component.taskPanel.title': 'Analysis tasks',

  // ---- 第 6 类 异常页面  ----
  // 404页面/重定向页面
  'exception.404.title': '404', // 404 route title (route handle)
  'exception.404.description': '404 page not found', // 404 route description (route handle)
  'exception.redirect.title': 'Redirect', // redirect route title (route handle)
  'exception.redirect.description': 'Automatically redirected to the target page', // redirect route description (route handle)
  // exception.routeBoundary.*
  'exception.routeBoundary.backHome': 'Back home', // route error: back to home
  'exception.routeBoundary.backToLogin': 'Back to login', // route error: back to login
  'exception.routeBoundary.description': 'This page or component could not load. The network may be unavailable, or the system version may have changed. Reload the page or return to login and try again.', // route error description
  'exception.routeBoundary.details': 'View details', // route error: expand details
  'exception.routeBoundary.hideDetails': 'Hide details', // route error: collapse details
  'exception.routeBoundary.errorDetail': 'Error detail', // route error detail block title
  'exception.routeBoundary.copy': 'Copy', // copy error detail
  'exception.routeBoundary.copied': 'Copied', // error detail copied to clipboard
  'exception.routeBoundary.reload': 'Reload', // route error: reload
  'exception.routeBoundary.title': 'Page failed to load', // route error title

  // ---- 第 7 类 登录/注册 auth ----
  'auth.login.title': 'Login page',
  'auth.login.description': 'Admin login to access the quantitative decision workspace',
  'auth.login.adminLogin': 'Admin login',
  'auth.login.hidePassword': 'Hide password',
  'auth.login.loginDescription': 'A valid credential is required to access the HRS decision workspace.',
  'auth.login.loginFailed': 'Login failed',
  'auth.login.loginPassword': 'Password',
  'auth.login.loginPasswordPlaceholder': 'Enter password',
  'auth.login.loginSubmit': 'Enter workspace',
  'auth.login.loginSubmitting': 'Connecting...',
  'auth.login.pageTitle': 'Login - HRS',
  'auth.login.passwordMismatch': 'The two passwords do not match',
  'auth.login.passwordRequired': 'Please enter your password',
  'auth.login.showPassword': 'Show password',
  'auth.login.username': 'Account',
  'auth.login.usernamePlaceholder': 'Enter account',
  'auth.login.usernameRequired': 'Please enter your account',
  'auth.login.validationFailed': 'Validation failed',

  // ---- 第 8 类 页面 ----
  // alerts.*
  'alerts.pageTitle': 'Alerts - HRS', // 【页面】告警-Alert page document title
  'alerts.headerEyebrow': 'Alert Center', // 【页面】告警-Alert center header eyebrow
  'alerts.title': 'Alert Center', // 【页面】告警-Alert center page title
  'alerts.subtitle': 'Manage event alerts, daily technical indicators, watchlists, position/account linkage, and market traffic-light rules; run one-off tests, and review the trigger history recorded by background evaluation tasks.', // 【页面】告警-Alert center page subtitle
  // chat.*
  'chat.agentBackendUnavailableTitle': 'The selected ask-stock method is unavailable', // 【页面】问股-
  'chat.agentModeDisabled': 'Agent Mode is disabled. Open Agent settings, enable it, and save before trying again.', // 【页面】问股-
  'chat.agentPlatformUnsupported': 'Codex local Agent does not currently support native Windows. Use the default model, or run the HRS backend on a supported system.', // 【页面】问股-
  'chat.analysisStopped': 'This analysis has stopped and its background task has ended.', // 【页面】问股-
  'chat.analysisTimedOut': 'This analysis timed out and ended. Try again with a narrower question.', // 【页面】问股-
  'chat.codexBackendBadge': 'Codex Agent · Experimental', // 【页面】问股-
  'chat.codexChangeBackend': 'Change ask-stock method', // 【页面】问股-
  'chat.codexLimitedMessage': 'Codex can read saved analysis context and backtest summaries. Use Default model for live quotes, news, market hotspots, technical-indicator recalculation, per-stock backtest details, or portfolio queries.', // 【页面】问股-
  'chat.codexLimitedTitle': 'What Codex can use now', // 【页面】问股-
  'chat.codexUnavailableMessage': 'This device does not currently meet the basic Codex ask-stock requirements. Open Agent settings to check installation and Single Agent mode.', // 【页面】问股-
  'chat.defaultBackendBadge': 'Default model', // 【页面】问股-
  'chat.defaultUnavailableMessage': 'Default-model ask-stock is unavailable. Open Agent settings and review the model configuration.', // 【页面】问股-
  'chat.emptyDescriptionCodex': 'Enter “Analyze AAPL” or “How have past analyses performed overall?” and Codex will answer from saved analysis context and backtest summaries.', // 【页面】问股-
  'chat.emptyDescriptionDefault': 'Enter “Analyze AAPL” or “Is Apple a buy now?” and AI will use live data tools to build a decision report.', // 【页面】问股-
  'chat.introCodex': 'Ask Codex about a stock using saved analysis context and backtest summaries.', // 【页面】问股-
  'chat.introDefault': 'Ask AI about a stock for skill-guided trading suggestions and a live decision report.', // 【页面】问股-
  'chat.openAgentSettings': 'Open Agent settings', // 【页面】问股-
  'chat.recheckAgentStatus': 'Check again', // 【页面】问股-
  'chat.statusCheckingMessage': 'This checks only whether the environment allows an attempt; it does not call a model or read stock data.', // 【页面】问股-
  'chat.statusCheckingTitle': 'Checking the ask-stock runtime', // 【页面】问股-
  'chat.statusUnavailableMessage': 'The ask-stock runtime cannot be confirmed, so sending is paused. You can check again manually; your question will be preserved.', // 【页面】问股-
  'chat.statusUnavailableTitle': 'Ask-stock status is temporarily unavailable', // 【页面】问股-
  'chat.stopAnalysis': 'Stop analysis', // 【页面】问股-
  'chat.stopRequestFailed': 'The stop request was not delivered, so analysis is still running. Try stopping again.', // 【页面】问股-
  'chat.stoppingAnalysis': 'Stopping…', // 【页面】问股-
  // decisionSignals.*
  'decisionSignals.action': 'Action', // 【页面】AI建议-
  'decisionSignals.active': 'Active', // 【页面】AI建议-
  'decisionSignals.activeOnly': 'Active signals are shown by default', // 【页面】AI建议-
  'decisionSignals.allActions': 'All actions', // 【页面】AI建议-
  'decisionSignals.allMarkets': 'All markets', // 【页面】AI建议-
  'decisionSignals.allPhases': 'All phases', // 【页面】AI建议-
  'decisionSignals.allProfiles': 'All profiles', // 【页面】AI建议-
  'decisionSignals.allSources': 'All sources', // 【页面】AI建议-
  'decisionSignals.allStatuses': 'All statuses', // 【页面】AI建议-
  'decisionSignals.archive': 'Archive', // 【页面】AI建议-
  'decisionSignals.archiveConfirm': 'Archive this signal? Archived signals are no longer shown as current active recommendations.', // 【页面】AI建议-
  'decisionSignals.archived': 'Archived', // 【页面】AI建议-
  'decisionSignals.catalystSummary': 'Catalyst', // 【页面】AI建议-
  'decisionSignals.close': 'Close signal', // 【页面】AI建议-
  'decisionSignals.closeConfirm': 'Close this signal? Closed signals are no longer tracked as current recommendations.', // 【页面】AI建议-
  'decisionSignals.closed': 'Closed', // 【页面】AI建议-
  'decisionSignals.confidence': 'Confidence', // 【页面】AI建议-
  'decisionSignals.confirmStatusTitle': 'Update signal status', // 【页面】AI建议-
  'decisionSignals.createdAt': 'Created', // 【页面】AI建议-
  'decisionSignals.dataQuality': 'Data quality', // 【页面】AI建议-
  'decisionSignals.description': 'Query structured AI recommendations by stock, phase, source, and status while keeping risk and data-quality context visible.', // 【页面】AI建议-
  'decisionSignals.detailTitle': 'Signal details', // 【页面】AI建议-
  'decisionSignals.directionExpected': 'Expected direction', // 【页面】AI建议-
  'decisionSignals.emptyDescription': 'After a regular stock analysis completes, extracted structured recommendations appear here.', // 【页面】AI建议-
  'decisionSignals.emptyTitle': 'No decision signals', // 【页面】AI建议-
  'decisionSignals.entryRange': 'Entry range', // 【页面】AI建议-
  'decisionSignals.errorTitle': 'Failed to load decision signals', // 【页面】AI建议-
  'decisionSignals.evidence': 'Evidence', // 【页面】AI建议-
  'decisionSignals.expired': 'Expired', // 【页面】AI建议-
  'decisionSignals.expiresAt': 'Expires', // 【页面】AI建议-
  'decisionSignals.feedback.not_useful': 'Not useful', // 【页面】AI建议-
  'decisionSignals.feedback.useful': 'Useful', // 【页面】AI建议-
  'decisionSignals.feedbackNone': 'No feedback yet', // 【页面】AI建议-
  'decisionSignals.feedbackTitle': 'User feedback', // 【页面】AI建议-
  'decisionSignals.filter': 'Filter', // 【页面】AI建议-
  'decisionSignals.horizon': 'Horizon', // 【页面】AI建议-
  'decisionSignals.horizon.10d': '10 days', // 【页面】AI建议-
  'decisionSignals.horizon.1d': '1 day', // 【页面】AI建议-
  'decisionSignals.horizon.3d': '3 days', // 【页面】AI建议-
  'decisionSignals.horizon.5d': '5 days', // 【页面】AI建议-
  'decisionSignals.horizon.intraday': 'Intraday', // 【页面】AI建议-
  'decisionSignals.horizon.long': 'Long term', // 【页面】AI建议-
  'decisionSignals.horizon.swing': 'Swing', // 【页面】AI建议-
  'decisionSignals.invalidate': 'Mark invalid', // 【页面】AI建议-
  'decisionSignals.invalidateConfirm': 'Mark this signal invalid? Invalidated signals are no longer shown as current active recommendations.', // 【页面】AI建议-
  'decisionSignals.invalidated': 'Invalidated', // 【页面】AI建议-
  'decisionSignals.invalidation': 'Invalidation', // 【页面】AI建议-
  'decisionSignals.latestDescription': 'Read the latest active signals for the current stock context.', // 【页面】AI建议-
  'decisionSignals.latestTitle': 'Latest signals by stock', // 【页面】AI建议-
  'decisionSignals.market': 'Market', // 【页面】AI建议-
  'decisionSignals.market.cn': 'A-shares', // 【页面】AI建议-
  'decisionSignals.market.hk': 'Hong Kong', // 【页面】AI建议-
  'decisionSignals.market.jp': 'Japan', // 【页面】AI建议-
  'decisionSignals.market.kr': 'Korea', // 【页面】AI建议-
  'decisionSignals.market.tw': 'Taiwan', // 【页面】AI建议-
  'decisionSignals.market.us': 'US', // 【页面】AI建议-
  'decisionSignals.marketPhase': 'Phase', // 【页面】AI建议-
  'decisionSignals.marketPhase.closing_auction': 'Closing auction', // 【页面】AI建议-
  'decisionSignals.marketPhase.intraday': 'Intraday', // 【页面】AI建议-
  'decisionSignals.marketPhase.lunch_break': 'Lunch break', // 【页面】AI建议-
  'decisionSignals.marketPhase.non_trading': 'Non-trading', // 【页面】AI建议-
  'decisionSignals.marketPhase.postmarket': 'Post-market', // 【页面】AI建议-
  'decisionSignals.marketPhase.premarket': 'Pre-market', // 【页面】AI建议-
  'decisionSignals.marketPhase.unknown': 'Unknown phase', // 【页面】AI建议-
  'decisionSignals.metadata': 'Metadata', // 【页面】AI建议-
  'decisionSignals.noLatestDescription': 'This stock has no current active signal, or existing signals have expired.', // 【页面】AI建议-
  'decisionSignals.noLatestTitle': 'No latest active signals', // 【页面】AI建议-
  'decisionSignals.noOutcomes': 'No outcome results yet', // 【页面】AI建议-
  'decisionSignals.noReviewedStatsDescription': 'AI signals may already exist, but no statistically reviewable outcome has been produced yet.', // 【页面】AI建议-
  'decisionSignals.noReviewedStatsTitle': 'No reviewed samples yet', // 【页面】AI建议-
  'decisionSignals.outcome.hit': 'Hit', // 【页面】AI建议-
  'decisionSignals.outcome.miss': 'Miss', // 【页面】AI建议-
  'decisionSignals.outcome.neutral': 'Neutral', // 【页面】AI建议-
  'decisionSignals.outcome.unable': 'Unable', // 【页面】AI建议-
  'decisionSignals.outcomes': 'Outcome results', // 【页面】AI建议-
  'decisionSignals.pageTitle': 'AI signals - HRS', // 【页面】AI建议-
  'decisionSignals.planQuality': 'Plan quality', // 【页面】AI建议-
  'decisionSignals.planQuality.complete': 'Complete', // 【页面】AI建议-
  'decisionSignals.planQuality.minimal': 'Minimal', // 【页面】AI建议-
  'decisionSignals.planQuality.partial': 'Partial', // 【页面】AI建议-
  'decisionSignals.planQuality.unknown': 'Unknown', // 【页面】AI建议-
  'decisionSignals.portfolioColumn': 'AI signals', // 【页面】AI建议-
  'decisionSignals.portfolioEmpty': '-', // 【页面】AI建议-
  'decisionSignals.portfolioLoading': 'Loading', // 【页面】AI建议-
  'decisionSignals.portfolioPartialWarning': 'AI signals loaded only partially: {message}', // 【页面】AI建议-
  'decisionSignals.portfolioWarningTitle': 'AI signals degraded', // 【页面】AI建议-
  'decisionSignals.pricePlan': 'Price plan', // 【页面】AI建议-
  'decisionSignals.profile': 'Profile', // 【页面】AI建议-
  'decisionSignals.profile.aggressive': 'Aggressive', // 【页面】AI建议-
  'decisionSignals.profile.balanced': 'Balanced', // 【页面】AI建议-
  'decisionSignals.profile.conservative': 'Conservative', // 【页面】AI建议-
  'decisionSignals.profile.unknown': 'Unknown', // 【页面】AI建议-
  'decisionSignals.profileCalibrationAverageReturn': 'Average stock window return', // 【页面】AI建议-
  'decisionSignals.profileCalibrationBreakdownLabel': 'Breakdown view', // 【页面】AI建议-
  'decisionSignals.profileCalibrationByAction': 'By suggested action', // 【页面】AI建议-
  'decisionSignals.profileCalibrationByHorizon': 'By review horizon', // 【页面】AI建议-
  'decisionSignals.profileCalibrationCompletedShort': '{count} completed', // 【页面】AI建议-
  'decisionSignals.profileCalibrationDescription': 'These historical outcome reviews are descriptive only. They do not prove one profile is better and are not investment advice.', // 【页面】AI建议-
  'decisionSignals.profileCalibrationHitRate': 'Hit rate', // 【页面】AI建议-
  'decisionSignals.profileCalibrationInsufficient': 'Insufficient sample size; for observation only.', // 【页面】AI建议-
  'decisionSignals.profileCalibrationMae': 'Maximum adverse move', // 【页面】AI建议-
  'decisionSignals.profileCalibrationMaeDescription': 'Maximum adverse move is the worst move from the starting price during the review window. It is not a limit on future risk.', // 【页面】AI建议-
  'decisionSignals.profileCalibrationMissRate': 'Miss rate', // 【页面】AI建议-
  'decisionSignals.profileCalibrationNoBreakdownSamples': 'No breakdown samples are available to observe yet.', // 【页面】AI建议-
  'decisionSignals.profileCalibrationSampleCounts': '{completed} completed / {total} total', // 【页面】AI建议-
  'decisionSignals.profileCalibrationThreshold': 'Each group needs at least {count} completed samples before performance metrics are shown.', // 【页面】AI建议-
  'decisionSignals.profileCalibrationTitle': 'Decision profile history', // 【页面】AI建议-
  'decisionSignals.profileCalibrationUnableRate': 'Unable-to-evaluate rate', // 【页面】AI建议-
  'decisionSignals.profileCalibrationUnavailable': 'No calculable result', // 【页面】AI建议-
  'decisionSignals.profileCalibrationUnknownDimension': 'Unknown', // 【页面】AI建议-
  'decisionSignals.profileCalibrationUnknownNotice': '{count} historical samples have no decision profile label and are not included in the three profiles.', // 【页面】AI建议-
  'decisionSignals.reason': 'Reason', // 【页面】AI建议-
  'decisionSignals.reassessBlockedNote': 'This preview is constrained to a non-aggressive display action.', // 【页面】AI建议-
  'decisionSignals.reassessBlockedTitle': 'Preview blocked by guardrail', // 【页面】AI建议-
  'decisionSignals.reassessPersist': 'Confirm and save', // 【页面】AI建议-
  'decisionSignals.reassessPersistBlockedTitle': 'Save blocked by guardrail', // 【页面】AI建议-
  'decisionSignals.reassessPersistConfirmMessage': 'The server will recompute from the same persisted report snapshot and save only a guardrail-approved result.', // 【页面】AI建议-
  'decisionSignals.reassessPersistConfirmTitle': 'Save reassessed signal', // 【页面】AI建议-
  'decisionSignals.reassessPersistedCreated': 'Saved as a new DecisionSignal #{id}.', // 【页面】AI建议-
  'decisionSignals.reassessPersistedCreatedTitle': 'Reassessed signal saved', // 【页面】AI建议-
  'decisionSignals.reassessPersistedExisting': 'DecisionSignal #{id} already exists for the same report, profile, and signal identity. No duplicate was created; the original server record is shown.', // 【页面】AI建议-
  'decisionSignals.reassessPersistedExistingTitle': 'Existing signal reused', // 【页面】AI建议-
  'decisionSignals.reassessPersistedRefreshed': 'DecisionSignal #{id} was refreshed under the storage contract by renewing an expired record or filling missing identity dimensions. Original creation provenance is preserved; use the returned server record as authoritative.', // 【页面】AI建议-
  'decisionSignals.reassessPersistedRefreshedTitle': 'Reassessed signal refreshed', // 【页面】AI建议-
  'decisionSignals.reassessPersistedTerminalExisting': 'DecisionSignal #{id} is already {status}. No signal was created or reactivated.', // 【页面】AI建议-
  'decisionSignals.reassessPersistedTerminalTitle': 'Existing signal remains terminal', // 【页面】AI建议-
  'decisionSignals.reassessPersisting': 'Saving', // 【页面】AI建议-
  'decisionSignals.reassessPreview': 'Generate preview', // 【页面】AI建议-
  'decisionSignals.reassessProfile': 'Reassess profile', // 【页面】AI建议-
  'decisionSignals.reassessRawFinal': 'Raw / final', // 【页面】AI建议-
  'decisionSignals.reassessSource': 'Source report #{id}', // 【页面】AI建议-
  'decisionSignals.reassessTitle': 'Decision profile reassess preview', // 【页面】AI建议-
  'decisionSignals.reassessUnsupported': 'This signal does not support reassess', // 【页面】AI建议-
  'decisionSignals.reassessUnsupportedTitle': 'Missing source report', // 【页面】AI建议-
  'decisionSignals.reassessWarnings': 'Guardrail warnings', // 【页面】AI建议-
  'decisionSignals.refresh': 'Refresh', // 【页面】AI建议-
  'decisionSignals.returnPct': 'Window return', // 【页面】AI建议-
  'decisionSignals.riskSummary': 'Risk', // 【页面】AI建议-
  'decisionSignals.score': 'Score', // 【页面】AI建议-
  'decisionSignals.source': 'Source', // 【页面】AI建议-
  'decisionSignals.sourceReport': 'Source report', // 【页面】AI建议-
  'decisionSignals.sourceReportId': 'Source report ID', // 【页面】AI建议-
  'decisionSignals.sourceType.agent': 'Agent', // 【页面】AI建议-
  'decisionSignals.sourceType.alert': 'Alert', // 【页面】AI建议-
  'decisionSignals.sourceType.analysis': 'Analysis report', // 【页面】AI建议-
  'decisionSignals.sourceType.manual': 'Manual', // 【页面】AI建议-
  'decisionSignals.sourceType.market_review': 'Market review', // 【页面】AI建议-
  'decisionSignals.statsDescription': 'Signal performance from the current outcome engine version, excluding archived signals by default.', // 【页面】AI建议-
  'decisionSignals.statsErrorTitle': 'Failed to load outcome stats', // 【页面】AI建议-
  'decisionSignals.statsGlobalScope': 'These are global reviewed outcome stats. They are not the current visible signal count and do not follow the current stock filter.', // 【页面】AI建议-
  'decisionSignals.statsHitRate': 'Hit rate', // 【页面】AI建议-
  'decisionSignals.statsTitle': 'Signal performance', // 【页面】AI建议-
  'decisionSignals.statsTotal': 'Evaluations', // 【页面】AI建议-
  'decisionSignals.status': 'Status', // 【页面】AI建议-
  'decisionSignals.stockCode': 'Stock code', // 【页面】AI建议-
  'decisionSignals.stockContextApply': 'View stock', // 【页面】AI建议-
  'decisionSignals.stockContextClear': 'Clear current stock', // 【页面】AI建议-
  'decisionSignals.stockContextCurrent': 'Current stock: {stock}', // 【页面】AI建议-
  'decisionSignals.stockContextDescription': 'Choose one stock once; latest signals and the timeline will share that context.', // 【页面】AI建议-
  'decisionSignals.stockContextEmpty': 'No current stock selected.', // 【页面】AI建议-
  'decisionSignals.stockContextGuideDescription': 'Choose the current stock at the top of the page before viewing latest signals and the timeline.', // 【页面】AI建议-
  'decisionSignals.stockContextGuideTitle': 'Choose a stock to view AI signals', // 【页面】AI建议-
  'decisionSignals.stockContextNoCandidates': 'No candidates available. You can enter a stock code or name directly.', // 【页面】AI建议-
  'decisionSignals.stockContextPopular': 'Popular candidates', // 【页面】AI建议-
  'decisionSignals.stockContextRecent': 'Recent analyses', // 【页面】AI建议-
  'decisionSignals.stockContextTitle': 'Current stock', // 【页面】AI建议-
  'decisionSignals.stopLoss': 'Stop loss', // 【页面】AI建议-
  'decisionSignals.targetPrice': 'Target price', // 【页面】AI建议-
  'decisionSignals.timelineAlertShape': 'Diamond points indicate alert', // 【页面】AI建议-
  'decisionSignals.timelineDescription': 'Track how one stock signal changes over time.', // 【页面】AI建议-
  'decisionSignals.timelineEmptyDescription': 'No signals for this stock in the selected range.', // 【页面】AI建议-
  'decisionSignals.timelineEmptyTitle': 'No timeline signals', // 【页面】AI建议-
  'decisionSignals.timelineErrorTitle': 'Failed to load timeline', // 【页面】AI建议-
  'decisionSignals.timelineFamilyBullish': 'Bullish', // 【页面】AI建议-
  'decisionSignals.timelineFamilyDefensive': 'Defensive', // 【页面】AI建议-
  'decisionSignals.timelineFamilyNeutral': 'Neutral', // 【页面】AI建议-
  'decisionSignals.timelineGuideDescription': 'Adjust range, status, or market, then search the timeline to apply the filters.', // 【页面】AI建议-
  'decisionSignals.timelineGuideTitle': 'Search the current stock timeline', // 【页面】AI建议-
  'decisionSignals.timelineMarket': 'Timeline market', // 【页面】AI建议-
  'decisionSignals.timelineProfile': 'Timeline profile', // 【页面】AI建议-
  'decisionSignals.timelineRange': 'Range', // 【页面】AI建议-
  'decisionSignals.timelineRange.180d': '180 days', // 【页面】AI建议-
  'decisionSignals.timelineRange.30d': '30 days', // 【页面】AI建议-
  'decisionSignals.timelineRange.90d': '90 days', // 【页面】AI建议-
  'decisionSignals.timelineSearch': 'Search timeline', // 【页面】AI建议-
  'decisionSignals.timelineSelected': 'Selected point {index}', // 【页面】AI建议-
  'decisionSignals.timelineStatus': 'Timeline status', // 【页面】AI建议-
  'decisionSignals.timelineStatus.active': 'Active only', // 【页面】AI建议-
  'decisionSignals.timelineStatus.all': 'All history', // 【页面】AI建议-
  'decisionSignals.timelineTitle': 'Stock signal timeline', // 【页面】AI建议-
  'decisionSignals.timelineTruncatedDescription': 'Only the latest 100 signals are shown. Narrow the time range.', // 【页面】AI建议-
  'decisionSignals.timelineTruncatedTitle': 'Timeline truncated', // 【页面】AI建议-
  'decisionSignals.title': 'AI signals', // 【页面】AI建议-
  'decisionSignals.total': '{total} signals', // 【页面】AI建议-
  'decisionSignals.unableReason': 'Unable reason', // 【页面】AI建议-
  'decisionSignals.viewDetailsFor': 'View AI signal details for {stock}', // 【页面】AI建议-
  'decisionSignals.watchConditions': 'Watch conditions', // 【页面】AI建议-
  // eodPicker.*
  'eodPicker.start.button': 'Start Analysis', // 【页面】尾盘选股-开始分析按钮
  'eodPicker.start.editFilters': 'Click to edit', // 【页面】尾盘选股-点击编辑筛选条件提示
  'eodPicker.start.resetFilters': 'Default', // 【页面】尾盘选股-重置为默认筛选
  'eodPicker.filters.circMv': 'Circ. Market Cap', // 【页面】尾盘选股-筛选-流通市值
  'eodPicker.filters.volumeRatio': 'Volume Ratio', // 【页面】尾盘选股-筛选-量比
  'eodPicker.filters.changePct': 'Day Change', // 【页面】尾盘选股-筛选-当日涨幅
  'eodPicker.filters.turnoverRate': 'Turnover Rate', // 【页面】尾盘选股-筛选-换手率
  'eodPicker.filters.excludeSt': 'Exclude ST', // 【页面】尾盘选股-筛选-过滤ST开关
  'eodPicker.filters.strength': 'Intraday Strength', // 【页面】尾盘选股-筛选-分时强度
  'eodPicker.filters.title': 'Filters', // 【页面】尾盘选股-筛选条件面板标题
  'eodPicker.filters.done': 'Done', // 【页面】尾盘选股-筛选完成按钮
  'eodPicker.filters.on': 'On', // 【页面】尾盘选股-开关-开启
  'eodPicker.filters.off': 'Off', // 【页面】尾盘选股-开关-关闭
  'eodPicker.filters.unlimited': 'No limit', // 【页面】尾盘选股-筛选-不限
  'eodPicker.filters.cancel': 'Cancel', // 【页面】尾盘选股-筛选取消按钮
  'eodPicker.running.title': 'Picking…', // 【页面】尾盘选股-选股进行中标题
  'eodPicker.running.cancel': 'Cancel', // 【页面】尾盘选股-取消选股按钮
  'eodPicker.running.stepBasic': 'Step 1 · Basic filters', // 【页面】尾盘选股-进度步骤-基础条件过滤标题
  'eodPicker.running.stepStrength': 'Step 2 · Intraday strength', // 【页面】尾盘选股-进度步骤-分时强度过滤标题
  'eodPicker.running.stepPending': 'Filtering…', // 【页面】尾盘选股-进度步骤-进行中占位
  'eodPicker.running.stepEmpty': 'No results', // 【页面】尾盘选股-进度步骤-无股票提示
  'eodPicker.running.stepCount': '{count} stocks', // 【页面】尾盘选股-进度步骤-股票数量
  'eodPicker.result.title': 'Picking Results', // 【页面】尾盘选股-选股结果标题
  'eodPicker.result.basis': 'Basis date', // 【页面】尾盘选股-基准交易日标签
  'eodPicker.result.reanalyze': 'Re-run', // 【页面】尾盘选股-重新分析按钮
  'eodPicker.result.empty': 'No stocks matched the criteria. Try re-adjusting the filters.', // 【页面】尾盘选股-结果为空提示
  'eodPicker.result.emptyDesc': 'Try lowering the strength threshold, or relaxing the price-change / turnover-ratio conditions, then re-run.', // 【页面】尾盘选股-结果为空补充说明
  'eodPicker.result.sortBy': 'Sort by', // 【页面】尾盘选股-排序标签
  'eodPicker.result.sort.strength': 'Intraday Strength', // 【页面】尾盘选股-按分时强度排序选项
  'eodPicker.EodStockCard.strength': 'Strength', // 【页面组件】EodStockCard，卡片展示的分时强度指标数值
  'eodPicker.EodStockCard.circMv': 'Circ. Cap', // 【页面组件】EodStockCard，卡片指标-流通市值
  'eodPicker.EodStockCard.volumeRatio': 'Vol. Ratio', // 【页面组件】EodStockCard，卡片指标-量比
  'eodPicker.EodStockCard.turnoverRate': 'Turnover', // 【页面组件】EodStockCard，卡片指标-换手率
  'eodPicker.EodStockCard.amount': 'Amount', // 【页面组件】EodStockCard，卡片指标-成交额
  'eodPicker.EodStockCard.currentPrice': 'Price', // 【页面组件】EodStockCard，卡片指标-现价
  'eodPicker.EodStockCard.priceLegend': 'Price', // 【页面组件】EodStockCard，分时价格线图例文字
  'eodPicker.EodStockCard.avgPriceLegend': 'Avg', // 【页面组件】EodStockCard，分时均价线图例文字
  'eodPicker.EodStockCard.addWatchlist': 'Add to Watchlist', // 【页面组件】EodStockCard，加自选按钮文案
  'eodPicker.EodStockCard.inWatchlist': 'In Watchlist', // 【页面组件】EodStockCard，已加入自选的状态文案
  'eodPicker.EodStockCard.openKline': 'Click to open stock K-line', // 【页面组件】EodStockCard，点击卡片跳转 K 线的提示
  'eodPicker.EodStockCard.prevClose': 'Prev Close', // 【页面组件】EodStockCard，卡片指标-昨收
  'eodPicker.error.snapshot': 'Failed to fetch market snapshot; possibly a non-trading day or data source error.', // 【页面】尾盘选股-行情快照获取失败提示
  'eodPicker.error.failed': 'Screening task failed', // 【页面】尾盘选股-选股任务失败提示
  'eodPicker.error.generic': 'Operation failed, please retry later.', // 【页面】尾盘选股-通用操作失败提示
  'eodPicker.error.addWatchlist': 'Failed to add to watchlist, please retry later.', // 【页面】尾盘选股-加入自选失败提示
  // scanner.*
  'scanner.pool.title': 'Stock pool source', // 【页面】信号扫描-股票池来源卡片标题
  'scanner.pool.watchlist': 'Watchlist', // 【页面】信号扫描-股票池-自选股
  'scanner.pool.ranking': 'Ranking TopN', // 【页面】信号扫描-股票池-榜单 TopN
  'scanner.pool.limitUp': 'Limit-up pool', // 【页面】信号扫描-股票池-涨停池
  'scanner.pool.watchlistHint': 'Deduplicated pool from all watchlist groups', // 【页面】信号扫描-自选池说明
  'scanner.pool.rankingHint': 'Ranking comes from the full A-share realtime snapshot', // 【页面】信号扫描-榜单池说明
  'scanner.pool.limitUpHint': 'From the limit-up pool, sorted by consecutive boards and seal time', // 【页面】信号扫描-涨停池说明
  'scanner.pool.emptyWatchlist': 'Watchlist groups are empty, please add stocks first', // 【页面】信号扫描-自选池为空提示
  'scanner.pool.count': '{n} stocks in pool', // 【页面】信号扫描-股票池数量
  'scanner.rankingField.label': 'Sort by', // 【页面】信号扫描-榜单排序字段标签
  'scanner.rankingField.amount': 'Turnover', // 【页面】信号扫描-榜单排序-成交额
  'scanner.rankingField.changePercent': 'Change %', // 【页面】信号扫描-榜单排序-涨幅
  'scanner.rankingField.turnoverRate': 'Turnover rate', // 【页面】信号扫描-榜单排序-换手率
  'scanner.topN': 'Top {n}', // 【页面】信号扫描-TopN 选项
  'scanner.signals.title': 'Signal templates', // 【页面】信号扫描-信号模板卡片标题
  'scanner.signals.empty': 'Please select at least one signal template', // 【页面】信号扫描-未选信号提示
  'scanner.signal.ma_golden': 'MA golden cross', // 【页面】信号扫描-信号-MA金叉
  'scanner.signal.ma_golden_desc': 'Short MA crosses above long MA', // 【页面】信号扫描-信号-MA金叉说明
  'scanner.signal.ma_death': 'MA death cross', // 【页面】信号扫描-信号-MA死叉
  'scanner.signal.ma_death_desc': 'Short MA crosses below long MA', // 【页面】信号扫描-信号-MA死叉说明
  'scanner.signal.macd_golden': 'MACD golden cross', // 【页面】信号扫描-信号-MACD金叉
  'scanner.signal.macd_golden_desc': 'DIF crosses above DEA', // 【页面】信号扫描-信号-MACD金叉说明
  'scanner.signal.macd_death': 'MACD death cross', // 【页面】信号扫描-信号-MACD死叉
  'scanner.signal.macd_death_desc': 'DIF crosses below DEA', // 【页面】信号扫描-信号-MACD死叉说明
  'scanner.signal.rsi_oversold': 'RSI oversold', // 【页面】信号扫描-信号-RSI超卖
  'scanner.signal.rsi_oversold_desc': 'RSI below 30', // 【页面】信号扫描-信号-RSI超卖说明
  'scanner.signal.rsi_overbought': 'RSI overbought', // 【页面】信号扫描-信号-RSI超买
  'scanner.signal.rsi_overbought_desc': 'RSI above 70', // 【页面】信号扫描-信号-RSI超买说明
  'scanner.signal.boll_upper': 'BOLL upper', // 【页面】信号扫描-信号-BOLL突破上轨
  'scanner.signal.boll_upper_desc': 'Close breaks above the upper band', // 【页面】信号扫描-信号-BOLL突破上轨说明
  'scanner.signal.boll_lower': 'BOLL lower', // 【页面】信号扫描-信号-BOLL跌破下轨
  'scanner.signal.boll_lower_desc': 'Close breaks below the lower band', // 【页面】信号扫描-信号-BOLL跌破下轨说明
  'scanner.start': 'Start scan', // 【页面】信号扫描-开始扫描按钮
  'scanner.cancel': 'Cancel scan', // 【页面】信号扫描-取消扫描按钮
  'scanner.restart': 'Scan again', // 【页面】信号扫描-重新扫描按钮
  'scanner.progress.preparing': 'Preparing', // 【页面】信号扫描-进度未就绪占位
  'scanner.running.stepPool': 'Step 1 · Resolve pool', // 【页面】信号扫描-分步·解析股票池标题
  'scanner.running.stepSignal': 'Step 2 · Signal scan', // 【页面】信号扫描-分步·技术信号扫描标题
  'scanner.running.stepPending': 'Scanning…', // 【页面】信号扫描-分步·进行中占位
  'scanner.running.stepEmpty': 'No results', // 【页面】信号扫描-分步·无结果占位
  'scanner.running.stepCount': '{count} stocks', // 【页面】信号扫描-分步·命中数量
  'scanner.cancelled': 'Scan cancelled', // 【页面】信号扫描-取消完成提示
  'scanner.result.title': 'Scan results', // 【页面】信号扫描-扫描结果标题
  'scanner.result.count': '{n} triggered', // 【页面】信号扫描-结果计数
  'scanner.result.empty': 'No scan results yet', // 【页面】信号扫描-结果为空提示
  'scanner.result.emptyDesc': 'Pick a stock pool and signal templates, then start scanning', // 【页面】信号扫描-结果为空补充说明
  'scanner.result.openKline': 'Click to open the stock K-line', // 【页面】信号扫描-点击结果跳 K 线的提示
  'scanner.result.addWatchlist': 'Add', // 【页面】信号扫描-加自选按钮文案
  'scanner.result.inWatchlist': 'Added', // 【页面】信号扫描-已加入自选的状态文案
  'scanner.error.start': 'Failed to submit the scan task, please retry later.', // 【页面】信号扫描-提交任务失败提示
  'scanner.error.cancel': 'Failed to cancel the scan, please retry later.', // 【页面】信号扫描-取消失败提示
  'scanner.error.failed': 'Scan task failed', // 【页面】信号扫描-扫描任务失败提示
  'scanner.error.generic': 'Operation failed, please retry later.', // 【页面】信号扫描-通用操作失败提示
  'scanner.error.addWatchlist': 'Failed to add to watchlist, please retry later.', // 【页面】信号扫描-加入自选失败提示
  // history.*
  'history.actionAdd': 'Add', // 【页面】分析历史-
  'history.actionAlert': 'Alert', // 【页面】分析历史-
  'history.actionAvoid': 'Avoid', // 【页面】分析历史-
  'history.actionBuy': 'Buy', // 【页面】分析历史-
  'history.actionHold': 'Hold', // 【页面】分析历史-
  'history.actionReduce': 'Reduce', // 【页面】分析历史-
  'history.actionSell': 'Sell', // 【页面】分析历史-
  'history.actionWatch': 'Watch', // 【页面】分析历史-
  'history.analysisCount': '{count} runs', // 【页面】分析历史-
  'history.bottomReached': 'End', // 【页面】分析历史-
  'history.defaultEmptyDescription': 'Recent results will be saved here after the first analysis.', // 【页面】分析历史-
  'history.defaultEmptyTitle': 'No analysis history', // 【页面】分析历史-
  'history.defaultTitle': 'Analysis history', // 【页面】分析历史-
  'history.deleteRecord': 'Delete {name} history record', // 【页面】分析历史-
  'history.itemAria': '{name} {code} history record', // 【页面】分析历史-
  'history.loading': 'Loading history...', // 【页面】分析历史-
  'history.selectAllHistoryAria': 'Select all loaded history records', // 【页面】分析历史-
  'history.selectAllStockAria': 'Select all current stocks', // 【页面】分析历史-
  'history.sentiment': 'Sentiment', // 【页面】分析历史-
  // kline.*
  'kline.error': 'Failed to load K-line data', // 【页面】个股K线-
  'kline.empty': 'No K-line data', // 【页面】个股K线-
  'kline.fullData': 'Full Data', // 【页面】个股K线-
  'kline.info.amount': 'Amount', // 【页面】个股K线-
  'kline.info.amplitude': 'Amplitude', // 【页面】个股K线-
  'kline.info.high': 'High', // 【页面】个股K线-
  'kline.info.low': 'Low', // 【页面】个股K线-
  'kline.info.open': 'Open', // 【页面】个股K线-
  'kline.info.peRatioTTM': 'P/E (TTM)', // 【页面】个股K线-
  'kline.info.prevClose': 'Prev Close', // 【页面】个股K线-
  'kline.info.totalMarketCap': 'Market Cap', // 【页面】个股K线-
  'kline.info.turnoverRate': 'Turnover', // 【页面】个股K线-
  'kline.info.volume': 'Volume', // 【页面】个股K线-
  'kline.noStockSelected': 'Please search and select a stock to view K-line', // 【页面】个股K线-
  'kline.period.120m': '120m', // 【页面】个股K线-
  'kline.period.15m': '15m', // 【页面】个股K线-
  'kline.period.1m': 'Intraday', // 【页面】个股K线-
  'kline.period.30m': '30m', // 【页面】个股K线-
  'kline.period.5d': '5-Day', // 【页面】个股K线-
  'kline.period.5m': '5m', // 【页面】个股K线-
  'kline.period.60m': '60m', // 【页面】个股K线-
  'kline.period.daily': 'Daily', // 【页面】个股K线-
  'kline.period.monthly': 'Monthly', // 【页面】个股K线-
  'kline.period.weekly': 'Weekly', // 【页面】个股K线-
  'kline.period.yearly': 'Yearly', // 【页面】个股K线-
  'kline.tooltip.amount': 'Amount', // 【页面】个股K线-
  'kline.tooltip.change': 'Change', // 【页面】个股K线-
  'kline.tooltip.close': 'Close', // 【页面】个股K线-
  'kline.tooltip.date': 'Date', // 【页面】个股K线-
  'kline.tooltip.dea': 'DEA', // 【页面】个股K线-
  'kline.tooltip.dif': 'DIF', // 【页面】个股K线-
  'kline.tooltip.high': 'High', // 【页面】个股K线-
  'kline.tooltip.low': 'Low', // 【页面】个股K线-
  'kline.tooltip.ma10': 'MA10', // 【页面】个股K线-
  'kline.tooltip.ma30': 'MA30', // 【页面】个股K线-
  'kline.tooltip.ma5': 'MA5', // 【页面】个股K线-
  'kline.tooltip.ma60': 'MA60', // 【页面】个股K线-
  'kline.tooltip.macd': 'MACD', // 【页面】个股K线-
  'kline.tooltip.open': 'Open', // 【页面】个股K线-
  'kline.tooltip.volume': 'Volume', // 【页面】个股K线-
  // liveCalendar.*
  'liveCalendar.degradedTip.title': 'Data source temporarily unavailable', // 【页面】财经日历-
  'liveCalendar.degradedTip.message': 'Displaying locally cached data. Please check the data source query status.', // 【页面】财经日历-
  'liveCalendar.loading': 'Loading calendar…', // 【页面】财经日历-
  'liveCalendar.refresh': 'Refresh calendar', // 【页面】财经日历-
  'liveCalendar.refreshing': 'Refreshing…', // 【页面】财经日历-
  'liveCalendar.subtitle': 'Financial calendar for macro, earnings, IPO, and event items', // 【页面】财经日历-
  'liveCalendar.tabs.activity': 'Events', // 【页面】财经日历-
  'liveCalendar.tabs.all': 'All', // 【页面】财经日历-
  'liveCalendar.tabs.earnings': 'Earnings', // 【页面】财经日历-
  'liveCalendar.tabs.ipo': 'IPO', // 【页面】财经日历-
  'liveCalendar.tabs.macro': 'Macro', // 【页面】财经日历-
  'liveCalendar.title': 'Live Calendar', // 【页面】财经日历-
  // liveNews.*
  'liveNews.channelTabs': 'Newsflash channels', // 【页面】实时财经-
  'liveNews.dateAll': 'All dates', // 【页面】实时财经-
  'liveNews.dateToday': 'Today', // 【页面】实时财经-
  'liveNews.dateYesterday': 'Yesterday', // 【页面】实时财经-
  'liveNews.degradedTip': 'Live source unavailable — showing aggregated fallback data (no channel filter or importance level)', // 【页面】实时财经-
  'liveNews.empty': 'No newsflash yet', // 【页面】实时财经-
  'liveNews.emptyDate': 'No newsflash on the selected date', // 【页面】实时财经-
  'liveNews.emptyImportant': 'No important newsflash in this channel', // 【页面】实时财经-
  'liveNews.emptyKeyword': 'No matching newsflash found', // 【页面】实时财经-
  'liveNews.expand': 'Expand', // 【页面】实时财经-
  'liveNews.collapse': 'Collapse', // 【页面】实时财经-
  'liveNews.importantOnly': 'Important only', // 【页面】实时财经-
  'liveNews.importantTag': 'Important', // 【页面】实时财经-
  'liveNews.normalTag': 'Normal', // 【页面】实时财经-
  'liveNews.loadMore': 'Load more', // 【页面】实时财经-
  'liveNews.loading': 'Fetching latest newsflash…', // 【页面】实时财经-
  'liveNews.refresh': 'Refresh news', // 【页面】实时财经-
  'liveNews.refreshing': 'Refreshing news', // 【页面】实时财经-
  'liveNews.searchPlaceholder': 'Search newsflash…', // 【页面】实时财经-
  'liveNews.subtitle': '24/7 financial newsflash across headlines, A-shares, US, HK, FX, commodities, bonds and tech', // 【页面】实时财经-
  'liveNews.title': 'Newsflash', // 【页面】实时财经-
  // notFound.*
  'notFound.backHome': 'Back Home', // 【页面】404-
  'notFound.relogin': 'Re-login', // 【页面】404-
  'notFound.description': 'The page you requested does not exist or has moved.', // 【页面】404-
  'notFound.documentTitle': 'Page not found - HermesX', // 【页面】404-
  'notFound.title': 'Page not found', // 【页面】404-
  // report.*
  'report.addToWatchlist': 'Add to watchlist', // 【页面】报告-
  'report.removeFromWatchlist': 'Remove from watchlist', // 【页面】报告-
  'report.watchlist': 'Watchlist', // 【页面】报告-
  // review.*
  'review.analyze': 'Analyze', // 【页面】复盘-
  'review.analyzing': 'Analyzing', // 【页面】复盘-
  'review.askAi': 'Ask AI', // 【页面】复盘-
  'review.defaultStrategyDescription': 'Use the system default analysis framework', // 【页面】复盘-
  'review.defaultStrategyName': 'Default strategy', // 【页面】复盘-
  'review.duplicateTask': 'Task already exists', // 【页面】复盘-
  'review.fullReport': 'Full analysis report', // 【页面】复盘-
  'review.goSettings': 'Configure', // 【页面】复盘-
  'review.historyButton': 'History', // 【页面】复盘-
  'review.historyTrend': 'History trend', // 【页面】复盘-
  'review.inputInvalid': 'Invalid input', // 【页面】复盘-
  'review.loadingReport': 'Loading report...', // 【页面】复盘-
  'review.marketRegionAll': 'All markets', // 【页面】复盘-
  'review.marketRegionCn': 'A-shares', // 【页面】复盘-
  'review.marketRegionDefaultUnavailable': 'Resolved by the server when submitted', // 【页面】复盘-
  'review.marketRegionDescription': 'Choose one or more markets for this review run.', // 【页面】复盘-
  'review.marketRegionHk': 'Hong Kong', // 【页面】复盘-
  'review.marketRegionJp': 'Japan', // 【页面】复盘-
  'review.marketRegionKr': 'Korea', // 【页面】复盘-
  'review.marketRegionOneTimeHint': 'Applies only to this run and does not change global settings.', // 【页面】复盘-
  'review.marketRegionSelector': 'Select market review regions', // 【页面】复盘-
  'review.marketRegionServerDefault': 'Server default', // 【页面】复盘-
  'review.title': 'Market Review', // 【页面】复盘-Market Review page title
  'review.subtitle': 'Integrated stock analysis, market review, and task panels—auto-generating scheduled analysis review reports from closing, industry, and sentiment data', // 【页面】复盘-Home page subtitle
  'review.marketRegionTitle': 'Markets for this review', // 【页面】复盘-
  'review.marketRegionUs': 'US', // 【页面】复盘-
  'review.marketReview': 'Market review', // 【页面】复盘-
  'review.marketReviewCompleted': 'Market review completed', // 【页面】复盘-
  'review.marketReviewCompletedWithReport': 'Market review completed. Result:', // 【页面】复盘-
  'review.marketReviewCompletedWithoutReport': 'Market review completed. The result was generated and sent according to your configuration.', // 【页面】复盘-
  'review.marketReviewFailed': 'Market review failed.', // 【页面】复盘-
  'review.marketReviewInProgress': 'Market review in progress', // 【页面】复盘-
  'review.marketReviewSubmitted': 'Market review submitted', // 【页面】复盘-
  'review.marketReviewSubmittedWithRegion': '{message}; effective region: {region}', // 【页面】复盘-
  'review.marketReviewTimeout': 'Market review timed out', // 【页面】复盘-
  'review.marketReviewTimeoutMessage': 'The task did not return a final result in time. Check the task list or history.', // 【页面】复盘-
  'review.marketReviewUnknownStatus': 'Unexpected market review status', // 【页面】复盘-
  'review.notify': 'Send notification', // 【页面】复盘-
  'review.pageTitle': 'HermesX - HRS', // 【页面】复盘-
  'review.progressActive': 'In progress', // 【页面】复盘-
  'review.reanalyze': 'Reanalyze', // 【页面】复盘-
  'review.rerunMarketReview': 'Rerun market review', // 【页面】复盘-
  'review.setupIncomplete': 'Base configuration incomplete', // 【页面】复盘-
  'review.setupMissingGeneric': 'Base configuration is still incomplete. Complete it before running the minimal analysis flow.', // 【页面】复盘-
  'review.setupMissingWithLabels': 'Missing {labels}. Complete them before running the minimal analysis flow.', // 【页面】复盘-
  'review.startAnalysisDescription': 'Enter a stock code to analyze, or pick a historical report from the left.', // 【页面】复盘-
  'review.startAnalysisTitle': 'Start analysis', // 【页面】复盘-
  'review.strategy': 'Strategy', // 【页面】复盘-
  'review.submitMarketReview': 'Submitting', // 【页面】复盘-
  'review.taskStatus': 'Task status: {status} ({progress})', // 【页面】复盘-
  'review.taskStatusWithRegion': 'Task status: {status} ({progress}); effective region: {region}', // 【页面】复盘-
  'review.unknownTaskStatus': 'Received unknown task status: {status}', // 【页面】复盘-
  // sector.*
  'sector.tab.board': 'Sector', // 【页面】板块-Primary tab: Sector
  'sector.tab.boardConcept': 'Concept', // 【页面】板块-"Sector" secondary tab: Concept
  'sector.tab.boardIndustry': 'Industry', // 【页面】板块-"Sector" secondary tab: Industry
  'sector.tab.cloudConcept': 'Concept Cloud', // 【页面】板块-"Cloud Map" secondary tab: Concept Cloud
  'sector.tab.cloudEtf': 'ETF Cloud', // 【页面】板块-"Cloud Map" secondary tab: ETF Cloud
  'sector.tab.cloudMap': 'Cloud Map', // 【页面】板块-Primary tab: Cloud Map
  'sector.tab.cloudSector': 'Sector Cloud', // 【页面】板块-"Cloud Map" secondary tab: Sector Cloud
  'sector.tab.cloudStock': 'Stock Cloud', // 【页面】板块-"Cloud Map" secondary tab: Stock Cloud
  'sector.tab.fund': 'Fund', // 【页面】板块-Primary tab: Fund
  // settings.*
  'settings.actionSuccess': 'Success', // 【页面】设置-
  'settings.activePanelDescription': 'Use unified field cards to maintain this configuration category.', // 【页面】设置-
  'settings.activePanelTitle': 'Current category fields', // 【页面】设置-
  'settings.agentBackendCanTry': 'Can try', // 【页面】设置-
  'settings.agentBackendCanTryDescription': 'The basic environment check passed. You can return to Chat and ask directly; the first question performs the real execution.', // 【页面】设置-
  'settings.agentBackendCodexLabel': 'Codex Agent', // 【页面】设置-
  'settings.agentBackendCodexNotice': 'Codex can currently read only saved analysis context and backtest summaries. Live quotes, news, market hotspots, technical-indicator recalculation, per-stock backtest details, and portfolio tools are not available; choose Default model when you need them. Stop ends both the Codex turn and its tool task. This choice only affects ask-stock Chat; Multi Agent, Deep Research, regular reports, and scheduled tasks keep their existing routes. Codex is not an offline model, and services configured in Codex may process questions and tool results.', // 【页面】设置-
  'settings.agentBackendCodexNoticeTitle': 'Codex local Agent (experimental)', // 【页面】设置-
  'settings.agentBackendCommandNotFound': 'Codex was not found on the device running HRS. Install it there and ensure the HRS backend process can find it on PATH.', // 【页面】设置-
  'settings.agentBackendDefaultLabel': 'Default model', // 【页面】设置-
  'settings.agentBackendEnableMode': 'Enable Agent Mode', // 【页面】设置-
  'settings.agentBackendErrorCode': 'Error code', // 【页面】设置-
  'settings.agentBackendExperimental': 'Experimental', // 【页面】设置-
  'settings.agentBackendInvalidTimeout': 'Codex requires an Agent timeout greater than 0 so success, failure, timeout, and stop all reach a bounded end.', // 【页面】设置-
  'settings.agentBackendModeDisabled': 'Agent Mode is disabled. Update the draft below, then save the settings before using ask-stock Chat.', // 【页面】设置-
  'settings.agentBackendModeDisabledTitle': 'Enable Agent Mode', // 【页面】设置-
  'settings.agentBackendNeedsAction': 'Needs action', // 【页面】设置-
  'settings.agentBackendPlatformUnsupported': 'Codex local Agent does not currently support native Windows. Use macOS, Linux, or run the complete HRS backend inside WSL.', // 【页面】设置-
  'settings.agentBackendRefresh': 'Refresh status', // 【页面】设置-
  'settings.agentBackendRefreshing': 'Checking', // 【页面】设置-
  'settings.agentBackendSectionDescription': 'Choose the default model configuration or Codex on this device for the same ask-stock page, and preview the unsaved draft before saving.', // 【页面】设置-
  'settings.agentBackendSectionTitle': 'Ask-stock method', // 【页面】设置-
  'settings.agentBackendSingleOnly': 'Codex local Agent currently supports single-agent Chat only. This action changes the page draft; click Save to apply it.', // 【页面】设置-
  'settings.agentBackendSingleOnlyTitle': 'Switch to Single Agent', // 【页面】设置-
  'settings.agentBackendStatus': 'Ask-stock runtime status', // 【页面】设置-
  'settings.agentBackendStatusDescription': 'This check only confirms that the current settings, local Codex command, and required ask-stock protocol allow an attempt. It does not sign in, call a model, or read stock data. Actual execution is confirmed when you send a question.', // 【页面】设置-
  'settings.agentBackendTechnicalDetails': 'Technical details', // 【页面】设置-
  'settings.agentBackendUnavailableDescription': 'The selected ask-stock method is currently unavailable. Review the settings and try again.', // 【页面】设置-
  'settings.agentBackendUseSingle': 'Switch to Single Agent', // 【页面】设置-
  'settings.agentBackendVersion': 'Version', // 【页面】设置-
  'settings.agentSettings': 'Agent settings', // 【页面】设置-
  'settings.alphaSift': 'AlphaSift screening', // 【页面】设置-
  'settings.alphaSiftDescription': 'Enable the built-in experimental AlphaSift screening capability.', // 【页面】设置-
  'settings.alphaSiftDisabled': 'Screening disabled', // 【页面】设置-
  'settings.alphaSiftEnabled': 'Screening enabled', // 【页面】设置-
  'settings.alphaSiftRisk': 'Experimental risk notice: screening results are for research and decision support only and are not investment advice. Markets involve risk; trading decisions and results are your responsibility.', // 【页面】设置-
  'settings.alphaSiftSummary': 'When enabled, the left navigation shows Screening. Strategies and candidates come from AlphaSift; HRS adds quotes, fundamentals, and news context.', // 【页面】设置-
  'settings.authCurrentPassword': 'Current admin password', // 【页面】设置-
  'settings.authDescription': 'Manage admin password authentication to protect system settings.', // 【页面】设置-
  'settings.authDisabled': 'Disabled', // 【页面】设置-
  'settings.authEnabled': 'Enabled', // 【页面】设置-
  'settings.authFailure': 'Authentication settings failed', // 【页面】设置-
  'settings.authHelperDefault': 'Admin authentication protects Web settings and API endpoints from unauthorized access.', // 【页面】设置-
  'settings.authHelperEnabled': 'Admin authentication is enabled. Use Change password below to update it.', // 【页面】设置-
  'settings.authHelperNoPassword': 'No password has been set yet. Set an initial admin password before enabling authentication.', // 【页面】设置-
  'settings.authHelperPasswordRetained': 'The previous admin password was retained. Enter it to re-enable authentication quickly.', // 【页面】设置-
  'settings.authHelperTurnOff': 'If the current session is still valid, you can disable authentication directly. Otherwise, enter the current admin password.', // 【页面】设置-
  'settings.authPasswordHintOff': 'Identity verification may be required before disabling authentication', // 【页面】设置-
  'settings.authPasswordHintRetained': 'Enter the old password to reactivate authentication', // 【页面】设置-
  'settings.authPasswordPlaceholder': 'Enter current password', // 【页面】设置-
  'settings.authRequiredPassword': 'A new password is required', // 【页面】设置-
  'settings.authSetPassword': 'Set admin password', // 【页面】设置-
  'settings.authSetPasswordPlaceholder': 'Enter a new password (at least 6 characters)', // 【页面】设置-
  'settings.authStatus': 'Admin authentication', // 【页面】设置-
  'settings.authSuccessDisabled': 'Authentication disabled', // 【页面】设置-
  'settings.authSuccessUpdated': 'Authentication settings updated', // 【页面】设置-
  'settings.authTitle': 'Authentication and login protection', // 【页面】设置-
  'settings.categoryNavDescription': 'System settings and authentication capabilities grouped by module.', // 【页面】设置-
  'settings.categoryNavTitle': 'Categories', // 【页面】设置-
  'settings.dataSourceSectionTitle': 'Unified data source settings', // 【页面】设置-
  'settings.dataSourceSectionDescription': 'Review the local StockDB status plus the primary-source and fallback strategy for K-line, stock info, and code search.', // 【页面】设置-
  'settings.dataSourceStatusLabel': 'Local source status', // 【页面】设置-
  'settings.dataSourceBaseUrlLabel': 'Service URL', // 【页面】设置-
  'settings.dataSourcePrimarySourcesLabel': 'Primary sources', // 【页面】设置-
  'settings.dataSourceFallbackLabel': 'Auto fallback', // 【页面】设置-
  'settings.dataSourceKlineLabel': 'K-line', // 【页面】设置-
  'settings.dataSourceStockInfoLabel': 'Stock info', // 【页面】设置-
  'settings.dataSourceCodeSearchLabel': 'Code search', // 【页面】设置-
  'settings.dataSourceOpenStockData': 'Open local market view', // 【页面】设置-
  'settings.changePasswordConfirm': 'Confirm new password', // 【页面】设置-
  'settings.changePasswordConfirmPlaceholder': 'Enter the new password again', // 【页面】设置-
  'settings.changePasswordCurrent': 'Current password', // 【页面】设置-
  'settings.changePasswordCurrentPlaceholder': 'Enter current password', // 【页面】设置-
  'settings.changePasswordDescription': 'Update the current admin login password. Use the new password for future logins.', // 【页面】设置-
  'settings.changePasswordFailure': 'Password change failed', // 【页面】设置-
  'settings.changePasswordNew': 'New password', // 【页面】设置-
  'settings.changePasswordNewHint': 'At least 6 characters.', // 【页面】设置-
  'settings.changePasswordNewPlaceholder': 'Enter new password', // 【页面】设置-
  'settings.changePasswordRequiredCurrent': 'Enter the current password', // 【页面】设置-
  'settings.changePasswordRequiredNew': 'Enter a new password', // 【页面】设置-
  'settings.changePasswordSave': 'Save new password', // 【页面】设置-
  'settings.changePasswordShort': 'New password must be at least 6 characters', // 【页面】设置-
  'settings.changePasswordSuccess': 'Password changed', // 【页面】设置-
  'settings.changePasswordSuccessMessage': 'The admin password was updated.', // 【页面】设置-
  'settings.changePasswordTitle': 'Change password', // 【页面】设置-
  'settings.checkDesktopUpdate': 'Check for updates', // 【页面】设置-
  'settings.checkingDesktopUpdate': 'Checking...', // 【页面】设置-
  'settings.configBackup': 'Configuration backup', // 【页面】设置-
  'settings.configBackupDescription': 'Export the saved .env backup or restore configuration from a backup file. Importing overwrites keys present in the backup and reloads immediately.', // 【页面】设置-
  'settings.currentCategoryEmptyDescription': 'This category has no editable fields. Switch categories on the left to view other system settings.', // 【页面】设置-
  'settings.currentCategoryEmptyTitle': 'No fields in this category', // 【页面】设置-
  'settings.desktopCheckError': 'Update check failed', // 【页面】设置-
  'settings.desktopChecking': 'Checking for updates', // 【页面】设置-
  'settings.desktopCurrentNoStatus': 'No update status yet. The app checks in the background after startup.', // 【页面】设置-
  'settings.desktopDownload': 'Open release', // 【页面】设置-
  'settings.desktopDownloaded': 'Update downloaded', // 【页面】设置-
  'settings.desktopDownloading': 'Downloading update', // 【页面】设置-
  'settings.desktopInstall': 'Restart to install', // 【页面】设置-
  'settings.desktopInstalling': 'Installing update', // 【页面】设置-
  'settings.desktopLatest': 'latest version', // 【页面】设置-
  'settings.desktopManualUnsupported': 'This desktop runtime does not support automatic update installation. Open the release page to update manually.', // 【页面】设置-
  'settings.desktopUpToDate': 'Up to date', // 【页面】设置-
  'settings.desktopUpToDateMessage': 'The desktop app is already up to date.', // 【页面】设置-
  'settings.desktopUpdate': 'Desktop update', // 【页面】设置-
  'settings.desktopUpdateAvailable': 'New version available', // 【页面】设置-
  'settings.desktopUpdateCheckingMessage': 'Checking GitHub Releases for available versions.', // 【页面】设置-
  'settings.desktopUpdateDescription': 'After startup, the app checks GitHub Releases for the latest stable version. The Windows installer build downloads updates in the background and silently restarts to install after confirmation.', // 【页面】设置-
  'settings.desktopUpdateDownloadedMessage': 'The new version has been downloaded. Restart the app to finish installation.', // 【页面】设置-
  'settings.desktopUpdateDownloadingMessage': 'Downloading the desktop update in the background{percent}.', // 【页面】设置-
  'settings.desktopUpdateErrorMessage': 'Unable to complete the update check. Try again later.', // 【页面】设置-
  'settings.desktopUpdateInstallingMessage': 'Restarting and installing the update.', // 【页面】设置-
  'settings.desktopUpdateMessage': 'Current {current}, latest {latest}. {message}', // 【页面】设置-
  'settings.desktopUpdateReleaseMessage': 'Open GitHub Releases to download the update.', // 【页面】设置-
  'settings.diagnosticHintWeb': 'Check the browser developer console and backend logs, and provide the release version, browser version, and trigger path.', // 【页面】设置-
  'settings.disableAlphaSift': 'Disable screening', // 【页面】设置-
  'settings.disableAuth': 'Disable authentication', // 【页面】设置-
  'settings.disabledAlphaSiftSuccess': 'AlphaSift screening disabled.', // 【页面】设置-
  'settings.disabledAuthBackupWarning': 'The Web app is not protected by admin authentication, so .env export/import is disabled. Set ADMIN_AUTH_ENABLED=true and sign in as admin before using it.', // 【页面】设置-
  'settings.disablingAlphaSift': 'Disabling...', // 【页面】设置-
  'settings.enableAlphaSift': 'Enable screening', // 【页面】设置-
  'settings.enableAuth': 'Enable authentication', // 【页面】设置-
  'settings.enabledAlphaSiftSuccess': 'AlphaSift screening enabled.', // 【页面】设置-
  'settings.enablingAlphaSift': 'Enabling...', // 【页面】设置-
  'settings.envDockerNote': 'In Docker deployments, --env-file and Compose env_file inject environment variables only at startup. This export/import area uses the backend active .env file. To keep WebUI-saved values across container rebuilds, point ENV_FILE to a writable data-volume file such as /app/data/runtime.env and avoid keeping same-name old values in the startup environment.', // 【页面】设置-
  'settings.envExportNote': 'Exports include only currently saved configuration, not unsaved local drafts on the page.', // 【页面】设置-
  'settings.envExported': 'Saved .env backup exported.', // 【页面】设置-
  'settings.envImported': '.env backup imported and configuration reloaded.', // 【页面】设置-
  'settings.envImportedRefreshFailedMessage': 'The backup was imported, but configuration reload failed. Reload the page manually.', // 【页面】设置-
  'settings.envImportedRefreshFailedRaw': 'Env import succeeded but config refresh failed', // 【页面】设置-
  'settings.envImportedRefreshFailedTitle': 'Config imported but refresh failed', // 【页面】设置-
  'settings.exportEnv': 'Export .env', // 【页面】设置-
  'settings.exportingEnv': 'Exporting...', // 【页面】设置-
  'settings.fallbackVersionWarning': 'This build has no release version and is shown as development. Use the revision and build time to verify whether the static assets are current.', // 【页面】设置-
  'settings.fieldAddKey': 'Add key', // 【页面】设置-
  'settings.fieldDelete': 'Delete', // 【页面】设置-
  'settings.fieldSensitiveHint': 'Sensitive content is hidden by default. Click the eye icon to reveal plaintext.', // 【页面】设置-
  'settings.fieldSensitiveMultiHint': ' Multiple inputs can be added or removed.', // 【页面】设置-
  'settings.generationBackendConcurrency': 'Concurrency {count}', // 【页面】设置-
  'settings.generationBackendFallback': 'Fallback backend', // 【页面】设置-
  'settings.generationBackendGenerationOnly': 'Generation only', // 【页面】设置-
  'settings.generationBackendHealthFailed': 'Check failed', // 【页面】设置-
  'settings.generationBackendHealthPassed': 'Check passed', // 【页面】设置-
  'settings.generationBackendHealthSkipped': 'Skipped', // 【页面】设置-
  'settings.generationBackendLiteLLMDescription': 'This backend is used for report generation. Ask-stock tool calls still use the LiteLLM Agent path.', // 【页面】设置-
  'settings.generationBackendLocalCliDescription': 'Local CLI is only used for reports and text generation. It does not support ask-stock tool calls.', // 【页面】设置-
  'settings.generationBackendNeedsAction': 'Needs action', // 【页面】设置-
  'settings.generationBackendPrimary': 'Primary backend', // 【页面】设置-
  'settings.generationBackendRefresh': 'Refresh', // 【页面】设置-
  'settings.generationBackendRefreshing': 'Refreshing', // 【页面】设置-
  'settings.generationBackendRunnable': 'Ready to try', // 【页面】设置-
  'settings.generationBackendSmokeFailed': 'Smoke test failed', // 【页面】设置-
  'settings.generationBackendSmokePassed': 'Smoke test passed', // 【页面】设置-
  'settings.generationBackendSmokePassedMessage': 'Generation backend smoke test passed.', // 【页面】设置-
  'settings.generationBackendSmokeTest': 'JSON smoke test', // 【页面】设置-
  'settings.generationBackendSmokeTesting': 'Testing', // 【页面】设置-
  'settings.generationBackendStatus': 'Generation backend status', // 【页面】设置-
  'settings.generationBackendStatusDescription': 'The quick check only reads configuration and checks whether the local CLI executable is visible. Run the JSON smoke test to verify a real request.', // 【页面】设置-
  'settings.generationBackendToolsSupported': 'Tool calls', // 【页面】设置-
  'settings.helpClose': 'Close configuration help', // 【页面】设置-
  'settings.helpExamples': 'Examples', // 【页面】设置-
  'settings.helpImpact': 'Impact', // 【页面】设置-
  'settings.helpNotes': 'Notes', // 【页面】设置-
  'settings.helpPurpose': 'Usage', // 【页面】设置-
  'settings.helpRelatedDocs': 'Related docs', // 【页面】设置-
  'settings.helpTooltip': 'View configuration help', // 【页面】设置-
  'settings.helpValueNotes': 'Values', // 【页面】设置-
  'settings.importConfirmContinue': 'Continue import', // 【页面】设置-
  'settings.importConfirmMessage': 'This page has unsaved local edits. Continuing will discard those drafts and immediately update saved configuration with keys from the backup.', // 【页面】设置-
  'settings.importConfirmTitle': 'Import overwrites current drafts', // 【页面】设置-
  'settings.importEnv': 'Import .env', // 【页面】设置-
  'settings.importingEnv': 'Importing...', // 【页面】设置-
  'settings.intelligentImport': 'Smart import', // 【页面】设置-
  'settings.intelligentImportChooseFile': 'Choose file', // 【页面】设置-
  'settings.intelligentImportChooseImage': 'Choose image', // 【页面】设置-
  'settings.intelligentImportClear': 'Clear', // 【页面】设置-
  'settings.intelligentImportConfigUpdated': 'Configuration changed. Click "Merge into watchlist" again.', // 【页面】设置-
  'settings.intelligentImportDescription': 'Extract stock codes from images, files, or clipboard text and merge them into the watchlist.', // 【页面】设置-
  'settings.intelligentImportFileSizeError': 'Files must be 2MB or smaller', // 【页面】设置-
  'settings.intelligentImportHint': 'Image recognition requires a configured Vision model. Review parsed results before merging them into the watchlist.', // 【页面】设置-
  'settings.intelligentImportImageSizeError': 'Images must be 5MB or smaller', // 【页面】设置-
  'settings.intelligentImportImageTypeError': 'Images must be JPG, PNG, WebP, or GIF', // 【页面】设置-
  'settings.intelligentImportLoadConfigFirst': 'Load configuration before merging', // 【页面】设置-
  'settings.intelligentImportMergeFailed': 'Merge save failed', // 【页面】设置-
  'settings.intelligentImportMergeToWatchlist': 'Merge into watchlist', // 【页面】设置-
  'settings.intelligentImportParse': 'Parse', // 【页面】设置-
  'settings.intelligentImportParseFailed': 'Parse failed', // 【页面】设置-
  'settings.intelligentImportPastePlaceholder': 'Or paste text copied from CSV/Excel...', // 【页面】设置-
  'settings.intelligentImportRateLimited': 'Too many requests. Try again later.', // 【页面】设置-
  'settings.intelligentImportRecognitionFailed': 'Recognition failed. Try again.', // 【页面】设置-
  'settings.intelligentImportReviewWarning': 'Review each item before merging. High-confidence items are selected by default; medium/low confidence items need manual confirmation.', // 【页面】设置-
  'settings.intelligentImportSelectionSummary': '{valid} mergeable, {checked} selected', // 【页面】设置-
  'settings.intelligentImportSupportedInputs': 'Images, CSV/Excel files, and clipboard text', // 【页面】设置-
  'settings.intelligentImportTextSizeError': 'Pasted text must be 100KB or smaller', // 【页面】设置-
  'settings.intelligentImportTimeout': 'Request timed out. Check the network and retry.', // 【页面】设置-
  'settings.keepAuthDisabled': 'Keep disabled', // 【页面】设置-
  'settings.keepAuthEnabled': 'Keep enabled', // 【页面】设置-
  'settings.llmAccess': 'AI model access', // 【页面】设置-
  'settings.llmAccessDescription': 'Manage model channels, base URLs, API keys, primary models, and fallbacks.', // 【页面】设置-
  'settings.notificationSettings': 'Notification settings', // 【页面】设置-
  'settings.notificationTest': 'Notification test', // 【页面】设置-
  'settings.notificationTestBody': 'Body', // 【页面】设置-
  'settings.notificationTestChannel': 'Channel', // 【页面】设置-
  'settings.notificationTestContent': 'This is a test notification from the HRS Web settings page.', // 【页面】设置-
  'settings.notificationTestDescription': 'Send a real test notification using the current page draft. This test does not save configuration.', // 【页面】设置-
  'settings.notificationTestFailure': 'Test failed', // 【页面】设置-
  'settings.notificationTestSend': 'Send test', // 【页面】设置-
  'settings.notificationTestSuccess': 'Test succeeded', // 【页面】设置-
  'settings.notificationTestTimeout': 'Timeout seconds', // 【页面】设置-
  'settings.notificationTestTitle': 'Title', // 【页面】设置-
  'settings.notificationTestTitleValue': 'HRS notification test', // 【页面】设置-
  'settings.notificationTesting': 'Testing...', // 【页面】设置-
  'settings.pageDescription': 'Manage models, data sources, notifications, security authentication, and import capabilities.', // 【页面】设置-
  'settings.pageTitle': 'System settings', // 【页面】设置-
  'settings.eyebrow': 'Settings', // 【页面】设置-System settings header eyebrow
  'settings.pageTitleDocument': 'System settings - HRS', // 【页面】设置-
  'settings.promptCacheAdvancedDescription': 'Maintain provider prompt-cache telemetry, active hints, and sanitized diagnostics. Defaults are suitable for normal use.', // 【页面】设置-
  'settings.promptCacheAdvancedTitle': 'Provider Prompt Cache advanced settings', // 【页面】设置-
  'settings.reload': 'Reload', // 【页面】设置-
  'settings.reset': 'Reset', // 【页面】设置-
  'settings.revert': 'Revert', // 【页面】设置-
  'settings.saveConfig': 'Save configuration', // 【页面】设置-
  'settings.saveConfigWithCount': 'Save configuration ({count})', // 【页面】设置-
  'settings.saveRetry': 'Retry save', // 【页面】设置-
  'settings.saving': 'Saving...', // 【页面】设置-
  'settings.schedulerAddTime': 'Add time', // 【页面】设置-
  'settings.schedulerDescription': 'Configure the daily automatic analysis times. After saving, long-running Web/API/Desktop processes apply the new schedule.', // 【页面】设置-
  'settings.schedulerDisabled': 'Disabled', // 【页面】设置-
  'settings.schedulerEffectiveTimes': 'Active times', // 【页面】设置-
  'settings.schedulerEnable': 'Enable scheduled task', // 【页面】设置-
  'settings.schedulerEnableDescription': 'When enabled, analysis runs automatically at the times below.', // 【页面】设置-
  'settings.schedulerEnabled': 'Enabled', // 【页面】设置-
  'settings.schedulerLastError': 'Last error', // 【页面】设置-
  'settings.schedulerLastSuccess': 'Last success', // 【页面】设置-
  'settings.schedulerNextRun': 'Next run', // 【页面】设置-
  'settings.schedulerRefresh': 'Refresh status', // 【页面】设置-
  'settings.schedulerRefreshing': 'Refreshing...', // 【页面】设置-
  'settings.schedulerRemoveTime': 'Remove time', // 【页面】设置-
  'settings.schedulerRunAccepted': 'Run request submitted.', // 【页面】设置-
  'settings.schedulerRunNow': 'Run once now', // 【页面】设置-
  'settings.schedulerRunning': 'Running', // 【页面】设置-
  'settings.schedulerRunningNow': 'Running...', // 【页面】设置-
  'settings.schedulerStatus': 'Current status', // 【页面】设置-
  'settings.schedulerTimeInputAria': 'Scheduled time {index}', // 【页面】设置-
  'settings.schedulerTimes': 'Scheduled times', // 【页面】设置-
  'settings.schedulerTitle': 'Scheduled task', // 【页面】设置-
  'settings.setupGuideAddStocks': 'Manage watchlist', // 【页面】设置-
  'settings.setupGuideCheckingSummary': 'Reading configuration status. Missing items and the smoke-run entry appear after the check completes.', // 【页面】设置-
  'settings.setupGuideCheckingTitle': 'Checking first-run setup', // 【页面】设置-
  'settings.setupGuideCompleteTitle': 'Base setup is ready for minimal analysis', // 【页面】设置-
  'settings.setupGuideConfigureLlm': 'Configure models', // 【页面】设置-
  'settings.setupGuideConfigureNotification': 'Configure notifications', // 【页面】设置-
  'settings.setupGuideDescription': 'Check the watchlist, model channels, and notification setup for a minimal analysis flow, then submit a brief smoke run.', // 【页面】设置-
  'settings.setupGuideHiddenDescription': 'Reopen it when you want to recheck base settings, models, and notification setup.', // 【页面】设置-
  'settings.setupGuideHiddenTitle': 'First-run setup check is hidden', // 【页面】设置-
  'settings.setupGuideHide': 'Hide for now', // 【页面】设置-
  'settings.setupGuideIncompleteTitle': 'Some base setup still needs attention', // 【页面】设置-
  'settings.setupGuideMissingSummary': '{count} item(s) still need action: {labels}', // 【页面】设置-
  'settings.setupGuideOpen': 'Open check', // 【页面】设置-
  'settings.setupGuideReadySummary': 'All required items are ready. Run a brief analysis to verify the flow.', // 【页面】设置-
  'settings.setupGuideRefresh': 'Refresh check', // 【页面】设置-
  'settings.setupGuideRefreshing': 'Refreshing...', // 【页面】设置-
  'settings.setupGuideRunSmoke': 'Brief smoke run', // 【页面】设置-
  'settings.setupGuideSmokeAccepted': 'Submitted a brief analysis for {stock}.', // 【页面】设置-
  'settings.setupGuideSmokeAcceptedWithTask': 'Submitted a brief analysis for {stock}: {taskId}', // 【页面】设置-
  'settings.setupGuideSmokeNeedsStock': 'Add at least one watchlist stock before running the smoke check.', // 【页面】设置-
  'settings.setupGuideSmokeNotReady': 'Complete the required setup before running the smoke check.', // 【页面】设置-
  'settings.setupGuideSmokeRunning': 'Submitting...', // 【页面】设置-
  'settings.setupGuideSmokeUnavailableTitle': 'Smoke check unavailable', // 【页面】设置-
  'settings.setupGuideTitle': 'First-run setup check', // 【页面】设置-
  'settings.setupGuideUnknownSummary': 'The setup status check failed. You can still review settings and refresh the check later.', // 【页面】设置-
  'settings.setupGuideUnknownTitle': 'Setup status is unavailable', // 【页面】设置-
  'settings.setupStatusConfigured': 'Configured', // 【页面】设置-
  'settings.setupStatusInherited': 'Inherited', // 【页面】设置-
  'settings.setupStatusNeedsAction': 'Needs action', // 【页面】设置-
  'settings.setupStatusOptional': 'Optional', // 【页面】设置-
  'settings.updateBuildDescription': 'After rebuilding the frontend or Docker image, the revision and build time here update. Use them to confirm the current page assets are active.', // 【页面】设置-
  'settings.versionBuildTime': 'Build time', // 【页面】设置-
  'settings.versionDesktop': 'Desktop version', // 【页面】设置-
  'settings.versionInfo': 'Version info', // 【页面】设置-
  'settings.versionInfoDescription': 'Use this to confirm the current WebUI static assets are on the latest build.', // 【页面】设置-
  'settings.versionRevision': 'Revision', // 【页面】设置-
  'settings.versionWebui': 'WebUI version', // 【页面】设置-
  'settings.viewConfigItems': 'View fields', // 【页面】设置-
  // stockBar.*
  'stockBar.emptyDescription': 'Latest analysis results will be grouped by stock here after the first analysis.', // 【页面】个股工具条-
  'stockBar.emptyTitle': 'No stock records', // 【页面】个股工具条-
  'stockBar.loading': 'Loading stocks...', // 【页面】个股工具条-
  'stockBar.market': 'Market', // 【页面】个股工具条-
  'stockBar.title': 'Stocks', // 【页面】个股工具条-
  // stockTrend.*
  'stockTrend.allHistory': 'All history', // 【页面】个股趋势-
  'stockTrend.averageScore': 'Average {score}', // 【页面】个股趋势-
  'stockTrend.backToCurrentReport': 'Back to current report', // 【页面】个股趋势-
  'stockTrend.changePct': 'Change', // 【页面】个股趋势-
  'stockTrend.currentAdvice': 'Current view', // 【页面】个股趋势-
  'stockTrend.currentScore': 'Current score', // 【页面】个股趋势-
  'stockTrend.historyModelCount': '{count} historical models', // 【页面】个股趋势-
  'stockTrend.latestTime': 'Latest {time}', // 【页面】个股趋势-
  'stockTrend.loadFailed': 'Failed to load history trend', // 【页面】个股趋势-
  'stockTrend.loadMore': 'Load more', // 【页面】个股趋势-
  'stockTrend.loadedSummary': 'Loaded {loaded} / {total} · Newest first · Model: all', // 【页面】个股趋势-
  'stockTrend.loading': 'Loading same-stock history...', // 【页面】个股趋势-
  'stockTrend.loadingMore': 'Loading...', // 【页面】个股趋势-
  'stockTrend.model': 'Model', // 【页面】个股趋势-
  'stockTrend.modelCountSuffix': '{count} runs', // 【页面】个股趋势-
  'stockTrend.moreEmptyDescription': 'After multiple analyses, this view shows changes in opinions, score trends, and model records.', // 【页面】个股趋势-
  'stockTrend.moreEmptyTitle': 'No more same-stock history', // 【页面】个股趋势-
  'stockTrend.neverRecorded': 'Not recorded', // 【页面】个股趋势-
  'stockTrend.noModelTitle': 'No recorded model', // 【页面】个股趋势-
  'stockTrend.records': 'Historical analysis records', // 【页面】个股趋势-
  'stockTrend.reload': 'Reload', // 【页面】个股趋势-
  'stockTrend.report': 'View report', // 【页面】个股趋势-
  'stockTrend.result': 'Result', // 【页面】个股趋势-
  'stockTrend.score': 'Score', // 【页面】个股趋势-
  'stockTrend.stockPrice': 'Price', // 【页面】个股趋势-
  'stockTrend.table.action': 'Action', // 【页面】个股趋势-
  'stockTrend.time': 'Time', // 【页面】个股趋势-
  'stockTrend.title': 'History trend', // 【页面】个股趋势-
  'stockTrend.turnoverRate': 'Turnover', // 【页面】个股趋势-
  'stockTrend.volumeRatio': 'Volume ratio', // 【页面】个股趋势-
  'stockTrend.window30': 'Last 30 days', // 【页面】个股趋势-
  'stockTrend.window90': 'Last 90 days', // 【页面】个股趋势-
  // stockUnit.*
  'stockUnit.amountWanYi': 'T', // 【页面】个股单位-
  'stockUnit.amountYi': 'B', // 【页面】个股单位-
  'stockUnit.volumeHundredMillionLots': 'B', // 【页面】个股单位-
  'stockUnit.volumeTenThousandLots': 'M', // 【页面】个股单位-
  // usage.*
  'usage.breakdown': 'Breakdown', // 【页面】用量-
  'usage.callType.agent': 'Ask Agent', // 【页面】用量-
  'usage.callType.analysis': 'Stock analysis', // 【页面】用量-
  'usage.callType.marketReview': 'Market review', // 【页面】用量-
  'usage.callType.unknown': '{type}', // 【页面】用量-
  'usage.callTypeDetail': '{calls} calls · Prompt {prompt} · Completion {completion}', // 【页面】用量-
  'usage.callTypeTitle': 'Call type', // 【页面】用量-
  'usage.calls': '{count} calls', // 【页面】用量-
  'usage.completionTokens': 'Completion tokens', // 【页面】用量-
  'usage.completionTokensHint': 'Model output consumption', // 【页面】用量-
  'usage.dateRange': '{from} to {to}', // 【页面】用量-
  'usage.description': 'Inspect LLM call count, Prompt/Completion token consumption, model usage, and recent call details.', // 【页面】用量-
  'usage.emptyDescription': 'After an analysis, market review, or Ask call completes, model usage will appear here.', // 【页面】用量-
  'usage.emptyTitle': 'No token usage records', // 【页面】用量-
  'usage.error.message': 'Failed to load token usage data', // 【页面】用量-
  'usage.error.title': 'Failed to load token usage', // 【页面】用量-
  'usage.eyebrow': 'Usage', // 【页面】用量-
  'usage.maxSingleCall': 'Single-call peak', // 【页面】用量-
  'usage.modelUsage': 'Model usage', // 【页面】用量-
  'usage.modelUsageDescription': 'Token consumption, call count, and single-call peaks grouped by model.', // 【页面】用量-
  'usage.noRecentCalls': 'No recent call records', // 【页面】用量-
  'usage.period.all': 'All', // 【页面】用量-
  'usage.period.month': 'This month', // 【页面】用量-
  'usage.period.today': 'Today', // 【页面】用量-
  'usage.period.label': 'Time range', // 【页面】用量-
  'usage.promptTokens': 'Prompt tokens', // 【页面】用量-
  'usage.promptTokensHint': 'Input context consumption', // 【页面】用量-
  'usage.recentCalls': 'Recent calls', // 【页面】用量-
  'usage.recentCallsDescription': 'Latest 50 LLM token audit records.', // 【页面】用量-
  'usage.refresh': 'Refresh', // 【页面】用量-
  'usage.table.model': 'Model', // 【页面】用量-
  'usage.table.time': 'Time', // 【页面】用量-
  'usage.table.type': 'Type', // 【页面】用量-
  'usage.title': 'Token usage', // 【页面】用量-
  'usage.totalCalls': 'Calls', // 【页面】用量-
  'usage.totalCallsHint': 'Recorded LLM calls', // 【页面】用量-
  'usage.totalTokens': 'Total tokens', // 【页面】用量-
  // watchlist.*
  'watchlist.add': 'Add watchlist stock', // 【页面】自选-
  'watchlist.addPlaceholder': 'Add code, e.g. 600519', // 【页面】自选-
  'watchlist.analyzeAll': 'Analyze all', // 【页面】自选-
  'watchlist.analyzePending': 'Pending only', // 【页面】自选-
  'watchlist.analyzedToday': 'Analyzed today', // 【页面】自选-
  'watchlist.batchFailed': 'Watchlist batch submit failed', // 【页面】自选-
  'watchlist.batchIncompleteResponse': 'The batch API received {requested} stock(s) in this chunk but confirmed only {confirmed}; the response is incomplete', // 【页面】自选-
  'watchlist.batchPartiallySubmitted': 'Confirmed {accepted} submitted task(s) and {duplicates} already running; {unconfirmed} stock(s) remain unconfirmed. Further submission stopped and the task list was refreshed. Reason: {error}', // 【页面】自选-
  'watchlist.batchSubmitted': 'Submitted {accepted} task(s), {duplicates} already running', // 【页面】自选-
  'watchlist.emptyDescription': 'Add stocks here or from a report, then run the whole watchlist from one place.', // 【页面】自选-
  'watchlist.emptyTitle': 'No watchlist stocks', // 【页面】自选-
  'watchlist.listHint': 'Shown in watchlist order with today status', // 【页面】自选-
  'watchlist.loading': 'Loading watchlist...', // 【页面】自选-
  'watchlist.noPendingAnalyze': 'No watchlist stocks are pending today.', // 【页面】自选-
  'watchlist.noStocksAnalyze': 'Add watchlist stocks first.', // 【页面】自选-
  'watchlist.notAnalyzedToday': 'Not analyzed today', // 【页面】自选-
  'watchlist.pendingStatusUnavailable': 'Some watchlist today statuses are unknown. Refresh before submitting pending stocks.', // 【页面】自选-
  'watchlist.pendingToday': 'Pending today', // 【页面】自选-
  'watchlist.refresh': 'Refresh watchlist', // 【页面】自选-
  'watchlist.removeAria': 'Remove {code} from watchlist', // 【页面】自选-
  'watchlist.submitting': 'Submitting', // 【页面】自选-
  'watchlist.tabHistory': 'History', // 【页面】自选-
  'watchlist.tabToday': 'Today', // 【页面】自选-
  'watchlist.tabWatchlist': 'Watchlist', // 【页面】自选-
  'watchlist.taskRunning': 'Task {status}', // 【页面】自选-
  'watchlist.title': 'Watchlist', // 【页面】自选-
  'watchlist.todayCoverage': 'Today coverage', // 【页面】自选-
  'watchlist.todayEmptyDescription': 'After analyses finish today, stocks will appear here ranked by score.', // 【页面】自选-
  'watchlist.todayEmptyTitle': 'No analysis results today', // 【页面】自选-
  'watchlist.todayLoadErrorDescription': 'The full paginated history request failed. Refresh before viewing the ranking.', // 【页面】自选-
  'watchlist.todayLoadErrorTitle': 'Failed to load today ranking', // 【页面】自选-
  'watchlist.todaySortHint': 'Sorted by sentiment score first', // 【页面】自选-
  'watchlist.todayStatusLoading': 'Checking today status', // 【页面】自选-
  'watchlist.todayStatusUnavailable': 'Today status unknown', // 【页面】自选-
  'watchlist.todayTitle': 'Today', // 【页面】自选-
  'watchlist.topScore': 'Top score', // 【页面】自选-
  'watchlist.watchlistCoverage': 'Watchlist coverage' // 【页面】自选-

};

export default en;

