/**
 * 简体中文（zh）文案：组件 component 类别。
 * 由 uiText-zh.ts 按类别拆分，经 uiText-zh/index.ts 聚合；key 与三语主字典保持一致。
 */

export const componentZh = {
  // ---- 第 5 类 组件 component ----
  // component.LiveCalendar.*
  'component.LiveCalendar.allDay': '全天', // 日历事件全天标识
  'component.LiveCalendar.calendarType.FD': '经济数据', // 事件分类：经济数据指标
  'component.LiveCalendar.calendarType.FE': '大事件', // 事件分类：财经大事件
  'component.LiveCalendar.country': '国家', // List 视图列头：国家
  'component.LiveCalendar.drawer.actual': '公布', // 详情抽屉：公布值
  'component.LiveCalendar.drawer.forecast': '预期', // 详情抽屉：预期值
  'component.LiveCalendar.drawer.previous': '前值', // 详情抽屉：前值
  'component.LiveCalendar.drawer.source': '来源', // 详情抽屉：来源
  'component.LiveCalendar.drawer.sourceName': '华尔街见闻', // 详情抽屉：数据源名称（外链文案）
  'component.LiveCalendar.drawer.noSummary': '暂无详情内容', // 详情抽屉：事件无前瞻/正文时的占位提示
  'component.LiveCalendar.empty': '本月暂无日历事件', // 空态：当月无事件
  'component.LiveCalendar.emptyImportance': '没有符合重要级条件的事件，试试降低筛选条件', // 空态：重要级筛选无结果
  'component.LiveCalendar.filter.apply': '确认', // 筛选区域：确认按钮
  'component.LiveCalendar.filter.button': '筛选', // 筛选按钮（切换筛选区域展开）
  'component.LiveCalendar.filter.country': '国家/地区', // 筛选区域：国家 / 地区
  'component.LiveCalendar.filter.country.all': '全部国家/地区', // 筛选区域：国家下拉「全部」
  'component.LiveCalendar.filter.importance': '重要度', // 筛选区域：重要度多选
  'component.LiveCalendar.filter.importance.none': '无', // 筛选区域：重要度 0（数据源未提供重要度）
  'component.LiveCalendar.filter.keyword': '关键词', // 筛选区域：标题关键词
  'component.LiveCalendar.filter.keywordPlaceholder': '搜索新闻标题', // 筛选区域：关键词输入框占位符
  'component.LiveCalendar.filter.reset': '重置', // 筛选区域：重置按钮
  'component.LiveCalendar.filter.type': '类型', // 筛选区域：事件类型三态
  'component.LiveCalendar.filter.type.all': '全部', // 筛选区域：事件类型「全部」
  'component.LiveCalendar.importance': '重要级', // List 视图列头：重要级
  'component.LiveCalendar.includeEconomicData': '显示经济数据', // 是否显示 FD 经济数据开关
  'component.LiveCalendar.list.columns.time': '时间', // List 视图列头：时间
  'component.LiveCalendar.list.columns.title': '新闻标题', // List 视图列头：新闻标题
  'component.LiveCalendar.loading': '加载中…', // 组件内部月份切换中的加载文案
  'component.LiveCalendar.more': '更多信息', // 日历格子溢出折叠提示
  'component.LiveCalendar.nextMonth': '下月', // List 视图导航：下月
  'component.LiveCalendar.prevMonth': '上月', // List 视图导航：上月
  'component.LiveCalendar.today': '今天', // 月份切换：回到今天
  // component.runFlow.*
  'component.runFlow.drawerTitle': '运行流', // 运行流抽屉标题
  'component.runFlow.durationMinutes': '{value} 分钟', // 分钟耗时显示
  'component.runFlow.durationMs': '{value} ms', // 毫秒耗时显示
  'component.runFlow.durationSeconds': '{value} 秒', // 秒耗时显示
  'component.runFlow.edge.control': '控制', // 控制边类型
  'component.runFlow.edge.data': '数据', // 数据边类型
  'component.runFlow.edge.fallback': '降级回退', // 回退边类型
  'component.runFlow.edge.retry': '重试', // 重试边类型
  'component.runFlow.edgeLabel.details': '详情', // 详情边标签
  'component.runFlow.edgeLabel.invoke': '调用', // 调用边标签
  'component.runFlow.emptyDescription': '请选择一个活跃任务或历史报告查看运行流。', // 运行流空状态描述
  'component.runFlow.emptySnapshotDescription': '当前快照没有节点或事件；缺少 diagnostics 时会显示骨架或空状态。', // 运行流快照空描述
  'component.runFlow.emptySnapshotTitle': '暂无运行流细节', // 运行流快照空标题
  'component.runFlow.emptyTitle': '暂无运行流', // 运行流空状态标题
  'component.runFlow.errorTitle': '运行流加载失败', // 运行流加载失败标题
  'component.runFlow.events.count': '{count} 条事件', // 事件数量
  'component.runFlow.events.empty': '当前筛选下暂无事件。', // 事件空状态
  'component.runFlow.events.filter.all': '全部', // 全部事件筛选
  'component.runFlow.events.filter.cancelled': '取消', // 取消事件筛选
  'component.runFlow.events.filter.fallback': '降级回退/重试', // 回退重试事件筛选
  'component.runFlow.events.filter.important': '关键', // 关键事件筛选
  'component.runFlow.events.filter.problems': '失败/告警', // 失败告警事件筛选
  'component.runFlow.events.filters': '事件筛选', // 事件筛选标签
  'component.runFlow.events.openNode': '查看事件 {title} 关联节点', // 查看事件关联节点
  'component.runFlow.events.title': '事件流', // 事件流标题
  'component.runFlow.eyebrow': '运行流', // 运行流眉标
  'component.runFlow.graph.collapse': '收起', // 收起节点按钮
  'component.runFlow.graph.collapseNode': '收起 {label} 运行尝试', // 收起节点尝试
  'component.runFlow.graph.description': '自动分层展示入口、数据来源、分析引擎和产物链路。', // 运行拓扑图说明
  'component.runFlow.graph.expand': '展开', // 展开节点按钮
  'component.runFlow.graph.expandNode': '展开 {label} 运行尝试', // 展开节点尝试
  'component.runFlow.graph.nodeAria': '{label} 节点，状态 {status}', // 拓扑节点无障碍标签
  'component.runFlow.graph.startedAt': '开始', // 拓扑开始时间标签
  'component.runFlow.graph.title': '运行拓扑', // 运行拓扑图标题
  'component.runFlow.historyDrawerTitle': '{stock} 历史运行流', // 历史运行流抽屉标题
  'component.runFlow.loadingDescription': '正在读取任务快照、运行诊断和事件链路。', // 运行流加载说明
  'component.runFlow.loadingTitle': '正在加载运行流', // 运行流加载标题
  'component.runFlow.nodeDetails.attemptList': '运行尝试', // 运行尝试列表
  'component.runFlow.nodeDetails.attempts': '尝试次数', // 节点尝试次数
  'component.runFlow.nodeDetails.blockScores': '数据块评分', // 数据块评分
  'component.runFlow.nodeDetails.close': '关闭节点详情', // 关闭节点详情按钮
  'component.runFlow.nodeDetails.collapseAttempts': '收起尝试', // 收起尝试按钮
  'component.runFlow.nodeDetails.column.duration': '耗时', // 尝试列表耗时列
  'component.runFlow.nodeDetails.column.name': '名称', // 尝试列表名称列
  'component.runFlow.nodeDetails.column.records': '记录', // 尝试列表记录列
  'component.runFlow.nodeDetails.column.status': '状态', // 尝试列表状态列
  'component.runFlow.nodeDetails.column.time': '时间', // 尝试列表时间列
  'component.runFlow.nodeDetails.contextBlocks': '上下文输入', // 上下文输入块
  'component.runFlow.nodeDetails.contextQuality': '上下文质量', // 上下文质量标签
  'component.runFlow.nodeDetails.count.available': '可用', // 可用数量
  'component.runFlow.nodeDetails.count.degraded': '部分降级', // 降级数量
  'component.runFlow.nodeDetails.count.fallback': '降级回退', // 回退数量
  'component.runFlow.nodeDetails.count.missing': '缺失', // 缺失数量
  'component.runFlow.nodeDetails.count.partial': '部分', // 部分数量
  'component.runFlow.nodeDetails.count.skipped': '跳过', // 跳过数量
  'component.runFlow.nodeDetails.duration': '耗时', // 节点耗时标签
  'component.runFlow.nodeDetails.empty': '选择一个节点查看详情。', // 节点详情空状态
  'component.runFlow.nodeDetails.endedAt': '结束时间', // 节点结束时间
  'component.runFlow.nodeDetails.expandAttempts': '展开尝试', // 展开尝试按钮
  'component.runFlow.nodeDetails.kind': '类型', // 节点类型标签
  'component.runFlow.nodeDetails.metadata': '元数据', // 节点元数据
  'component.runFlow.nodeDetails.overallScore': '综合评分', // 综合评分
  'component.runFlow.nodeDetails.provider': '提供方', // 节点提供方标签
  'component.runFlow.nodeDetails.qualityLevel': '等级', // 质量等级
  'component.runFlow.nodeDetails.recordCount': '记录数', // 节点记录数
  'component.runFlow.nodeDetails.startedAt': '开始时间', // 节点开始时间
  'component.runFlow.nodeDetails.title': '节点详情', // 节点详情标题
  'component.runFlow.nodeDetails.version': '版本', // 节点版本标签
  'component.runFlow.nodeKind.analysis': '分析', // 分析节点类型
  'component.runFlow.nodeKind.artifact': '产物', // 产物节点类型
  'component.runFlow.nodeKind.dataSource': '数据源', // 数据源节点类型
  'component.runFlow.nodeKind.entry': '入口', // 入口节点类型
  'component.runFlow.nodeKind.model': '模型', // 模型节点类型
  'component.runFlow.nodeKind.notification': '通知', // 通知节点类型
  'component.runFlow.nodeKind.queue': '队列', // 队列节点类型
  'component.runFlow.open': '查看运行流', // 查看运行流入口
  'component.runFlow.openHistoryAria': '查看历史记录 {recordId} 运行流', // 查看历史运行流无障碍标签
  'component.runFlow.refresh': '刷新', // 运行流刷新按钮
  'component.runFlow.refreshing': '刷新中', // 运行流刷新中状态
  'component.runFlow.retry': '重新加载', // 运行流重新加载
  'component.runFlow.severity.danger': '危险', // 危险级别
  'component.runFlow.severity.info': '信息', // 信息级别
  'component.runFlow.severity.success': '成功', // 成功级别
  'component.runFlow.severity.warning': '告警', // 告警级别
  'component.runFlow.status.cancelRequested': '请求取消', // 运行流请求取消状态
  'component.runFlow.status.cancelled': '已取消', // 运行流已取消状态
  'component.runFlow.status.degraded': '部分降级', // 运行流降级状态
  'component.runFlow.status.failed': '失败', // 运行流失败状态
  'component.runFlow.status.fallback': '降级回退', // 运行流回退状态
  'component.runFlow.status.pending': '等待中', // 运行流等待状态
  'component.runFlow.status.running': '运行中', // 运行流运行状态
  'component.runFlow.status.skipped': '已跳过', // 运行流已跳过状态
  'component.runFlow.status.success': '成功', // 运行流成功状态
  'component.runFlow.status.timeout': '超时', // 运行流超时状态
  'component.runFlow.status.unknown': '未知', // 运行流未知状态
  'component.runFlow.summary.dataSources': '数据源', // 数据源数量
  'component.runFlow.summary.elapsed': '总耗时', // 运行流总耗时
  'component.runFlow.summary.failedAttempts': '失败尝试', // 失败尝试次数
  'component.runFlow.summary.fallbackCount': '降级回退/重试', // 回退重试次数
  'component.runFlow.summary.generatedAt': '生成时间', // 运行流生成时间
  'component.runFlow.summary.model': '模型', // 模型标识
  'component.runFlow.summary.task': 'Task', // 任务标识
  'component.runFlow.summary.trace': 'Trace', // 追踪标识
  'component.runFlow.taskDrawerTitle': '{stock} 运行流', // 任务运行流抽屉标题
  'component.runFlow.title': '数据流与信息流', // 运行流主标题
  'component.runFlow.valueUnavailable': '未记录', // 运行流值不可用
  // component.stockSearch.*
  'component.stockSearch.placeholder': '输入股票代码或名称', // 股票搜索框默认占位符
  // component.taskPanel.*
  'component.taskPanel.cancelRequested': '请求取消', // 任务请求取消状态
  'component.taskPanel.cancelRequestedAria': '任务请求取消', // 请求取消无障碍标签
  'component.taskPanel.cancelled': '已取消', // 任务已取消状态
  'component.taskPanel.diagnostics': '运行诊断', // 运行诊断按钮
  'component.taskPanel.openRunFlow': '查看运行流', // 查看运行流按钮
  'component.taskPanel.openRunFlowAria': '查看 {stock} 运行流', // 查看运行流无障碍标签
  'component.taskPanel.pending': '等待中', // 任务等待中状态
  'component.taskPanel.pendingAria': '任务等待中', // 任务等待中无障碍标签
  'component.taskPanel.pendingTasks': '{count} 等待中', // 等待中任务数量
  'component.taskPanel.processing': '分析中', // 任务分析中状态
  'component.taskPanel.processingAria': '任务进行中', // 任务进行中无障碍标签
  'component.taskPanel.processingTasks': '{count} 进行中', // 进行中任务数量
  'component.taskPanel.statusAria': '任务状态：{status}', // 任务状态无障碍标签
  'component.taskPanel.title': '分析任务', // 任务面板标题

} as const;
