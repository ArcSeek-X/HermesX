/**
 * 英文（en）文案：component 命名空间。
 * 由 uiText-en.ts 按 uiText-zh/ 分片结构拆分，经 uiText-en/index.ts 聚合；key 与中文分片逐一对齐。
 */

export const componentEn = {
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
  'component.stockSearch.placeholder': 'Enter a stock code or name',
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
} as const;
