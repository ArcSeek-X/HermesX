/**
 * @file uiText-zh.ts
 * @description 中文（zh）界面文案配置，是所有 i18n 键值的真源（source of truth）
 * @module i18n
 */

const zh = {
  'common.cancel': '取消', // 通用取消按钮文案
  'common.close': '关闭', // 通用关闭按钮文案
  'common.closeDrawer': '关闭抽屉', // 关闭抽屉组件
  'common.confirm': '确定', // 通用确认按钮文案
  'common.delete': '删除', // 通用删除按钮文案
  'common.deleting': '删除中', // 删除进行中状态
  'common.details': '查看详情', // 查看详情入口
  'common.disabled': '未启用', // 功能未启用状态
  'common.enabled': '已启用', // 功能已启用状态
  'common.failure': '失败', // 通用失败状态
  'common.hideContent': '隐藏内容', // 隐藏敏感内容
  'common.itemsCount': '{count}只', // 条目数量统计
  'common.loading': '正在加载', // 通用加载中文案
  'common.noData': '暂无数据', // 通用空数据提示
  'common.processing': '处理中...', // 通用处理中状态
  'common.readOnly': '只读', // 只读模式标识
  'common.retry': '重试', // 通用重试按钮
  'common.selectAllCurrent': '全选当前', // 全选当前列表项
  'common.selectPlaceholder': '请选择', // 选择器占位符
  'common.selectedCount': '已选 {count}', // 已选数量统计
  'common.sensitive': '敏感', // 敏感字段标识
  'common.showContent': '显示内容', // 显示敏感内容
  'common.success': '成功', // 通用成功状态
  'common.copy': '复制', // 复制按钮文案
  'common.copied': '已复制!', // 复制成功提示

  'language.current': '中文', // 当前界面语言名称
  'language.english': 'English', // 英文语言选项
  'language.short.en': 'EN', // 英文语言简写
  'language.short.zh': '中', // 中文语言简写
  'language.toggle': '切换界面语言', // 切换语言按钮提示
  'language.uiLanguage': '界面语言', // 界面语言设置项标题

  'theme.dark': '深色', // 深色主题名称
  'theme.light': '浅色', // 浅色主题名称
  'theme.menu': '主题模式', // 主题模式菜单标题
  'theme.system': '跟随系统', // 跟随系统主题
  'theme.theme': '主题', // 主题通用标签
  'theme.toggle': '切换主题', // 切换主题按钮提示
  'theme.primary': '主色', // 主题主色配置标签
  'theme.reset': '重置', // 重置主题主色按钮
  'theme.save': '保存', // 保存主题设置按钮

  'layout.appFallbackDescription': 'Web workspace', // 应用回退描述文案
  'layout.appFallbackTitle': 'HermesX', // 应用回退标题
  'layout.collapseSidebar': '折叠侧边栏', // 折叠侧边栏按钮
  'layout.desktopSidebar': '桌面侧边导航', // 桌面端侧边栏标签
  'layout.expandSidebar': '展开侧边栏', // 展开侧边栏按钮
  'layout.mainNav': '主导航', // 主导航区域标签
  'layout.nav.alerts': '告警', // 告警导航项
  'layout.nav.backtest': '回测', // 回测导航项
  'layout.nav.chat': '问股', // 问股导航项
  'layout.nav.decisionSignals': 'AI 建议', // AI 建议导航项
  'layout.nav.dashboard': '总览', // 总览导航项
  'layout.nav.home': '首页', // 首页导航项
  'layout.nav.kline': 'K 线', // K 线导航项
  'layout.nav.sectorAnalysis': '板块', // 板块分析导航项
  'layout.nav.stockCloud': '个股云图', // 个股云图导航项
  'layout.nav.portfolio': '持仓', // 持仓导航项
  'layout.nav.settings': '设置', // 设置导航项
  'layout.nav.screening': '选股', // 选股导航项
  'layout.nav.usage': '用量', // 用量导航项
  'layout.navMenu': '导航菜单', // 导航菜单标签
  'layout.newChatMessage': '问股有新消息', // 问股新消息提示
  'layout.openNav': '打开导航菜单', // 打开导航菜单提示
  'layout.route.alerts.description': '规则、触发记录与通知尝试', // 告警路由描述
  'layout.route.alerts.title': '告警', // 告警路由标题
  'layout.route.backtest.description': '回测任务与结果浏览', // 回测路由描述
  'layout.route.backtest.title': '回测', // 回测路由标题
  'layout.route.chat.description': '多轮策略问答与历史会话管理', // 问股路由描述
  'layout.route.chat.title': '问股', // 问股路由标题
  'layout.route.decisionSignals.description': 'AI 建议、风险与观察条件', // AI 建议路由描述
  'layout.route.decisionSignals.title': 'AI 建议', // AI 建议路由标题
  'layout.route.dashboard.description': '市场行情与核心指标总览', // 总览路由描述
  'layout.route.dashboard.title': '总览', // 总览路由标题
  'layout.route.home.description': '股票分析与历史报告工作台', // 首页路由描述
  'layout.route.home.title': '首页', // 首页路由标题
  'layout.route.sectorAnalysis.description': '板块涨跌、资金流向与热点追踪', // 板块分析路由描述
  'layout.route.sectorAnalysis.title': '板块分析', // 板块分析路由标题
  'layout.route.portfolio.description': '组合快照、手工录入与风险分析', // 持仓路由描述
  'layout.route.portfolio.title': '持仓', // 持仓路由标题
  'layout.route.settings.description': '系统配置、模型与认证管理', // 设置路由描述
  'layout.route.settings.title': '设置', // 设置路由标题
  'layout.route.screening.description': 'AlphaSift 策略选股与候选研究', // 选股路由描述
  'layout.route.screening.title': '选股', // 选股路由标题
  'layout.route.usage.description': 'LLM Token 消耗与模型调用明细', // 用量路由描述
  'layout.route.usage.title': '用量', // 用量路由标题
  'layout.route.kline.description': '个股 K 线走势、技术指标与多周期分析', // K 线路由描述
  'layout.route.kline.title': '个股 K 线', // K 线路由标题
  'layout.logout': '退出', // 退出登录按钮
  'layout.logoutConfirm': '确认退出', // 退出确认按钮
  'layout.logoutMessage': '确认退出当前登录状态吗？退出后需要重新输入密码。', // 退出确认提示文案
  'layout.logoutTitle': '退出登录', // 退出登录弹窗标题
  'header.themeSettings': '主题设置', // 头部主题设置按钮
  'header.language': '界面语言', // 头部中英文切换按钮
  'header.userSettings': '个人设置', // 头部个人设置按钮

  // K 线页面
  'kline.title': '个股 K 线', // K 线页面标题
  'kline.searchPlaceholder': '输入股票代码、名称、拼音或简拼', // K 线搜索框占位符
  'kline.period.1m': '分时', // 分时周期
  'kline.period.5d': '5日', // 5日周期
  'kline.period.daily': '日K', // 日K周期
  'kline.period.weekly': '周 K', // 周 K 周期
  'kline.period.monthly': '月 K', // 月 K 周期
  'kline.period.yearly': '年 K', // 年 K 周期
  'kline.period.5m': '5 分', // 5 分钟周期
  'kline.period.15m': '15 分', // 15 分钟周期
  'kline.period.30m': '30 分', // 30 分钟周期
  'kline.period.60m': '60 分', // 60 分钟周期
  'kline.period.120m': '120 分', // 120 分钟周期
  'kline.info.open': '今开', // 今日开盘价
  'kline.info.prevClose': '昨收', // 昨日收盘价
  'kline.info.high': '最高', // 最高价
  'kline.info.low': '最低', // 最低价
  'kline.info.volume': '成交量', // 成交量
  'kline.info.amount': '成交额', // 成交额
  'kline.info.turnoverRate': '换手率', // 换手率
  'kline.info.amplitude': '振幅', // 振幅
  'kline.info.peRatioTTM': '市盈率(TTM)', // 市盈率TTM
  'kline.info.totalMarketCap': '总市值', // 总市值
  'stockUnit.volumeTenThousandLots': '万手', // 成交量单位万手
  'stockUnit.volumeHundredMillionLots': '亿手', // 成交量单位亿手
  'stockUnit.amountYi': '亿', // 金额单位亿
  'stockUnit.amountWanYi': '万亿', // 金额单位万亿
  'kline.noStockSelected': '请搜索并选择一只股票查看 K 线', // 未选择股票提示
  'kline.fullData': '全量数据', // 全量数据选项
  'kline.loading': '正在加载 K 线数据', // K 线加载中文案
  'kline.error': 'K 线数据加载失败', // K 线加载失败提示
  'kline.tooltip.kline': 'K 线', // K 线 tooltip 标签
  'kline.tooltip.open': '开盘', // tooltip 开盘价
  'kline.tooltip.close': '收盘', // tooltip 收盘价
  'kline.tooltip.high': '最高', // tooltip 最高价
  'kline.tooltip.low': '最低', // tooltip 最低价
  'kline.tooltip.volume': '成交量', // tooltip 成交量
  'kline.tooltip.amount': '成交额', // tooltip 成交额
  'kline.tooltip.change': '涨跌幅', // tooltip 涨跌幅
  'kline.tooltip.date': '日期', // tooltip 日期
  'kline.tooltip.ma5': 'MA5', // tooltip MA5 均线
  'kline.tooltip.ma10': 'MA10', // tooltip MA10 均线
  'kline.tooltip.ma30': 'MA30', // tooltip MA30 均线
  'kline.tooltip.ma60': 'MA60', // tooltip MA60 均线
  'kline.tooltip.dif': 'DIF', // tooltip DIF 指标
  'kline.tooltip.dea': 'DEA', // tooltip DEA 指标
  'kline.tooltip.macd': 'MACD', // tooltip MACD 指标

  'usage.breakdown': 'Breakdown', // 用量明细标签
  'usage.callType.agent': '问股 Agent', // 问股调用类型
  'usage.callType.analysis': '个股分析', // 个股分析调用类型
  'usage.callType.marketReview': '大盘复盘', // 大盘复盘调用类型
  'usage.callType.unknown': '{type}', // 未知调用类型
  'usage.callTypeDetail': '{calls} 次 · Prompt {prompt} · Completion {completion}', // 调用类型明细文案
  'usage.callTypeTitle': '调用类型', // 调用类型标题
  'usage.calls': '{count} 次调用', // 调用次数统计
  'usage.completionTokens': 'Completion tokens', // Completion token 数量
  'usage.completionTokensHint': '模型输出消耗', // Completion token 说明
  'usage.dateRange': '{from} 至 {to}', // 日期范围
  'usage.description': '查看 LLM 调用次数、Prompt/Completion Token 消耗、模型用量和最近调用明细。', // 用量页面描述
  'usage.emptyDescription': '完成一次分析、大盘复盘或问股调用后，这里会显示模型用量。', // 用量空状态描述
  'usage.emptyTitle': '暂无 Token 用量记录', // 用量空状态标题
  'usage.error.message': 'Token 用量数据加载失败', // 用量加载失败提示
  'usage.error.title': 'Token 用量加载失败', // 用量加载失败标题
  'usage.eyebrow': 'Usage', // 用量页面眉标
  'usage.maxSingleCall': '单次峰值', // 单次调用 token 峰值
  'usage.modelUsage': '模型用量', // 模型用量区块标题
  'usage.modelUsageDescription': '按模型聚合 Token 消耗、调用次数和单次峰值。', // 模型用量说明
  'usage.noRecentCalls': '暂无最近调用记录', // 最近调用空状态
  'usage.period.all': '全部', // 全部时间范围
  'usage.period.month': '本月', // 本月时间范围
  'usage.period.today': '今日', // 今日时间范围
  'usage.promptTokens': 'Prompt tokens', // Prompt token 数量
  'usage.promptTokensHint': '输入上下文消耗', // Prompt token 说明
  'usage.recentCalls': '最近调用', // 最近调用区块标题
  'usage.recentCallsDescription': '最近 50 条 LLM token 审计记录。', // 最近调用说明
  'usage.refresh': '刷新', // 刷新按钮
  'usage.table.model': '模型', // 调用表格模型列
  'usage.table.time': '时间', // 调用表格时间列
  'usage.table.type': '类型', // 调用表格类型列
  'usage.title': 'Token 用量监控', // 用量页面标题
  'usage.totalCalls': '调用次数', // 总调用次数
  'usage.totalCallsHint': '已记录的 LLM 调用', // 总调用次数说明
  'usage.totalTokens': '总 tokens', // 总 token 数量

  'routeError.backHome': '返回首页', // 路由错误返回首页
  'routeError.description': '当前页面资源或组件未能正常加载，可能是网络中断或页面版本已更新。请重新加载页面，或返回首页后再试。', // 路由错误描述
  'routeError.reload': '重新加载页面', // 路由错误重新加载
  'routeError.title': '页面加载失败', // 路由错误标题
  'notFound.backHome': '返回首页', // 404 返回首页
  'notFound.description': '抱歉，您访问的页面不存在或已被移动', // 404 描述
  'notFound.pageTitle': '页面未找到 - HRS', // 404 页面标题
  'notFound.title': '页面未找到', // 404 标题

  'login.adminLogin': '管理员登录', // 管理员登录标题
  'login.adminPassword': '管理员密码', // 管理员密码标签
  'login.confirmPassword': '确认密码', // 确认密码标签
  'login.confirmPasswordPlaceholder': '再次确认管理员密码', // 确认密码占位符
  'login.loginDescription': '访问 HRS 量化决策引擎需要有效的身份凭证。', // 登录页描述
  'login.loginFailed': '登录失败', // 登录失败提示
  'login.loginPassword': '登录密码', // 登录密码标签
  'login.loginPasswordPlaceholder': '请输入密码', // 登录密码占位符
  'login.loginSubmit': '授权进入工作台', // 登录提交按钮
  'login.loginSubmitting': '正在建立连接...', // 登录提交中状态
  'login.pageTitle': '登录 - HRS', // 登录页标题
  'login.passwordMismatch': '两次输入的密码不一致', // 密码不一致提示
  'login.setupDescription': '首次启用认证，请为系统工作台设置管理员密码。', // 初始密码设置描述
  'login.setupFailed': '配置失败', // 初始设置失败提示
  'login.setupPasswordPlaceholder': '请设置 6 位以上密码', // 初始密码占位符
  'login.setupSubmit': '完成设置并登录', // 初始设置提交按钮
  'login.setupSubmitting': '初始化中...', // 初始设置提交中状态
  'login.setupTitle': '设置初始密码', // 初始密码设置标题
  'login.validationFailed': '验证未通过', // 验证失败提示

  'home.analyze': '分析', // 分析按钮
  'home.analyzing': '分析中', // 分析中状态
  'home.askAi': '追问 AI', // 追问 AI 按钮
  'home.defaultStrategyDescription': '沿用系统默认分析框架', // 默认策略描述
  'home.defaultStrategyName': '默认策略', // 默认策略名称
  'home.duplicateTask': '任务已存在', // 重复任务提示
  'home.goSettings': '去配置', // 跳转设置按钮
  'home.historyButton': '历史记录', // 历史记录按钮
  'home.historyTrend': '历史趋势', // 历史趋势入口
  'home.inputInvalid': '输入有误', // 输入无效提示
  'home.loadingReport': '加载报告中...', // 报告加载中状态
  'home.marketReview': '大盘复盘', // 大盘复盘入口
  'home.marketReviewCompleted': '大盘复盘已完成', // 大盘复盘完成提示
  'home.marketReviewCompletedWithReport': '大盘复盘任务已完成，结果如下：', // 大盘复盘完成含结果
  'home.marketReviewCompletedWithoutReport': '大盘复盘任务已完成，结果已生成并按配置推送。', // 大盘复盘完成无结果展示
  'home.marketReviewFailed': '大盘复盘执行失败。', // 大盘复盘失败提示
  'home.marketReviewHistoryEmptyDescription': '运行大盘复盘后，这里会集中展示历史记录。', // 大盘复盘历史空状态描述
  'home.marketReviewHistoryEmptyTitle': '暂无大盘复盘', // 大盘复盘历史空状态标题
  'home.marketReviewHistoryTitle': '大盘复盘历史', // 大盘复盘历史标题
  'home.marketReviewInProgress': '大盘复盘进行中', // 大盘复盘进行中状态
  'home.marketReviewSubmitted': '大盘复盘已提交', // 大盘复盘已提交提示
  'home.marketReviewSubmittedWithRegion': '{message}；实际市场：{region}', // 大盘复盘提交含市场
  'home.marketReviewTimeout': '大盘复盘已超时', // 大盘复盘超时提示
  'home.marketReviewTimeoutMessage': '任务长时间未返回最终结果，请在任务列表/历史中查看。', // 大盘复盘超时说明
  'home.marketReviewUnknownStatus': '大盘复盘状态异常', // 大盘复盘状态异常提示
  'home.marketRegionAll': '全部市场', // 全部市场选项
  'home.marketRegionCn': 'A 股', // A 股市场
  'home.marketRegionDefaultUnavailable': '由服务器在提交时决定', // 市场默认值不可用说明
  'home.marketRegionDescription': '选择本次复盘覆盖的市场，可单选或多选。', // 市场选择说明
  'home.marketRegionHk': '港股', // 港股市场
  'home.marketRegionJp': '日股', // 日股市场
  'home.marketRegionKr': '韩股', // 韩股市场
  'home.marketRegionOneTimeHint': '仅影响本次触发，不会修改全局配置。', // 市场选择一次性提示
  'home.marketRegionSelector': '选择大盘复盘市场', // 市场选择器标题
  'home.marketRegionServerDefault': '服务器默认', // 服务器默认市场
  'home.marketRegionTitle': '本次复盘市场', // 本次复盘市场标题
  'home.marketRegionUs': '美股', // 美股市场
  'home.notify': '推送通知', // 推送通知选项
  'home.pageTitle': '每日选股分析 - HRS', // 首页文档标题
  'home.placeholder': '输入股票代码或名称，如 600519、贵州茅台、AAPL', // 股票输入框占位符
  'home.progressActive': '进行中', // 任务进行中状态
  'home.reanalyze': '重新分析', // 重新分析按钮
  'home.rerunMarketReview': '重新复盘', // 重新复盘按钮
  'home.fullReport': '完整分析报告', // 完整报告入口
  'home.setupIncomplete': '基础配置未完成', // 配置未完成提示
  'home.setupMissingGeneric': '还缺少基础配置，完成后即可开始最小可用分析。', // 缺少配置通用提示
  'home.setupMissingWithLabels': '还缺少 {labels}，完成后即可开始最小可用分析。', // 缺少配置含标签提示
  'home.startAnalysisDescription': '输入股票代码进行分析，或从左侧选择历史报告查看。', // 开始分析描述
  'home.startAnalysisTitle': '开始分析', // 开始分析标题
  'home.strategy': '策略', // 策略标签
  'home.submitMarketReview': '提交中', // 大盘复盘提交中状态
  'home.taskStatus': '任务状态：{status}（{progress}）', // 任务状态文案
  'home.taskStatusWithRegion': '任务状态：{status}（{progress}）；实际市场：{region}', // 任务状态含市场
  'home.unknownTaskStatus': '收到未知任务状态：{status}', // 未知任务状态提示

  'decisionSignals.action': '动作', // 信号动作标签
  'decisionSignals.active': '有效', // 有效信号状态
  'decisionSignals.activeOnly': '默认展示 active 信号', // 仅展示有效信号说明
  'decisionSignals.allActions': '全部动作', // 全部动作筛选
  'decisionSignals.allMarkets': '全部市场', // 全部市场筛选
  'decisionSignals.allPhases': '全部阶段', // 全部阶段筛选
  'decisionSignals.allProfiles': '全部风格', // 全部风格筛选
  'decisionSignals.allSources': '全部来源', // 全部来源筛选
  'decisionSignals.allStatuses': '全部状态', // 全部状态筛选
  'decisionSignals.archive': '归档', // 归档按钮
  'decisionSignals.archiveConfirm': '确认将这条信号归档吗？归档后不会再作为当前 active 建议展示。', // 归档确认提示
  'decisionSignals.archived': '已归档', // 已归档状态
  'decisionSignals.close': '关闭信号', // 关闭信号按钮
  'decisionSignals.closeConfirm': '确认关闭这条信号吗？关闭表示你不再跟踪这条建议。', // 关闭信号确认
  'decisionSignals.closed': '已关闭', // 已关闭状态
  'decisionSignals.confidence': '置信度', // 信号置信度
  'decisionSignals.confirmStatusTitle': '更新信号状态', // 状态更新弹窗标题
  'decisionSignals.createdAt': '创建时间', // 信号创建时间
  'decisionSignals.catalystSummary': '催化', // 催化因素摘要
  'decisionSignals.dataQuality': '数据质量', // 数据质量标签
  'decisionSignals.description': '按股票、阶段、来源和状态查询结构化 AI 建议，并保留风险与数据质量上下文。', // AI 建议页面描述
  'decisionSignals.detailTitle': '信号详情', // 信号详情标题
  'decisionSignals.directionExpected': '预期方向', // 预期方向标签
  'decisionSignals.emptyDescription': '完成一次普通个股分析后，系统会从报告中沉淀可查询的结构化建议。', // 信号空状态描述
  'decisionSignals.emptyTitle': '暂无决策信号', // 信号空状态标题
  'decisionSignals.entryRange': '入场区间', // 入场区间标签
  'decisionSignals.errorTitle': '决策信号加载失败', // 信号加载失败标题
  'decisionSignals.evidence': '证据', // 证据标签
  'decisionSignals.expired': '已过期', // 已过期状态
  'decisionSignals.expiresAt': '过期时间', // 过期时间标签
  'decisionSignals.feedback.not_useful': '无用', // 无用反馈选项
  'decisionSignals.feedback.useful': '有用', // 有用反馈选项
  'decisionSignals.feedbackNone': '暂无反馈', // 无反馈状态
  'decisionSignals.feedbackTitle': '用户反馈', // 用户反馈标题
  'decisionSignals.filter': '筛选', // 筛选按钮
  'decisionSignals.horizon': '周期', // 持仓周期标签
  'decisionSignals.horizon.1d': '1 日', // 1 日周期
  'decisionSignals.horizon.3d': '3 日', // 3 日周期
  'decisionSignals.horizon.5d': '5 日', // 5 日周期
  'decisionSignals.horizon.10d': '10 日', // 10 日周期
  'decisionSignals.horizon.intraday': '盘中', // 盘中周期
  'decisionSignals.horizon.long': '长期', // 长期周期
  'decisionSignals.horizon.swing': '波段', // 波段周期
  'decisionSignals.invalidation': '失效条件', // 信号失效条件
  'decisionSignals.invalidate': '标记失效', // 标记失效按钮
  'decisionSignals.invalidateConfirm': '确认将这条信号标记为失效吗？失效后不会再作为当前 active 建议展示。', // 标记失效确认
  'decisionSignals.invalidated': '已失效', // 已失效状态
  'decisionSignals.latestButton': '查询最新', // 查询最新信号按钮
  'decisionSignals.latestDescription': '读取当前查看股票的最新 active 信号。', // 查询最新说明
  'decisionSignals.latestInput': '最新股票代码', // 最新股票代码输入标签
  'decisionSignals.latestPlaceholder': '例如 600519、HK00700、AAPL', // 最新股票代码占位符
  'decisionSignals.latestTitle': '按股票查询最新信号', // 按股票查询标题
  'decisionSignals.market': '市场', // 市场标签
  'decisionSignals.market.cn': 'A 股', // A 股市场
  'decisionSignals.market.hk': '港股', // 港股市场
  'decisionSignals.market.jp': '日股', // 日股市场
  'decisionSignals.market.kr': '韩股', // 韩股市场
  'decisionSignals.market.tw': '台股', // 台股市场
  'decisionSignals.market.us': '美股', // 美股市场
  'decisionSignals.marketPhase': '阶段', // 市场阶段标签
  'decisionSignals.marketPhase.closing_auction': '集合竞价', // 集合竞价阶段
  'decisionSignals.marketPhase.intraday': '盘中', // 盘中阶段
  'decisionSignals.marketPhase.lunch_break': '午间休市', // 午间休市阶段
  'decisionSignals.marketPhase.non_trading': '非交易时段', // 非交易时段
  'decisionSignals.marketPhase.postmarket': '盘后', // 盘后阶段
  'decisionSignals.marketPhase.premarket': '盘前', // 盘前阶段
  'decisionSignals.marketPhase.unknown': '未知阶段', // 未知阶段
  'decisionSignals.metadata': '元数据', // 元数据标签
  'decisionSignals.noLatestDescription': '该股票当前没有 active 信号，或信号已过期。', // 无最新信号说明
  'decisionSignals.noLatestTitle': '暂无最新有效信号', // 无最新信号标题
  'decisionSignals.noReviewedStatsDescription': '当前已有 AI 建议时，也可能还没有形成可统计的后验复盘结果。', // 无复盘样本说明
  'decisionSignals.noReviewedStatsTitle': '暂无已复盘样本', // 无复盘样本标题
  'decisionSignals.noOutcomes': '暂无后验结果', // 无后验结果提示
  'decisionSignals.noStatsDescription': '触发一次信号后验计算后，这里会显示命中、未命中和无法评估统计。', // 无后验统计说明
  'decisionSignals.noStatsTitle': '暂无后验统计', // 无后验统计标题
  'decisionSignals.outcome.hit': '命中', // 命中后验结果
  'decisionSignals.outcome.miss': '未命中', // 未命中后验结果
  'decisionSignals.outcome.neutral': '中性', // 中性后验结果
  'decisionSignals.outcome.unable': '无法评估', // 无法评估后验结果
  'decisionSignals.outcomes': '后验结果', // 后验结果标签
  'decisionSignals.pageTitle': 'AI 建议 - HRS', // AI 建议页文档标题
  'decisionSignals.planQuality': '计划质量', // 计划质量标签
  'decisionSignals.planQuality.complete': '完整', // 完整计划质量
  'decisionSignals.planQuality.minimal': '最小', // 最小计划质量
  'decisionSignals.planQuality.partial': '部分', // 部分计划质量
  'decisionSignals.planQuality.unknown': '未知', // 未知计划质量
  'decisionSignals.pricePlan': '价格计划', // 价格计划标签
  'decisionSignals.profile': '风格', // 决策风格标签
  'decisionSignals.profile.aggressive': '进取', // 进取风格
  'decisionSignals.profile.balanced': '均衡', // 均衡风格
  'decisionSignals.profile.conservative': '保守', // 保守风格
  'decisionSignals.profile.unknown': '未知', // 未知风格
  'decisionSignals.reason': '理由', // 信号理由标签
  'decisionSignals.reassessBlockedNote': '该预览已被风控约束为非进攻展示动作。', // 重评估被阻断说明
  'decisionSignals.reassessBlockedTitle': '预览被风控阻断', // 重评估阻断标题
  'decisionSignals.reassessPersist': '确认保存', // 确认保存重评估
  'decisionSignals.reassessPersistBlockedTitle': '保存被风控阻断', // 保存被阻断标题
  'decisionSignals.reassessPersistConfirmMessage': '服务端将基于同一份历史报告快照重新计算，并保存通过风控的结果。', // 保存重评估确认文案
  'decisionSignals.reassessPersistConfirmTitle': '保存重评估信号', // 保存重评估确认标题
  'decisionSignals.reassessPersistedCreated': '已保存为新的 DecisionSignal #{id}。', // 重评估新建成功提示
  'decisionSignals.reassessPersistedCreatedTitle': '重评估信号已保存', // 重评估新建成功标题
  'decisionSignals.reassessPersistedExisting': '同一报告、风格和信号身份的 DecisionSignal #{id} 已存在，本次没有重复创建；展示其原始服务端记录。', // 重评估复用现有信号提示
  'decisionSignals.reassessPersistedExistingTitle': '已复用现有信号', // 重评估复用现有信号标题
  'decisionSignals.reassessPersistedRefreshed': '现有 DecisionSignal #{id} 已按存储契约完成过期续期或缺失维度补齐；原始创建来源保持不变，请以后端返回记录为准。', // 重评估刷新信号提示
  'decisionSignals.reassessPersistedRefreshedTitle': '重评估信号已刷新', // 重评估刷新信号标题
  'decisionSignals.reassessPersistedTerminalExisting': 'DecisionSignal #{id} 已处于“{status}”状态，本次没有新建或重新激活信号。', // 重评估终态信号提示
  'decisionSignals.reassessPersistedTerminalTitle': '现有信号保持终态', // 重评估终态信号标题
  'decisionSignals.reassessPersisting': '正在保存', // 重评估保存中状态
  'decisionSignals.reassessPreview': '生成预览', // 生成重评估预览按钮
  'decisionSignals.reassessProfile': '重评估风格', // 重评估风格标签
  'decisionSignals.reassessRawFinal': '原始/最终', // 原始与最终对比标签
  'decisionSignals.reassessSource': '来源报告 #{id}', // 重评估来源报告
  'decisionSignals.reassessTitle': '决策风格重评估预览', // 重评估预览标题
  'decisionSignals.reassessUnsupported': '该信号不支持重评估', // 不支持重评估提示
  'decisionSignals.reassessUnsupportedTitle': '缺少来源报告', // 不支持重评估标题
  'decisionSignals.reassessWarnings': '风控提示', // 风控提示标签
  'decisionSignals.refresh': '刷新', // 刷新按钮
  'decisionSignals.returnPct': '区间收益', // 区间收益率
  'decisionSignals.riskSummary': '风险', // 风险摘要标签
  'decisionSignals.score': '评分', // 信号评分
  'decisionSignals.source': '来源', // 信号来源标签
  'decisionSignals.sourceType.agent': 'Agent', // Agent 来源
  'decisionSignals.sourceType.alert': '告警', // 告警来源
  'decisionSignals.sourceType.analysis': '分析报告', // 分析报告来源
  'decisionSignals.sourceType.manual': '手动', // 手动来源
  'decisionSignals.sourceType.market_review': '大盘复盘', // 大盘复盘来源
  'decisionSignals.sourceReport': '来源报告', // 来源报告标签
  'decisionSignals.sourceReportId': '来源报告 ID', // 来源报告 ID
  'decisionSignals.statsDescription': '基于当前后验引擎版本统计信号表现，默认排除已归档信号。', // 信号统计说明
  'decisionSignals.statsErrorTitle': '后验统计加载失败', // 统计加载失败标题
  'decisionSignals.statsGlobalScope': '当前统计为全局已复盘 outcome 口径，不等于当前可见信号数量，也不随当前股票过滤。', // 全局统计口径说明
  'decisionSignals.statsHitRate': '命中率', // 命中率统计
  'decisionSignals.statsTitle': '信号表现统计', // 信号统计标题
  'decisionSignals.statsTotal': '评估数', // 评估总数
  'decisionSignals.profileCalibrationAverageReturn': '标的平均区间涨跌', // 风格校准平均涨跌
  'decisionSignals.profileCalibrationBreakdownLabel': '细分统计方式', // 细分统计标签
  'decisionSignals.profileCalibrationByAction': '按建议动作', // 按动作细分
  'decisionSignals.profileCalibrationByHorizon': '按复盘周期', // 按周期细分
  'decisionSignals.profileCalibrationCompletedShort': '已完成 {count}', // 已完成数量
  'decisionSignals.profileCalibrationDescription': '这些数据来自历史后验复盘，只用于描述，不代表某种风格更优，也不构成投资建议。', // 风格校准说明
  'decisionSignals.profileCalibrationHitRate': '命中率', // 风格校准命中率
  'decisionSignals.profileCalibrationInsufficient': '样本不足，仅供观察。', // 样本不足提示
  'decisionSignals.profileCalibrationMae': '最大不利波动', // 最大不利波动指标
  'decisionSignals.profileCalibrationMaeDescription': '最大不利波动表示复盘期间相对起始价最不利的一次波动，不代表未来风险上限。', // 最大不利波动说明
  'decisionSignals.profileCalibrationMissRate': '未命中率', // 未命中率
  'decisionSignals.profileCalibrationNoBreakdownSamples': '暂无可观察的细分样本。', // 无细分样本提示
  'decisionSignals.profileCalibrationSampleCounts': '已完成 {completed} / 总评估 {total}', // 样本数量统计
  'decisionSignals.profileCalibrationThreshold': '每个分组至少需要 {count} 个已完成样本才展示表现指标。', // 展示阈值说明
  'decisionSignals.profileCalibrationTitle': '决策风格历史表现', // 风格校准标题
  'decisionSignals.profileCalibrationUnableRate': '无法评估率', // 无法评估率
  'decisionSignals.profileCalibrationUnavailable': '暂无可计算结果', // 无可计算结果提示
  'decisionSignals.profileCalibrationUnknownDimension': '未知', // 未知维度
  'decisionSignals.profileCalibrationUnknownNotice': '另有 {count} 条历史样本缺少决策风格标记，未计入三类风格。', // 未知风格样本提示
  'decisionSignals.status': '状态', // 信号状态标签
  'decisionSignals.stockContextApply': '查看股票', // 应用股票上下文按钮
  'decisionSignals.stockContextClear': '清空当前股票', // 清空股票上下文按钮
  'decisionSignals.stockContextCurrent': '当前查看：{stock}', // 当前股票上下文
  'decisionSignals.stockContextDescription': '选择一次股票后，最新信号和时间线会共享这个上下文。', // 股票上下文说明
  'decisionSignals.stockContextEmpty': '尚未选择当前股票。', // 未选股票提示
  'decisionSignals.stockContextGuideDescription': '先在页面顶部选择当前股票，再查看最新信号和时间线。', // 股票上下文引导说明
  'decisionSignals.stockContextGuideTitle': '选择股票查看 AI 建议', // 股票上下文引导标题
  'decisionSignals.stockContextInput': '当前股票', // 当前股票输入标签
  'decisionSignals.stockContextNoCandidates': '暂无可用候选，可直接输入股票代码或名称。', // 无候选股票提示
  'decisionSignals.stockContextPlaceholder': '输入股票代码或名称，如 600519、贵州茅台、AAPL', // 股票上下文输入占位符
  'decisionSignals.stockContextPopular': '热门候选', // 热门候选股票
  'decisionSignals.stockContextRecent': '最近分析', // 最近分析股票
  'decisionSignals.stockContextTitle': '当前股票', // 当前股票标题
  'decisionSignals.stockCode': '股票代码', // 股票代码标签
  'decisionSignals.stopLoss': '止损', // 止损价标签
  'decisionSignals.targetPrice': '目标价', // 目标价标签
  'decisionSignals.title': 'AI 建议', // AI 建议页面标题
  'decisionSignals.total': '共 {total} 条信号', // 信号总数
  'decisionSignals.timelineAlertShape': '菱形点表示 alert', // 时间线告警形状说明
  'decisionSignals.timelineDescription': '按单支股票查看同一建议随时间变化的轨迹。', // 时间线说明
  'decisionSignals.timelineEmptyDescription': '当前时间范围内没有该股票的信号。', // 时间线空状态描述
  'decisionSignals.timelineEmptyTitle': '暂无时间线信号', // 时间线空状态标题
  'decisionSignals.timelineErrorTitle': '时间线加载失败', // 时间线加载失败标题
  'decisionSignals.timelineFamilyBullish': '偏多', // 偏多信号族
  'decisionSignals.timelineFamilyDefensive': '防御', // 防御信号族
  'decisionSignals.timelineFamilyNeutral': '中性', // 中性信号族
  'decisionSignals.timelineGuideDescription': '调整时间范围、状态或市场后，点击查询时间线应用筛选。', // 时间线引导说明
  'decisionSignals.timelineGuideTitle': '查询当前股票时间线', // 时间线引导标题
  'decisionSignals.timelineMarket': '时间线市场', // 时间线市场筛选
  'decisionSignals.timelineProfile': '时间线风格', // 时间线风格筛选
  'decisionSignals.timelineRange': '时间范围', // 时间线范围标签
  'decisionSignals.timelineRange.30d': '30 天', // 30 天时间范围
  'decisionSignals.timelineRange.90d': '90 天', // 90 天时间范围
  'decisionSignals.timelineRange.180d': '180 天', // 180 天时间范围
  'decisionSignals.timelineSearch': '查询时间线', // 查询时间线按钮
  'decisionSignals.timelineSelected': '已选第 {index} 个点', // 时间线选中点提示
  'decisionSignals.timelineStatus': '时间线状态', // 时间线状态筛选
  'decisionSignals.timelineStatus.active': '仅有效', // 仅有效信号筛选
  'decisionSignals.timelineStatus.all': '全部历史', // 全部历史筛选
  'decisionSignals.timelineStockCode': '时间线股票代码', // 时间线股票代码标签
  'decisionSignals.timelineStockPlaceholder': '例如 600519、HK00700、AAPL', // 时间线股票占位符
  'decisionSignals.timelineTitle': '股票信号时间线', // 时间线标题
  'decisionSignals.timelineTruncatedDescription': '仅展示最近 100 条信号，请缩小时间范围。', // 时间线截断说明
  'decisionSignals.timelineTruncatedTitle': '时间线已截断', // 时间线截断标题
  'decisionSignals.unableReason': '无法评估原因', // 无法评估原因标签
  'decisionSignals.watchConditions': '观察条件', // 观察条件标签
  'decisionSignals.viewDetailsFor': '查看 {stock} AI 建议详情', // 查看股票建议详情
  'decisionSignals.portfolioColumn': 'AI 建议', // 持仓 AI 建议列名
  'decisionSignals.portfolioEmpty': '-', // 持仓 AI 建议空值
  'decisionSignals.portfolioLoading': '加载中', // 持仓 AI 建议加载中
  'decisionSignals.portfolioPartialWarning': 'AI 建议只加载了部分数据：{message}', // 持仓 AI 建议部分加载警告
  'decisionSignals.portfolioWarningTitle': 'AI 建议降级', // 持仓 AI 建议降级标题

  'history.analysisCount': '{count}次', // 分析次数统计
  'history.bottomReached': '已到底部', // 历史列表到底提示
  'history.defaultEmptyDescription': '完成首次分析后，这里会保留最近结果。', // 历史空状态描述
  'history.defaultEmptyTitle': '暂无历史分析记录', // 历史空状态标题
  'history.defaultTitle': '历史分析', // 历史分析标题
  'history.deleteRecord': '删除 {name} 历史记录', // 删除历史记录按钮
  'history.itemAria': '{name} {code} 历史记录', // 历史记录项无障碍标签
  'history.loading': '加载历史记录中...', // 历史加载中状态
  'history.actionAdd': '加仓', // 加仓动作
  'history.actionAlert': '预警', // 预警动作
  'history.actionAvoid': '回避', // 回避动作
  'history.actionBuy': '买入', // 买入动作
  'history.actionHold': '持有', // 持有动作
  'history.actionReduce': '减仓', // 减仓动作
  'history.actionSell': '卖出', // 卖出动作
  'history.actionWatch': '观望', // 观望动作
  'history.sentiment': '情绪', // 情绪标签
  'history.selectAllHistoryAria': '全选当前已加载历史记录', // 全选历史无障碍标签
  'history.selectAllStockAria': '全选当前个股', // 全选个股无障碍标签
  'stockBar.emptyDescription': '完成首次分析后，这里将按股票展示最新分析结果。', // 个股栏空状态描述
  'stockBar.emptyTitle': '暂无个股记录', // 个股栏空状态标题
  'stockBar.loading': '加载个股中...', // 个股栏加载中状态
  'stockBar.market': '大盘', // 个股栏大盘入口
  'stockBar.title': '个股栏', // 个股栏标题
  'watchlist.add': '添加自选股', // 添加自选股按钮
  'watchlist.addPlaceholder': '添加代码，如 600519', // 添加自选股占位符
  'watchlist.analyzeAll': '分析全部', // 分析全部自选股
  'watchlist.analyzePending': '仅未分析', // 仅分析未分析自选股
  'watchlist.analyzedToday': '今日已分析', // 今日已分析状态
  'watchlist.batchFailed': '自选股批量分析提交失败', // 批量分析失败提示
  'watchlist.batchIncompleteResponse': '批量接口本组请求 {requested} 只，仅确认 {confirmed} 只，返回结果不完整', // 批量响应不完整提示
  'watchlist.batchPartiallySubmitted': '已确认提交 {accepted} 个任务，{duplicates} 个正在运行；另有 {unconfirmed} 只未确认，已停止后续提交并刷新任务列表。原因：{error}', // 批量部分提交提示
  'watchlist.batchSubmitted': '已提交 {accepted} 个任务，{duplicates} 个正在运行', // 批量提交成功提示
  'watchlist.emptyDescription': '在报告详情或这里添加股票后，可一键运行整组自选股。', // 自选股空状态描述
  'watchlist.emptyTitle': '暂无自选股', // 自选股空状态标题
  'watchlist.listHint': '按自选顺序展示，今日状态实时标记', // 自选股列表说明
  'watchlist.loading': '加载自选股中...', // 自选股加载中状态
  'watchlist.noPendingAnalyze': '今天没有待分析的自选股。', // 无待分析自选股提示
  'watchlist.noStocksAnalyze': '请先添加自选股。', // 无自选股提示
  'watchlist.notAnalyzedToday': '今日未分析', // 今日未分析状态
  'watchlist.pendingToday': '今日待分析', // 今日待分析状态
  'watchlist.pendingStatusLoading': '正在确认自选股今日状态，请稍后再提交仅未分析。', // 待分析状态加载中提示
  'watchlist.pendingStatusUnavailable': '自选股今日状态仍有未知项，请刷新后再提交仅未分析。', // 待分析状态不可用提示
  'watchlist.refresh': '刷新自选股', // 刷新自选股按钮
  'watchlist.removeAria': '从自选股移除 {code}', // 移除自选股无障碍标签
  'watchlist.submitting': '提交中', // 自选股提交中状态
  'watchlist.tabHistory': '历史', // 自选股历史标签页
  'watchlist.tabToday': '今日', // 自选股今日标签页
  'watchlist.tabWatchlist': '自选', // 自选股自选标签页
  'watchlist.taskRunning': '任务{status}', // 自选股任务运行状态
  'watchlist.title': '自选股', // 自选股标题
  'watchlist.todayStatusLoading': '确认今日状态中', // 今日状态确认中
  'watchlist.todayCoverage': '今日覆盖', // 今日分析覆盖率
  'watchlist.todayEmptyDescription': '今天完成分析后，这里会按评分显示股票排行。', // 今日空状态描述
  'watchlist.todayEmptyTitle': '今天还没有分析结果', // 今日空状态标题
  'watchlist.todayLoadErrorDescription': '完整历史分页加载失败，为避免展示不完整排行，请刷新后重试。', // 今日排行加载失败描述
  'watchlist.todayLoadErrorTitle': '今日排行加载失败', // 今日排行加载失败标题
  'watchlist.todaySortHint': '按情绪分优先排序', // 今日排序提示
  'watchlist.todayStatusUnavailable': '今日状态未知', // 今日状态未知提示
  'watchlist.todayTitle': '今日分析', // 今日分析标题
  'watchlist.topScore': '最高分', // 最高分标签
  'watchlist.watchlistCoverage': '自选覆盖', // 自选覆盖率

  'stockTrend.allHistory': '全部历史', // 全部历史选项
  'stockTrend.averageScore': '平均分 {score}', // 平均分显示
  'stockTrend.backToCurrentReport': '返回当前报告', // 返回当前报告按钮
  'stockTrend.currentAdvice': '当前观点', // 当前观点标签
  'stockTrend.currentScore': '当前分数', // 当前分数标签
  'stockTrend.historyModelCount': '历史模型 {count} 种', // 历史模型数量
  'stockTrend.loadedSummary': '已加载 {loaded} / {total} 条 · 排序：最新优先 · 模型：全部', // 加载摘要
  'stockTrend.loadFailed': '历史趋势加载失败', // 历史趋势加载失败提示
  'stockTrend.loading': '加载同股历史中...', // 同股历史加载中
  'stockTrend.loadMore': '加载更多', // 加载更多按钮
  'stockTrend.loadingMore': '加载中...', // 加载更多中状态
  'stockTrend.latestTime': '最近一次 {time}', // 最近一次时间
  'stockTrend.model': '模型', // 模型标签
  'stockTrend.modelCountSuffix': '{count}次', // 模型次数后缀
  'stockTrend.moreEmptyDescription': '完成多次分析后，这里会展示观点变化、评分走势和模型记录。', // 更多历史空状态描述
  'stockTrend.moreEmptyTitle': '暂无更多同股历史分析', // 更多历史空状态标题
  'stockTrend.neverRecorded': '未记录', // 未记录提示
  'stockTrend.noModelTitle': '未记录模型', // 未记录模型标题
  'stockTrend.records': '历史分析记录', // 历史记录标签
  'stockTrend.reload': '重新加载', // 重新加载按钮
  'stockTrend.report': '查看报告', // 查看报告按钮
  'stockTrend.result': '分析结果', // 分析结果标签
  'stockTrend.score': '分数', // 分数标签
  'stockTrend.stockPrice': '股价', // 股价标签
  'stockTrend.table.action': '操作', // 趋势表格操作列
  'stockTrend.time': '时间', // 趋势表格时间列
  'stockTrend.title': '历史趋势', // 历史趋势标题
  'stockTrend.volumeRatio': '量比', // 量比标签
  'stockTrend.window30': '近30天', // 近 30 天窗口
  'stockTrend.window90': '近90天', // 近 90 天窗口
  'stockTrend.changePct': '涨跌幅', // 涨跌幅标签
  'stockTrend.turnoverRate': '换手率', // 换手率标签

  'taskPanel.diagnostics': '运行诊断', // 运行诊断按钮
  'taskPanel.pending': '等待中', // 任务等待中状态
  'taskPanel.pendingTasks': '{count} 等待中', // 等待中任务数量
  'taskPanel.processing': '分析中', // 任务分析中状态
  'taskPanel.processingAria': '任务进行中', // 任务进行中无障碍标签
  'taskPanel.processingTasks': '{count} 进行中', // 进行中任务数量
  'taskPanel.cancelRequested': '请求取消', // 任务请求取消状态
  'taskPanel.cancelRequestedAria': '任务请求取消', // 请求取消无障碍标签
  'taskPanel.cancelled': '已取消', // 任务已取消状态
  'taskPanel.pendingAria': '任务等待中', // 任务等待中无障碍标签
  'taskPanel.openRunFlow': '查看运行流', // 查看运行流按钮
  'taskPanel.openRunFlowAria': '查看 {stock} 运行流', // 查看运行流无障碍标签
  'taskPanel.statusAria': '任务状态：{status}', // 任务状态无障碍标签
  'taskPanel.title': '分析任务', // 任务面板标题

  'runFlow.drawerTitle': '运行流', // 运行流抽屉标题
  'runFlow.eyebrow': '运行流', // 运行流眉标
  'runFlow.title': '数据流与信息流', // 运行流主标题
  'runFlow.open': '查看运行流', // 查看运行流入口
  'runFlow.openHistoryAria': '查看历史记录 {recordId} 运行流', // 查看历史运行流无障碍标签
  'runFlow.taskDrawerTitle': '{stock} 运行流', // 任务运行流抽屉标题
  'runFlow.historyDrawerTitle': '{stock} 历史运行流', // 历史运行流抽屉标题
  'runFlow.loadingTitle': '正在加载运行流', // 运行流加载标题
  'runFlow.loadingDescription': '正在读取任务快照、运行诊断和事件链路。', // 运行流加载说明
  'runFlow.errorTitle': '运行流加载失败', // 运行流加载失败标题
  'runFlow.retry': '重新加载', // 运行流重新加载
  'runFlow.refresh': '刷新', // 运行流刷新按钮
  'runFlow.refreshing': '刷新中', // 运行流刷新中状态
  'runFlow.emptyTitle': '暂无运行流', // 运行流空状态标题
  'runFlow.emptyDescription': '请选择一个活跃任务或历史报告查看运行流。', // 运行流空状态描述
  'runFlow.emptySnapshotTitle': '暂无运行流细节', // 运行流快照空标题
  'runFlow.emptySnapshotDescription': '当前快照没有节点或事件；缺少 diagnostics 时会显示骨架或空状态。', // 运行流快照空描述
  'runFlow.valueUnavailable': '未记录', // 运行流值不可用
  'runFlow.durationMs': '{value} ms', // 毫秒耗时显示
  'runFlow.durationSeconds': '{value} 秒', // 秒耗时显示
  'runFlow.durationMinutes': '{value} 分钟', // 分钟耗时显示
  'runFlow.status.pending': '等待中', // 运行流等待状态
  'runFlow.status.running': '运行中', // 运行流运行状态
  'runFlow.status.success': '成功', // 运行流成功状态
  'runFlow.status.failed': '失败', // 运行流失败状态
  'runFlow.status.degraded': '部分降级', // 运行流降级状态
  'runFlow.status.fallback': '降级回退', // 运行流回退状态
  'runFlow.status.timeout': '超时', // 运行流超时状态
  'runFlow.status.cancelRequested': '请求取消', // 运行流请求取消状态
  'runFlow.status.cancelled': '已取消', // 运行流已取消状态
  'runFlow.status.skipped': '已跳过', // 运行流已跳过状态
  'runFlow.status.unknown': '未知', // 运行流未知状态
  'runFlow.severity.info': '信息', // 信息级别
  'runFlow.severity.success': '成功', // 成功级别
  'runFlow.severity.warning': '告警', // 告警级别
  'runFlow.severity.danger': '危险', // 危险级别
  'runFlow.edge.data': '数据', // 数据边类型
  'runFlow.edge.control': '控制', // 控制边类型
  'runFlow.edge.fallback': '降级回退', // 回退边类型
  'runFlow.edge.retry': '重试', // 重试边类型
  'runFlow.edgeLabel.invoke': '调用', // 调用边标签
  'runFlow.edgeLabel.details': '详情', // 详情边标签
  'runFlow.nodeKind.entry': '入口', // 入口节点类型
  'runFlow.nodeKind.queue': '队列', // 队列节点类型
  'runFlow.nodeKind.dataSource': '数据源', // 数据源节点类型
  'runFlow.nodeKind.analysis': '分析', // 分析节点类型
  'runFlow.nodeKind.model': '模型', // 模型节点类型
  'runFlow.nodeKind.artifact': '产物', // 产物节点类型
  'runFlow.nodeKind.notification': '通知', // 通知节点类型
  'runFlow.summary.elapsed': '总耗时', // 运行流总耗时
  'runFlow.summary.fallbackCount': '降级回退/重试', // 回退重试次数
  'runFlow.summary.failedAttempts': '失败尝试', // 失败尝试次数
  'runFlow.summary.dataSources': '数据源', // 数据源数量
  'runFlow.summary.task': 'Task', // 任务标识
  'runFlow.summary.trace': 'Trace', // 追踪标识
  'runFlow.summary.model': '模型', // 模型标识
  'runFlow.summary.generatedAt': '生成时间', // 运行流生成时间
  'runFlow.graph.title': '运行拓扑', // 运行拓扑图标题
  'runFlow.graph.description': '自动分层展示入口、数据来源、分析引擎和产物链路。', // 运行拓扑图说明
  'runFlow.graph.nodeAria': '{label} 节点，状态 {status}', // 拓扑节点无障碍标签
  'runFlow.graph.startedAt': '开始', // 拓扑开始时间标签
  'runFlow.graph.expand': '展开', // 展开节点按钮
  'runFlow.graph.collapse': '收起', // 收起节点按钮
  'runFlow.graph.expandNode': '展开 {label} 运行尝试', // 展开节点尝试
  'runFlow.graph.collapseNode': '收起 {label} 运行尝试', // 收起节点尝试
  'runFlow.events.title': '事件流', // 事件流标题
  'runFlow.events.count': '{count} 条事件', // 事件数量
  'runFlow.events.filters': '事件筛选', // 事件筛选标签
  'runFlow.events.filter.all': '全部', // 全部事件筛选
  'runFlow.events.filter.important': '关键', // 关键事件筛选
  'runFlow.events.filter.problems': '失败/告警', // 失败告警事件筛选
  'runFlow.events.filter.fallback': '降级回退/重试', // 回退重试事件筛选
  'runFlow.events.filter.cancelled': '取消', // 取消事件筛选
  'runFlow.events.openNode': '查看事件 {title} 关联节点', // 查看事件关联节点
  'runFlow.events.empty': '当前筛选下暂无事件。', // 事件空状态
  'runFlow.nodeDetails.empty': '选择一个节点查看详情。', // 节点详情空状态
  'runFlow.nodeDetails.title': '节点详情', // 节点详情标题
  'runFlow.nodeDetails.close': '关闭节点详情', // 关闭节点详情按钮
  'runFlow.nodeDetails.kind': '类型', // 节点类型标签
  'runFlow.nodeDetails.version': '版本', // 节点版本标签
  'runFlow.nodeDetails.provider': '提供方', // 节点提供方标签
  'runFlow.nodeDetails.duration': '耗时', // 节点耗时标签
  'runFlow.nodeDetails.attempts': '尝试次数', // 节点尝试次数
  'runFlow.nodeDetails.recordCount': '记录数', // 节点记录数
  'runFlow.nodeDetails.startedAt': '开始时间', // 节点开始时间
  'runFlow.nodeDetails.endedAt': '结束时间', // 节点结束时间
  'runFlow.nodeDetails.metadata': '元数据', // 节点元数据
  'runFlow.nodeDetails.expandAttempts': '展开尝试', // 展开尝试按钮
  'runFlow.nodeDetails.collapseAttempts': '收起尝试', // 收起尝试按钮
  'runFlow.nodeDetails.attemptList': '运行尝试', // 运行尝试列表
  'runFlow.nodeDetails.contextBlocks': '上下文输入', // 上下文输入块
  'runFlow.nodeDetails.column.name': '名称', // 尝试列表名称列
  'runFlow.nodeDetails.column.status': '状态', // 尝试列表状态列
  'runFlow.nodeDetails.column.duration': '耗时', // 尝试列表耗时列
  'runFlow.nodeDetails.column.records': '记录', // 尝试列表记录列
  'runFlow.nodeDetails.column.time': '时间', // 尝试列表时间列
  'runFlow.nodeDetails.contextQuality': '上下文质量', // 上下文质量标签
  'runFlow.nodeDetails.overallScore': '综合评分', // 综合评分
  'runFlow.nodeDetails.qualityLevel': '等级', // 质量等级
  'runFlow.nodeDetails.blockScores': '数据块评分', // 数据块评分
  'runFlow.nodeDetails.count.available': '可用', // 可用数量
  'runFlow.nodeDetails.count.missing': '缺失', // 缺失数量
  'runFlow.nodeDetails.count.partial': '部分', // 部分数量
  'runFlow.nodeDetails.count.degraded': '部分降级', // 降级数量
  'runFlow.nodeDetails.count.fallback': '降级回退', // 回退数量
  'runFlow.nodeDetails.count.skipped': '跳过', // 跳过数量

  'report.addToWatchlist': '加入自选', // 报告加入自选按钮
  'report.removeFromWatchlist': '从自选删除', // 报告移除自选按钮
  'report.watchlist': '自选', // 报告自选标签

  'settings.actionSuccess': '操作成功', // 设置操作成功提示
  'settings.activePanelDescription': '使用统一字段卡片维护当前分类的系统配置。', // 当前分类配置说明
  'settings.activePanelTitle': '当前分类配置项', // 当前分类配置标题
  'settings.agentSettings': 'Agent 设置', // Agent 设置入口
  'settings.alphaSift': 'AlphaSift 选股', // AlphaSift 选股标题
  'settings.alphaSiftDescription': '启用内置 AlphaSift 实验性质选股能力。', // AlphaSift 选股说明
  'settings.alphaSiftDisabled': '选股未开启', // 选股未开启状态
  'settings.alphaSiftEnabled': '选股已开启', // 选股已开启状态
  'settings.alphaSiftRisk': '实验功能与风险提示：选股结果仅用于研究和辅助判断，不构成投资建议；市场有风险，交易决策和损益由使用者自行承担。', // AlphaSift 风险提示
  'settings.alphaSiftSummary': '开启后左侧导航会显示“选股”；策略和候选生成来自 AlphaSift，HRS 会补充行情、基本面和新闻上下文。', // AlphaSift 概要说明
  'settings.authCurrentPassword': '当前管理员密码', // 当前管理员密码标签
  'settings.authDescription': '管理管理员密码认证，保护您的系统配置安全。', // 认证设置说明
  'settings.authDisabled': '未启用', // 认证未启用状态
  'settings.authEnabled': '已启用', // 认证已启用状态
  'settings.authFailure': '认证设置失败', // 认证设置失败提示
  'settings.authHelperDefault': '管理员认证可保护 Web 设置页及 API 接口，防止未经授权的访问。', // 认证默认帮助说明
  'settings.authHelperEnabled': '管理员认证已启用。如需更新密码，请使用下方的“修改密码”功能。', // 认证已启用帮助说明
  'settings.authHelperNoPassword': '系统尚未设置密码。启用认证前请先设置初始管理员密码，设置后请妥善保管。', // 无密码帮助说明
  'settings.authHelperPasswordRetained': '系统已保留之前设置的管理员密码。输入当前密码即可快速重新启用认证。', // 密码已保留帮助说明
  'settings.authHelperTurnOff': '若当前登录会话仍有效，可直接关闭认证；若会话已失效，请输入当前管理员密码。', // 关闭认证帮助说明
  'settings.authPasswordHintOff': '关闭认证前可能需要验证身份', // 关闭认证提示
  'settings.authPasswordHintRetained': '输入旧密码以重新激活认证', // 重新激活认证提示
  'settings.authPasswordPlaceholder': '请输入当前密码', // 认证密码占位符
  'settings.authRequiredPassword': '设置新密码是必填项', // 新密码必填提示
  'settings.authSetPassword': '设置管理员密码', // 设置管理员密码按钮
  'settings.authSetPasswordPlaceholder': '输入新密码 (至少 6 位)', // 新密码占位符
  'settings.authStatus': '管理员认证', // 管理员认证状态
  'settings.authSuccessDisabled': '认证已关闭', // 认证关闭成功提示
  'settings.authSuccessUpdated': '认证设置已更新', // 认证更新成功提示
  'settings.authTitle': '认证与登录保护', // 认证设置标题
  'settings.categoryNavDescription': '按模块整理系统设置与认证能力。', // 分类导航说明
  'settings.categoryNavTitle': '配置分类', // 配置分类标题
  'settings.changePasswordConfirm': '确认新密码', // 确认新密码标签
  'settings.changePasswordConfirmPlaceholder': '再次输入新密码', // 确认新密码占位符
  'settings.changePasswordCurrent': '当前密码', // 当前密码标签
  'settings.changePasswordCurrentPlaceholder': '输入当前密码', // 当前密码占位符
  'settings.changePasswordDescription': '更新当前管理员登录密码。修改成功后，后续登录请使用新密码。', // 修改密码说明
  'settings.changePasswordFailure': '修改失败', // 修改密码失败提示
  'settings.changePasswordNew': '新密码', // 新密码标签
  'settings.changePasswordNewHint': '至少 6 位。', // 新密码要求提示
  'settings.changePasswordNewPlaceholder': '输入新密码', // 新密码占位符
  'settings.changePasswordRequiredCurrent': '请输入当前密码', // 当前密码必填提示
  'settings.changePasswordRequiredNew': '请输入新密码', // 新密码必填提示
  'settings.changePasswordSave': '保存新密码', // 保存新密码按钮
  'settings.changePasswordShort': '新密码至少 6 位', // 密码过短提示
  'settings.changePasswordSuccess': '修改成功', // 修改密码成功提示
  'settings.changePasswordSuccessMessage': '管理员密码已更新。', // 修改密码成功消息
  'settings.changePasswordTitle': '修改密码', // 修改密码标题
  'settings.checkDesktopUpdate': '检查更新', // 检查桌面端更新按钮
  'settings.checkingDesktopUpdate': '检查中...', // 检查更新中状态
  'settings.configBackup': '配置备份', // 配置备份标题
  'settings.configBackupDescription': '导出当前已保存的 .env 备份，或从备份文件恢复配置。导入会覆盖备份中出现的键并立即重载。', // 配置备份说明
  'settings.currentCategoryEmptyDescription': '当前分类没有可编辑字段；可切换左侧分类继续查看其它系统配置。', // 当前分类空状态描述
  'settings.currentCategoryEmptyTitle': '当前分类下暂无配置项', // 当前分类空状态标题
  'settings.desktopCheckError': '检查更新失败', // 桌面端检查更新失败
  'settings.desktopChecking': '正在检查更新', // 桌面端检查更新中
  'settings.desktopCurrentNoStatus': '当前尚无更新状态，应用启动后会在后台自动检查。', // 桌面端无更新状态
  'settings.desktopDownload': '前往下载', // 前往下载按钮
  'settings.desktopDownloaded': '更新已下载', // 更新已下载状态
  'settings.desktopDownloading': '正在下载更新', // 更新下载中状态
  'settings.desktopInstall': '重启安装', // 重启安装按钮
  'settings.desktopInstalling': '正在安装更新', // 安装更新中状态
  'settings.desktopLatest': '最新版本', // 最新版本标签
  'settings.desktopManualUnsupported': '当前桌面端不支持自动安装更新，请前往发布页手动更新。', // 不支持自动更新提示
  'settings.desktopUpdate': '桌面端更新', // 桌面端更新标题
  'settings.desktopUpdateAvailable': '发现新版本', // 发现新版本提示
  'settings.desktopUpdateDescription': '启动后会自动检查 GitHub Releases 最新正式版；Windows 安装版会后台下载更新，确认后静默重启安装。', // 桌面端更新说明
  'settings.desktopUpdateDownloadedMessage': '新版本已下载，可重启应用完成安装。', // 更新已下载消息
  'settings.desktopUpdateDownloadingMessage': '正在后台下载桌面端更新{percent}。', // 更新下载中消息
  'settings.desktopUpdateErrorMessage': '无法完成更新检查，请稍后重试。', // 更新检查错误消息
  'settings.desktopUpdateInstallingMessage': '正在重启并安装更新。', // 安装更新消息
  'settings.desktopUpdateMessage': '当前 {current}，最新 {latest}。{message}', // 更新状态消息
  'settings.desktopUpdateReleaseMessage': '可前往 GitHub Releases 下载更新。', // 发布页下载消息
  'settings.desktopUpdateCheckingMessage': '正在检查 GitHub Releases 中是否有可用新版本。', // 检查更新中消息
  'settings.desktopUpToDate': '已是最新版本', // 已是最新版本状态
  'settings.desktopUpToDateMessage': '当前桌面端已是最新版本。', // 已是最新版本消息
  'settings.diagnosticHintDesktop': '请查看并提供桌面端日志 desktop.log，同时补充 release 版本、Windows 版本和触发入口。', // 桌面端诊断提示
  'settings.diagnosticHintWeb': '请查看浏览器开发者工具控制台与后端日志，并补充 release 版本、浏览器版本和触发入口。', // Web 端诊断提示
  'settings.disabledAuthBackupWarning': '当前 Web 端未开启管理员鉴权，导出/导入 `.env` 备份功能已停用；请先将 `ADMIN_AUTH_ENABLED` 设为 `true` 并完成管理员登录后再使用。', // 未启用认证时备份警告
  'settings.enableAuth': '开启认证', // 开启认证按钮
  'settings.disableAuth': '关闭认证', // 关闭认证按钮
  'settings.keepAuthDisabled': '保持已关闭', // 保持已关闭按钮
  'settings.keepAuthEnabled': '保持已开启', // 保持已开启按钮
  'settings.enableAlphaSift': '开启选股', // 开启选股按钮
  'settings.disableAlphaSift': '关闭选股', // 关闭选股按钮
  'settings.enablingAlphaSift': '开启中...', // 开启选中状态
  'settings.disablingAlphaSift': '关闭中...', // 关闭选中状态
  'settings.enabledAlphaSiftSuccess': '已开启 AlphaSift 选股。', // 开启选股成功提示
  'settings.disabledAlphaSiftSuccess': '已关闭 AlphaSift 选股。', // 关闭选股成功提示
  'settings.setupStatusConfigured': '已配置', // 已配置状态
  'settings.setupStatusInherited': '已继承', // 已继承状态
  'settings.setupStatusNeedsAction': '待处理', // 待处理状态
  'settings.setupStatusOptional': '可选', // 可选状态
  'settings.setupGuideHiddenTitle': '首次启动配置检查已隐藏', // 配置检查已隐藏标题
  'settings.setupGuideHiddenDescription': '需要重新检查基础配置、模型和通知时，可再次展开。', // 配置检查已隐藏描述
  'settings.setupGuideOpen': '展开检查', // 展开检查按钮
  'settings.setupGuideTitle': '首次启动配置检查', // 首次启动配置检查标题
  'settings.setupGuideDescription': '按最小可用分析流程检查自选股、模型渠道和通知配置，完成后可直接发起一次简短试跑。', // 首次启动配置检查说明
  'settings.setupGuideCheckingTitle': '正在检查首次启动配置', // 正在检查配置标题
  'settings.setupGuideCheckingSummary': '正在读取配置状态，完成后会显示缺失项和试跑入口。', // 正在检查配置摘要
  'settings.setupGuideUnknownTitle': '暂无法判断配置状态', // 无法判断配置状态标题
  'settings.setupGuideUnknownSummary': '配置状态读取失败。可先检查或修改设置项，稍后刷新检查结果。', // 无法判断配置状态摘要
  'settings.setupGuideCompleteTitle': '基础配置已满足最小可用分析', // 基础配置已完成标题
  'settings.setupGuideIncompleteTitle': '还有基础配置需要处理', // 基础配置未完成标题
  'settings.setupGuideMissingSummary': '还缺少 {count} 项：{labels}', // 缺少配置项摘要
  'settings.setupGuideReadySummary': '所有必需项已就绪，可运行一次简短分析验证链路。', // 配置就绪摘要
  'settings.setupGuideRefreshing': '刷新中...', // 刷新中状态
  'settings.setupGuideRefresh': '刷新检查', // 刷新检查按钮
  'settings.setupGuideHide': '暂时隐藏', // 暂时隐藏按钮
  'settings.setupGuideConfigureLlm': '配置模型', // 配置模型按钮
  'settings.setupGuideAddStocks': '维护自选股', // 维护自选股按钮
  'settings.setupGuideConfigureNotification': '配置通知', // 配置通知按钮
  'settings.setupGuideSmokeRunning': '提交中...', // 提交中状态
  'settings.setupGuideSmokeNeedsStock': '需要至少一个自选股代码后才能试跑。', // 试跑需要自选股提示
  'settings.setupGuideRunSmoke': '简短试跑', // 简短试跑按钮
  'settings.setupGuideSmokeNotReady': '请先完成必需配置后再运行试跑。', // 试跑未就绪提示
  'settings.setupGuideSmokeUnavailableTitle': '暂不能试跑', // 暂不能试跑标题
  'settings.setupGuideSmokeAcceptedWithTask': '已提交 {stock} 的简短分析任务：{taskId}', // 试跑已提交含任务
  'settings.setupGuideSmokeAccepted': '已提交 {stock} 的简短分析任务。', // 试跑已提交
  'settings.schedulerAddTime': '添加时间', // 添加时间按钮
  'settings.schedulerDescription': '配置自动分析的每日执行时间，保存后长运行的 Web/API/Desktop 进程会按新配置生效。', // 定时任务说明
  'settings.schedulerDisabled': '未启用', // 定时任务未启用状态
  'settings.schedulerEffectiveTimes': '生效时间', // 生效时间列表
  'settings.schedulerEnable': '启用定时任务', // 启用定时任务按钮
  'settings.schedulerEnabled': '已启用', // 定时任务已启用状态
  'settings.schedulerEnableDescription': '开启后会按下方时间自动执行分析任务。', // 启用定时任务说明
  'settings.schedulerLastError': '最近错误', // 最近错误时间
  'settings.schedulerLastSuccess': '上次成功', // 上次成功时间
  'settings.schedulerNextRun': '下次执行', // 下次执行时间
  'settings.schedulerRefresh': '刷新状态', // 刷新状态按钮
  'settings.schedulerRefreshing': '刷新中...', // 刷新中状态
  'settings.schedulerRemoveTime': '删除时间', // 删除时间按钮
  'settings.schedulerRunAccepted': '已提交执行请求。', // 执行请求已提交提示
  'settings.schedulerRunNow': '立即执行一次', // 立即执行一次按钮
  'settings.schedulerRunning': '运行中', // 运行中状态
  'settings.schedulerRunningNow': '执行中...', // 执行中状态
  'settings.schedulerStatus': '当前状态', // 当前状态标签
  'settings.schedulerTimeInputAria': '定时执行时间 {index}', // 定时执行时间无障碍标签
  'settings.schedulerTimes': '定时执行时间', // 定时执行时间列表
  'settings.schedulerTitle': '定时任务', // 定时任务标题
  'settings.envExported': '已导出当前已保存的 .env 备份。', // 导出成功提示
  'settings.envImported': '已导入 .env 备份并重新加载配置。', // 导入成功提示
  'settings.envImportedRefreshFailedMessage': '备份已导入，但重新加载配置失败，请手动重载页面。', // 导入后刷新失败消息
  'settings.envImportedRefreshFailedRaw': 'Env import succeeded but config refresh failed', // 导入后刷新失败原始信息
  'settings.envImportedRefreshFailedTitle': '配置已导入但刷新失败', // 导入后刷新失败标题
  'settings.exportEnv': '导出 .env', // 导出 .env 按钮
  'settings.exportingEnv': '导出中...', // 导出中状态
  'settings.fallbackVersionWarning': '当前构建未提供发布版本，页面显示为 development；可结合代码版本和构建时间确认静态资源是否已更新。', // 版本回退警告
  'settings.fieldAddKey': '添加 Key', // 添加 Key 按钮
  'settings.fieldDelete': '删除', // 删除字段按钮
  'settings.fieldSensitiveHint': '敏感内容默认隐藏，可点击眼睛图标查看明文。', // 敏感字段提示
  'settings.fieldSensitiveMultiHint': ' 支持添加多个输入框进行增删。', // 敏感多值字段提示
  'settings.helpClose': '关闭配置说明', // 关闭配置说明按钮
  'settings.helpExamples': '配置样例', // 配置样例标签
  'settings.helpImpact': '影响范围', // 影响范围标签
  'settings.helpNotes': '注意事项', // 注意事项标签
  'settings.helpPurpose': '用途', // 用途标签
  'settings.helpRelatedDocs': '相关文档', // 相关文档标签
  'settings.helpTitleFallback': '配置说明', // 配置说明默认标题
  'settings.helpTooltip': '查看配置说明', // 查看配置说明提示
  'settings.helpValueNotes': '取值说明', // 取值说明标签
  'settings.importConfirmContinue': '继续导入', // 继续导入按钮
  'settings.importConfirmMessage': '当前页面还有未保存修改。继续导入会丢弃这些本地草稿，并立即用备份文件中的键值更新已保存配置。', // 导入确认消息
  'settings.importConfirmTitle': '导入会覆盖当前草稿', // 导入确认标题
  'settings.importEnv': '导入 .env', // 导入 .env 按钮
  'settings.importingEnv': '导入中...', // 导入中状态
  'settings.intelligentImport': '智能导入', // 智能导入标题
  'settings.intelligentImportDescription': '从图片、文件或剪贴板中提取股票代码，并合并到自选股列表。', // 智能导入说明
  'settings.intelligentImportSupportedInputs': '支持图片、CSV/Excel 文件与剪贴板文本', // 智能导入支持输入类型
  'settings.intelligentImportHint': '图片识别需预先配置 Vision 模型。建议先人工核对解析结果，再合并到自选股。', // 智能导入提示
  'settings.intelligentImportChooseImage': '选择图片', // 选择图片按钮
  'settings.intelligentImportChooseFile': '选择文件', // 选择文件按钮
  'settings.intelligentImportPastePlaceholder': '或粘贴 CSV/Excel 复制的文本...', // 粘贴文本占位符
  'settings.intelligentImportParse': '解析', // 解析按钮
  'settings.intelligentImportReviewWarning': '建议人工逐条核对后再合并。高置信度默认勾选，中/低置信度需手动确认。', // 人工核对警告
  'settings.intelligentImportSelectionSummary': '共 {valid} 条可合并，已勾选 {checked} 条', // 选择摘要
  'settings.intelligentImportClear': '清空', // 清空按钮
  'settings.intelligentImportMergeToWatchlist': '合并到自选股', // 合并到自选股按钮
  'settings.intelligentImportImageTypeError': '图片仅支持 JPG、PNG、WebP、GIF', // 图片类型错误提示
  'settings.intelligentImportImageSizeError': '图片不超过 5MB', // 图片大小错误提示
  'settings.intelligentImportFileSizeError': '文件不超过 2MB', // 文件大小错误提示
  'settings.intelligentImportTextSizeError': '粘贴文本不超过 100KB', // 文本大小错误提示
  'settings.intelligentImportRecognitionFailed': '识别失败，请重试', // 识别失败提示
  'settings.intelligentImportRateLimited': '请求过于频繁，请稍后再试', // 请求频繁提示
  'settings.intelligentImportTimeout': '请求超时，请检查网络后重试', // 请求超时提示
  'settings.intelligentImportParseFailed': '解析失败', // 解析失败提示
  'settings.intelligentImportLoadConfigFirst': '请先加载配置后再合并', // 先加载配置提示
  'settings.intelligentImportConfigUpdated': '配置已更新，请再次点击「合并到自选股」', // 配置已更新提示
  'settings.intelligentImportMergeFailed': '合并保存失败', // 合并保存失败提示
  'settings.generationBackendConcurrency': '并发 {count}', // 并发数显示
  'settings.generationBackendFallback': '备用后端', // 备用后端标签
  'settings.generationBackendGenerationOnly': '仅生成', // 仅生成标签
  'settings.generationBackendHealthFailed': '检测失败', // 检测失败状态
  'settings.generationBackendHealthPassed': '检测通过', // 检测通过状态
  'settings.generationBackendHealthSkipped': '已跳过', // 已跳过状态
  'settings.generationBackendLiteLLMDescription': '当前后端用于报告生成；问股工具调用仍沿用 LiteLLM Agent 路径。', // LiteLLM 后端说明
  'settings.generationBackendLocalCliDescription': '本地 CLI 只用于报告和文本生成，不支持问股工具调用。', // 本地 CLI 后端说明
  'settings.generationBackendNeedsAction': '需要处理', // 需要处理状态
  'settings.generationBackendPrimary': '主后端', // 主后端标签
  'settings.generationBackendRefresh': '刷新', // 刷新按钮
  'settings.generationBackendRefreshing': '刷新中', // 刷新中状态
  'settings.generationBackendRunnable': '可尝试运行', // 可尝试运行状态
  'settings.generationBackendSmokeFailed': '冒烟测试失败', // 冒烟测试失败状态
  'settings.generationBackendSmokePassed': '冒烟测试通过', // 冒烟测试通过状态
  'settings.generationBackendSmokePassedMessage': '生成后端冒烟测试通过。', // 冒烟测试通过消息
  'settings.generationBackendSmokeTest': 'JSON 冒烟测试', // JSON 冒烟测试按钮
  'settings.generationBackendSmokeTesting': '测试中', // 测试中状态
  'settings.generationBackendStatus': '生成后端状态', // 生成后端状态标题
  'settings.generationBackendStatusDescription': '快速检查只读取配置，并检查本地 CLI 可执行文件是否可见；要确认真实请求是否能跑通，请运行 JSON 冒烟测试。', // 生成后端状态说明
  'settings.generationBackendToolsSupported': '工具调用', // 工具调用支持标签
  'settings.agentBackendStatus': '问股运行状态', // 问股运行状态标题
  'settings.agentBackendStatusDescription': '这里只检查当前设置、本机 Codex 命令和问股所需协议是否允许尝试启动；不会登录、调用模型或读取股票数据。真正是否能完成问股，会在你发送问题时确认。', // 问股运行状态说明
  'settings.agentBackendSectionTitle': '问股生成方式', // 问股生成方式标题
  'settings.agentBackendSectionDescription': '在同一个问股页面中选择默认模型配置或本机 Codex，并在保存前预览当前草稿是否可运行。', // 问股生成方式说明
  'settings.agentBackendDefaultLabel': '默认模型', // 默认模型标签
  'settings.agentBackendCodexLabel': 'Codex Agent', // Codex Agent 标签
  'settings.agentBackendCanTry': '可以尝试', // 可以尝试状态
  'settings.agentBackendNeedsAction': '需要处理', // 需要处理状态
  'settings.agentBackendExperimental': '实验功能', // 实验功能标签
  'settings.agentBackendCanTryDescription': '基础环境检查已通过。你可以回到问股页直接提问，首次问题会进行真实执行。', // 可以尝试说明
  'settings.agentBackendUnavailableDescription': '当前问股方式暂不可用，请检查设置后重试。', // 不可用说明
  'settings.agentBackendCommandNotFound': '运行 HRS 的设备找不到 Codex。请在该设备安装 Codex，并确保 HRS 后端进程可以从 PATH 找到它。', // Codex 未找到提示
  'settings.agentBackendModeDisabledTitle': '需要启用 Agent 模式', // 需启用 Agent 模式标题
  'settings.agentBackendModeDisabled': 'Agent 模式当前未启用。点击下方按钮修改页面草稿，然后保存设置后再使用问股。', // Agent 模式未启用提示
  'settings.agentBackendEnableMode': '启用 Agent 模式', // 启用 Agent 模式按钮
  'settings.agentBackendPlatformUnsupported': 'Codex 本地 Agent 当前不支持原生 Windows。可在 macOS、Linux，或让 HRS 后端完整运行于 WSL 后使用。', // 平台不支持提示
  'settings.agentBackendInvalidTimeout': 'Codex 必须设置大于 0 的 Agent 整体时限，确保成功、失败、超时或停止都能明确结束。', // 超时设置无效提示
  'settings.agentBackendSingleOnlyTitle': '需要切换为单 Agent', // 需切换单 Agent 标题
  'settings.agentBackendSingleOnly': 'Codex 本地 Agent 当前只支持单 Agent 问股。此操作只修改页面草稿，仍需点击保存。', // 仅支持单 Agent 提示
  'settings.agentBackendUseSingle': '切换为单 Agent', // 切换为单 Agent 按钮
  'settings.agentBackendCodexNoticeTitle': 'Codex 本地 Agent（实验）', // Codex 本地 Agent 标题
  'settings.agentBackendCodexNotice': 'Codex 目前只能读取已保存的分析上下文和回测汇总。实时行情、新闻、市场热点、技术指标重算、个股回测明细和持仓工具暂不开放；需要这些能力时，请选择“默认模型”。点击停止后，本次 Codex 和工具任务会一起结束。此选择只影响问股 Chat；Multi Agent、Deep Research、普通报告和定时任务保持原路径。Codex 不是离线模型，问题和工具结果可能由 Codex 配置的服务处理。', // Codex 本地 Agent 说明
  'settings.agentBackendRefresh': '刷新状态', // 刷新状态按钮
  'settings.agentBackendRefreshing': '正在检查', // 正在检查状态
  'settings.agentBackendTechnicalDetails': '技术详情', // 技术详情标签
  'settings.agentBackendVersion': '版本', // 版本标签
  'settings.agentBackendErrorCode': '错误代码', // 错误代码标签
  'chat.agentBackendUnavailableTitle': '当前问股方式不可用', // 问股方式不可用标题
  'chat.agentModeDisabled': 'Agent 模式尚未启用，请前往 Agent 设置启用并保存后再试。', // Agent 模式未启用提示
  'chat.agentPlatformUnsupported': 'Codex 本地 Agent 当前不支持原生 Windows，请改用默认模型问股，或在支持的系统上运行 HRS 后端。', // 平台不支持提示
  'chat.codexBackendBadge': 'Codex Agent · 实验', // Codex Agent 徽标
  'chat.defaultBackendBadge': '默认模型', // 默认模型徽标
  'chat.codexUnavailableMessage': '当前设备的 Codex 基础环境暂不满足问股要求，请前往 Agent 设置检查安装和单 Agent 配置。', // Codex 不可用消息
  'chat.defaultUnavailableMessage': '默认模型问股当前不可用，请前往 Agent 设置检查模型配置。', // 默认模型不可用消息
  'chat.statusUnavailableTitle': '暂时无法读取问股运行状态', // 状态不可用标题
  'chat.statusUnavailableMessage': '当前无法确认问股运行环境，因此暂不发送。你可以手动重新检查，问题内容不会丢失。', // 状态不可用消息
  'chat.statusCheckingTitle': '正在确认问股运行环境', // 正在确认状态标题
  'chat.statusCheckingMessage': '这里只检查环境是否允许尝试，不会调用模型或读取股票数据。', // 正在确认状态消息
  'chat.recheckAgentStatus': '重新检查', // 重新检查按钮
  'chat.codexLimitedTitle': 'Codex 当前可用范围', // Codex 可用范围标题
  'chat.codexLimitedMessage': '可读取已保存的分析上下文和回测汇总；实时行情、新闻、市场热点、技术指标重算、个股回测明细和持仓查询请使用默认模型。', // Codex 可用范围消息
  'chat.codexChangeBackend': '切换问股方式', // 切换问股方式按钮
  'chat.stopAnalysis': '停止分析', // 停止分析按钮
  'chat.stoppingAnalysis': '正在停止…', // 正在停止状态
  'chat.analysisStopped': '本次分析已停止，后台任务也已结束。', // 分析已停止提示
  'chat.analysisTimedOut': '本次分析已超时并结束，请缩小问题范围后重试。', // 分析已超时提示
  'chat.stopRequestFailed': '停止请求未送达，分析仍在继续。请再次停止或稍后重试。', // 停止请求失败提示
  'chat.introDefault': '向 AI 询问个股分析，获取基于技能视角的交易建议与实时决策报告。', // 默认问股引导文案
  'chat.introCodex': '使用已保存的分析上下文和回测汇总，向 Codex 询问个股。', // Codex 问股引导文案
  'chat.emptyDescriptionDefault': '输入「分析 600519」或「茅台现在能买吗」，AI 将调用实时数据工具为您生成决策报告。', // 默认问股空状态描述
  'chat.emptyDescriptionCodex': '输入「分析 600519」或「历史分析整体表现如何」，Codex 将基于已保存的分析上下文和回测汇总回答。', // Codex 问股空状态描述
  'chat.openAgentSettings': '前往 Agent 设置', // 前往 Agent 设置按钮
  'settings.llmAccess': 'AI 模型接入', // AI 模型接入标题
  'settings.llmAccessDescription': '统一管理模型渠道、基础地址、API Key、主模型与备选模型。', // AI 模型接入说明
  'settings.notificationSettings': '通知设置', // 通知设置标题
  'settings.notificationTest': '通知测试', // 通知测试标题
  'settings.notificationTestBody': '正文', // 通知测试正文标签
  'settings.notificationTestChannel': '渠道', // 通知测试渠道标签
  'settings.notificationTestContent': '这是一条来自 HRS Web 设置页的通知测试消息。', // 通知测试内容
  'settings.notificationTestDescription': '使用当前页面草稿发送一条真实测试通知；测试不会保存配置。', // 通知测试说明
  'settings.notificationTestFailure': '测试失败', // 测试失败提示
  'settings.notificationTestSend': '发送测试', // 发送测试按钮
  'settings.notificationTestSuccess': '测试成功', // 测试成功提示
  'settings.notificationTestTimeout': '超时秒数', // 超时秒数标签
  'settings.notificationTestTitle': '标题', // 通知测试标题标签
  'settings.notificationTestTitleValue': 'HRS 通知测试', // 通知测试标题值
  'settings.notificationTesting': '测试中...', // 测试中状态
  'settings.openConfigItems': '查看配置项', // 查看配置项按钮
  'settings.pageDescription': '统一管理模型、数据源、通知、安全认证与导入能力。', // 设置页描述
  'settings.pageTitle': '系统设置', // 系统设置标题
  'settings.pageTitleDocument': '系统设置 - HRS', // 系统设置文档标题
  'settings.promptCacheAdvancedDescription': '维护 provider prompt cache 的观测、主动 hint 与脱敏诊断；默认配置已适合普通使用。', // Prompt Cache 高级设置说明
  'settings.promptCacheAdvancedTitle': 'Provider Prompt Cache 高级设置', // Prompt Cache 高级设置标题
  'settings.reload': '重新加载', // 重新加载按钮
  'settings.reset': '重置', // 重置按钮
  'settings.revert': '还原', // 还原按钮
  'settings.saveConfig': '保存配置', // 保存配置按钮
  'settings.saveConfigWithCount': '保存配置 ({count})', // 保存配置含数量按钮
  'settings.saveRetry': '重试保存', // 重试保存按钮
  'settings.saving': '保存中...', // 保存中状态
  'settings.updateBuildDescription': '重新执行前端构建或 Docker 镜像构建后，此处的代码版本和构建时间会更新，可用来确认当前页面资源是否已切换。', // 更新构建说明
  'settings.versionBuildTime': '构建时间', // 构建时间标签
  'settings.versionRevision': '代码版本', // 代码版本标签
  'settings.versionDesktop': '桌面端版本', // 桌面端版本标签
  'settings.versionInfo': '版本信息', // 版本信息标题
  'settings.versionInfoDescription': '用于确认当前 WebUI 静态资源是否已经切换到最新构建。', // 版本信息说明
  'settings.versionWebui': 'WebUI 版本', // WebUI 版本标签
  'settings.viewConfigItems': '查看配置项', // 查看配置项按钮
  'settings.envExportNote': '导出内容仅包含当前已保存配置，不包含页面上尚未保存的本地草稿。', // 导出说明
  'settings.envDockerNote': 'Docker 部署中，`--env-file` / Compose `env_file` 只会在启动时注入环境变量；此处导出/导入的是后端当前活跃的 `.env` 文件。若需要让 WebUI 保存值随容器重建保留，请将 `ENV_FILE` 指向 `/app/data/runtime.env` 等可写数据卷文件，并避免启动环境里继续保留同名旧值。', // Docker 环境变量说明
} as const;

export type UiTextKey = keyof typeof zh;

export default zh;
