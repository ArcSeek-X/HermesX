/**
 * @file uiText-zh.ts
 * @description 中文（zh）界面文案配置，是所有 i18n 键值的真源（source of truth）
 * @module i18n
 */

const zh = {

  // ---- 第 1 类 全局 common ----
  'common.cancel': '取消', // 通用取消按钮文案
  'common.clear': '清除', // 通用清除文案
  'common.close': '关闭', // 通用关闭按钮文案
  'common.closeDrawer': '关闭抽屉', // 关闭抽屉组件
  'common.confirm': '确定', // 通用确认按钮文案
  'common.copied': '已复制!', // 复制成功提示
  'common.copy': '复制', // 复制按钮文案
  'common.datetime.day': '日', // 日历视图粒度：日
  'common.datetime.list': '列表', // 日历视图粒度：列表
  'common.datetime.month': '月', // 日历视图粒度：月
  'common.datetime.today': '今天', // 日历回到今天按钮
  'common.datetime.week': '周', // 日历视图粒度：周
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

  // ---- 第 2 类 语言 language ----
  'language.chineseSimplified': '简体中文', // 简体中文语言选项
  'language.chineseTraditional': '繁体中文', // 繁体中文语言选项
  'language.english': 'English', // 英文语言选项
  'language.short.en': 'EN', // 英文语言简写
  'language.short.zh': '中', // 中文语言简写
  'language.short.zhHant': '繁', // 繁体中文语言简写
  'language.toggle': '切换界面语言', // 切换语言按钮提示

  // ---- 第 3 类 主题 theme ----
  'theme.themeMode.dark': '深色', // 深色主题名称
  'theme.themeMode.light': '浅色', // 浅色主题名称
  'theme.themeMode.settingTitle': '主题模式', // 主题模式菜单标题
  'theme.themeColor.settingTitle': '主色', // 主题主色配置标签
  'theme.reset': '重置', // 重置主题主色按钮
  'theme.save': '保存', // 保存主题设置按钮
  'theme.themeMode.system': '跟随系统', // 跟随系统主题
  'theme.sidebarTheme.settingTitle': '侧栏风格', // 侧栏视觉主题设置标题
  'theme.sidebarTheme.pill': '胶囊圆角', // 侧栏风格：大圆角胶囊感
  'theme.sidebarTheme.square': '方正', // 侧栏风格：方角

  // ---- 第 4 类 布局与菜单 layout ----
  // 布局直属 layout.*
  'layout.appFallbackDescription': 'Web workspace', // 应用回退描述文案
  'layout.appFallbackTitle': 'HermesX', // 应用回退标题
  'layout.collapseSidebar': '折叠侧边栏', // 折叠侧边栏按钮
  'layout.desktopSidebar': '桌面侧边导航', // 桌面端侧边栏标签
  'layout.expandSidebar': '展开侧边栏', // 展开侧边栏按钮
  'layout.logout': '退出', // 退出登录按钮
  'layout.logoutConfirm': '确认退出', // 退出确认按钮
  'layout.logoutMessage': '确认退出当前登录状态吗？退出后需要重新输入密码登录。', // 退出确认提示文案
  'layout.logoutTitle': '退出登录', // 退出登录弹窗标题
  'layout.mainNav': '主导航', // 主导航区域标签
  'layout.newChatMessage': '问股有新消息', // 问股新消息提示
  'layout.openNav': '打开导航菜单', // 打开导航菜单提示
  // 头部操作区 layout.header.*
  'layout.header.goHome': '回到主页', // 头部回到主页按钮
  'layout.header.language': '界面语言', // 头部中英文切换按钮
  'layout.header.myApps': '我的应用', // 头部我的应用按钮
  'layout.header.themeSettings': '主题设置', // 头部主题设置按钮
  'layout.header.userSettings': '个人设置', // 头部个人设置按钮
  'layout.header.fullscreen': '全屏', // 头部全屏切换按钮（进入全屏）
  'layout.header.exitFullscreen': '退出全屏', // 头部全屏切换按钮（退出全屏）

  // 导航菜单（产品模式） layout.nav.*
  'layout.nav.alerts.title': '告警', // 告警导航项
  'layout.nav.alerts.description': '规则、触发记录与通知尝试', // 告警导航项描述
  'layout.nav.backtest.title': '回测', // 回测导航项
  'layout.nav.backtest.description': '回测任务与结果浏览', // 回测导航项描述
  'layout.nav.chat.title': '问股', // 问股导航项
  'layout.nav.chat.description': '多轮策略问答与历史会话管理', // 问股导航项描述
  'layout.nav.codeTest.title': '测试', // 测试页导航项
  'layout.nav.codeTest.description': '组件演示与联调测试页', // 测试导航项描述
  'layout.nav.index.title': '总览', // 行情总览导航项
  'layout.nav.index.description': 'A股、港股、美股、日韩市场行情与核心指标总览', // 行情总览导航项描述
  'layout.nav.market.title': '行情', // 行情一级分组导航项
  'layout.nav.market.description': '市场行情、指数总览与板块分析', // 行情一级分组导航项描述
  'layout.nav.emotion.title': '情绪', // 情绪一级分组导航项
  'layout.nav.emotion.description': '市场情绪与涨跌榜单', // 情绪一级分组导航项描述
  'layout.nav.boardlist.title': '涨跌榜', // 涨跌榜导航项
  'layout.nav.boardlist.description': '涨停与跌停榜单总览', // 涨跌榜导航项描述
  'emotion.board.limitUp': '涨停榜单', // 涨跌榜页 TAB：涨停榜单
  'emotion.board.limitDown': '跌停榜单', // 涨跌榜页 TAB：跌停榜单
  'emotion.board.switch': '榜单切换', // 涨跌榜页 TAB 切换无障碍标签
  'emotion.board.col.code': '代码', // 涨停榜单表头：代码
  'emotion.board.col.name': '名称', // 涨停榜单表头：名称
  'emotion.board.col.price': '现价', // 涨停榜单表头：现价
  'emotion.board.col.changePercent': '涨幅', // 涨停榜单表头：涨幅
  'emotion.board.col.limitTime': '涨停时间', // 涨停榜单表头：涨停时间
  'emotion.board.col.boards': '连板', // 涨停榜单表头：连板
  'emotion.board.col.sealAmount': '封单额(亿)', // 涨停榜单表头：封单额
  'emotion.board.col.amount': '成交额(亿)', // 涨停榜单表头：成交额
  'emotion.board.col.turnoverRate': '换手率', // 涨停榜单表头：换手率
  'emotion.board.col.industry': '所属行业', // 涨停榜单表头：所属行业
  'emotion.board.limitDownComing': '跌停榜单开发中', // 跌停榜单内容待开发占位
  'layout.nav.stock.title': '个股', // 个股一级分组导航项
  'layout.nav.stock.description': '个股行情、K 线与多周期分析', // 个股一级分组导航项描述
  'dashboard.tab.a': 'A股', // 总览页市场TAB：A股
  'dashboard.tab.hkUs': '港美', // 总览页市场TAB：港美
  'dashboard.tab.jpKr': '日韩', // 总览页市场TAB：日韩
  'dashboard.marketSwitch': '市场切换', // 总览页市场TAB切换无障碍标签
  'layout.nav.decisionSignals.title': 'AI 建议', // AI 建议导航项
  'layout.nav.decisionSignals.description': 'AI 建议、风险与观察条件', // AI 建议导航项描述
  'layout.nav.home.title': '首页', // 首页导航项
  'layout.nav.home.description': '股票分析与历史报告工作台', // 首页导航项描述
  'layout.nav.kline.title': 'K 线', // K 线导航项
  'layout.nav.kline.description': '个股 K 线走势、技术指标与多周期分析', // K 线导航项描述
  'layout.nav.stockDataView.title': '股票数据视图', // 股票数据视图导航项
  'layout.nav.stockDataView.description': '查看个股行情、K 线与多周期数据视图', // 股票数据视图导航项描述
  'layout.nav.liveCalendar.title': '日历', // 消息日历导航项
  'layout.nav.liveCalendar.description': '宏观、财报、新股、活动等重要事件日历', // 日历导航项描述
  'layout.nav.liveNews.title': '快讯', // 实时快讯导航项
  'layout.nav.liveNews.description': '7x24 财经快讯，按频道筛选与重要级过滤', // 快讯导航项描述
  'layout.nav.news.title': '资讯', // 资讯一级分组导航项
  'layout.nav.news.description': '财经资讯与日历', // 资讯一级分组导航项描述
  'layout.nav.choose.title': '选股', // 选股一级分组导航项
  'layout.nav.choose.description': 'AI 对话选股与智能决策建议', // 选股一级分组导航项描述
  'layout.nav.trading.title': '交易', // 交易一级分组导航项
  'layout.nav.trading.description': '组合持仓与交易管理', // 交易一级分组导航项描述
  'layout.nav.portfolio.title': '持仓', // 持仓导航项
  'layout.nav.portfolio.description': '组合快照、手工录入与风险分析', // 持仓导航项描述
  'layout.nav.review.title': '复盘', // 复盘导航项
  'layout.nav.review.description': '历史复盘与大盘回顾', // 复盘导航项描述
  'layout.nav.screening.title': '选股', // 选股导航项
  'layout.nav.screening.description': 'AlphaSift 策略选股与候选研究', // 选股导航项描述
  'layout.nav.sectorAnalysis.title': '板块', // 板块分析导航项
  'layout.nav.sectorAnalysis.description': '板块涨跌、资金流向与热点追踪', // 板块导航项描述
  'layout.nav.settings.title': '设置', // 设置导航项
  'layout.nav.settings.description': '系统配置、模型与认证管理', // 设置导航项描述
  'layout.nav.stockCloud.title': '个股云图', // 个股云图导航项
  'layout.nav.stockCloud.description': '个股云图与板块分布可视化', // 个股云图导航项描述
  'layout.nav.usage.title': '用量', // 用量导航项
  'layout.nav.usage.description': 'LLM Token 消耗与模型调用明细', // 用量导航项描述
  'layout.nav.watchlist.title': '自选', // 自选导航项
  'layout.nav.watchlist.description': '自选股列表与行情跟踪', // 自选导航项描述
  'layout.nav.discover.title': '发现', // 发现导航项
  'layout.nav.discover.description': '发现者模块：选股与扫描', // 发现者导航项描述
  'layout.nav.eodPicker.title': '尾盘选股', // 尾盘选股导航项
  'layout.nav.eodPicker.description': '一日持股法分析工具 · 筛选分时强势股票', // 尾盘选股导航项描述

  'layout.nav.scanner.title': '信号扫描', // 信号扫描导航项
  'layout.nav.scanner.description': '统一并发控制、支持取消的技术信号扫描器', // 信号扫描导航项描述

  // 导航菜单（调试开发模式） layout.nav.development.*
  'layout.nav.development.docsCheckbox.title': '复选框', // 复选框组件文档导航项
  'layout.nav.development.docsCheckbox.description': 'HrsCheckbox 勾选框组件演示与用法', // 复选框导航项描述
  'layout.nav.development.docsDrawer.title': '抽屉', // 抽屉组件文档导航项
  'layout.nav.development.docsDrawer.description': 'HrsDrawer 侧滑抽屉组件演示与用法', // 抽屉导航项描述
  'layout.nav.development.docsButton.title': '按钮', // 按钮组件文档导航项
  'layout.nav.development.docsButton.description': 'HrsButton 通用按钮组件演示与用法', // 按钮导航项描述
  'layout.nav.development.docsSelect.title': '下拉选择', // 下拉选择组件文档导航项
  'layout.nav.development.docsSelect.description': 'HrsSelect 下拉选择器组件演示与用法', // 下拉选择导航项描述
  'layout.nav.development.docsSeparator.title': '分割线', // 分割线组件文档导航项
  'layout.nav.development.docsSeparator.description': 'Separator 分割线组件演示与用法', // 分割线导航项描述
  'layout.nav.development.docsTable.title': '表格', // 表格组件文档导航项
  'layout.nav.development.docsTable.description': 'Table 通用数据表格组件演示与用法', // 表格导航项描述
  'layout.nav.development.docsToast.title': '轻提示', // 轻提示组件文档导航项
  'layout.nav.development.docsToast.description': 'Toast 命令式轻提示组件演示与用法', // 轻提示导航项描述
  'layout.nav.development.docsInlineToast.title': '内联轻提示', // InlineToast 内联轻提示组件文档导航项
  'layout.nav.development.docsInlineToast.description': 'InlineToast 内联轻提示组件演示与用法', // 内联轻提示导航项描述
  'layout.nav.development.docsModal.title': '模态框', // 模态框组件文档导航项
  'layout.nav.development.docsModal.description': 'Modal 模态框组件演示与用法', // 模态框导航项描述
  'layout.nav.development.docsAnimCard.title': '动画卡片', // 动画卡片组件文档导航项
  'layout.nav.development.docsAnimCard.description': 'AnimCard 动画卡片组件演示与用法', // 动画卡片导航项描述
  'layout.nav.development.docsNewsCard.title': '快讯卡片', // 快讯卡片组件文档导航项
  'layout.nav.development.docsNewsCard.description': 'NewsCard 财经快讯卡片组件演示与用法', // 快讯卡片导航项描述
  'layout.nav.development.docsListCard.title': '列表卡片', // 列表卡片组件文档导航项
  'layout.nav.development.docsListCard.description': 'ListCard 通用列表卡片组件演示与用法', // 列表卡片导航项描述
  'layout.nav.development.docsTabNav.title': '标签页', // 标签页组件文档导航项
  'layout.nav.development.docsTabNav.description': 'TabNav 标签页导航组件演示与用法', // 标签页导航项描述
  'layout.nav.development.docsSideBar.title': '侧边栏', // 侧边栏组件文档导航项
  'layout.nav.development.docsSideBar.description': 'Sidebar 侧边导航组件演示与用法', // 侧边栏导航项描述
  'layout.nav.development.docsInput.title': '输入框', // 输入框组件文档导航项
  'layout.nav.development.docsInput.description': 'Input 通用表单输入组件演示与用法', // 输入框导航项描述
  'layout.nav.development.docsTextArea.title': '文本域', // 文本域组件文档导航项
  'layout.nav.development.docsTextArea.description': 'TextArea 多行文本输入组件演示与用法', // 文本域导航项描述
  'layout.nav.development.docsNumberField.title': '数字输入框', // 数字输入框组件文档导航项
  'layout.nav.development.docsNumberField.description': 'NumberField 数字输入组件演示与用法', // 数字输入框导航项描述
  'layout.nav.development.docsChip.title': '标签芯片', // 标签芯片组件文档导航项
  'layout.nav.development.docsChip.description': 'Chip 圆角胶囊标签组件演示与用法', // 标签芯片导航项描述
  'layout.nav.development.docsEmptyState.title': '空状态', // 空状态组件文档导航项
  'layout.nav.development.docsEmptyState.description': 'EmptyState 空状态组件演示与用法', // 空状态导航项描述

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

  // ---- 第 6 类 异常页面  ----
  // 404页面/重定向页面
  'exception.404.title': '404', // 404 路由标题（route handle）
  'exception.404.description': '404 页面未找到', // 404 路由描述（route handle）
  'exception.redirect.title': '重定向', // 重定向路由标题（route handle）
  'exception.redirect.description': '自动重定向到目标页面', // 重定向路由描述（route handle）
  // exception.routeBoundary.*
  'exception.routeBoundary.backHome': '返回首页', // 路由错误返回首页
  'exception.routeBoundary.backToLogin': '返回登录', // 路由错误返回登录
  'exception.routeBoundary.description': '当前页面资源或组件未能正常加载，可能是网络中断或系统版本已更新。请重新加载页面，或返回登录后再试。', // 路由错误描述
  'exception.routeBoundary.details': '查看详情', // 路由错误展开详情
  'exception.routeBoundary.hideDetails': '收起详情', // 路由错误收起详情
  'exception.routeBoundary.errorDetail': '错误详情', // 路由错误详情代码块标题
  'exception.routeBoundary.copy': '复制', // 复制错误详情
  'exception.routeBoundary.copied': '已复制', // 错误详情已复制到剪贴板
  'exception.routeBoundary.reload': '重新加载', // 路由错误重新加载
  'exception.routeBoundary.title': '页面加载失败', // 路由错误标题

  // ---- 第 7 类 登录/注册 auth ----
  'auth.login.title': '登录页', // 管理员登录页标题（route handle）
  'auth.login.description': '管理员登录认证，进入量化决策工作台', // 管理员登录页路由描述（route handle）
  'auth.login.adminLogin': '管理员登录', // 管理员登录标题
  'auth.login.hidePassword': '隐藏密码', // 隐藏密码按钮提示
  'auth.login.loginDescription': '访问 HRS 量化决策引擎需要有效的身份凭证。', // 登录页描述
  'auth.login.loginFailed': '登录失败', // 登录失败提示
  'auth.login.loginPassword': '登录密码', // 登录密码标签
  'auth.login.loginPasswordPlaceholder': '请输入密码', // 登录密码占位符
  'auth.login.loginSubmit': '授权进入工作台', // 登录提交按钮
  'auth.login.loginSubmitting': '正在建立连接...', // 登录提交中状态
  'auth.login.pageTitle': '登录 - HRS', // 登录页标题
  'auth.login.passwordMismatch': '两次输入的密码不一致', // 密码不一致提示
  'auth.login.passwordRequired': '请输入密码', // 密码必填校验提示
  'auth.login.showPassword': '显示密码', // 显示密码按钮提示
  'auth.login.username': '账号', // 账号标签
  'auth.login.usernamePlaceholder': '请输入账号', // 账号占位符
  'auth.login.usernameRequired': '请输入账号', // 账号必填校验提示
  'auth.login.validationFailed': '验证未通过', // 验证失败提示

  // ---- 第 8 类 页面 ----
  // alerts.*
  'alerts.pageTitle': '告警中心 - HRS', // 【页面】告警-告警页文档标题
  'alerts.headerEyebrow': 'Alert Center', // 【页面】告警-告警中心页眉标签
  'alerts.title': '告警中心', // 【页面】告警-告警中心页标题
  'alerts.subtitle': '管理事件告警、日线技术指标、自选股、持仓/账户联动和大盘红绿灯规则，执行一次性测试，并查看后台评估任务记录的触发历史。', // 【页面】告警-告警中心页副标题
  // chat.*
  'chat.agentBackendUnavailableTitle': '当前问股方式不可用', // 【页面】问股-问股方式不可用标题
  'chat.agentModeDisabled': 'Agent 模式尚未启用，请前往 Agent 设置启用并保存后再试。', // 【页面】问股-Agent 模式未启用提示
  'chat.agentPlatformUnsupported': 'Codex 本地 Agent 当前不支持原生 Windows，请改用默认模型问股，或在支持的系统上运行 HRS 后端。', // 【页面】问股-平台不支持提示
  'chat.analysisStopped': '本次分析已停止，后台任务也已结束。', // 【页面】问股-分析已停止提示
  'chat.analysisTimedOut': '本次分析已超时并结束，请缩小问题范围后重试。', // 【页面】问股-分析已超时提示
  'chat.codexBackendBadge': 'Codex Agent · 实验', // 【页面】问股-Codex Agent 徽标
  'chat.codexChangeBackend': '切换问股方式', // 【页面】问股-切换问股方式按钮
  'chat.codexLimitedMessage': '可读取已保存的分析上下文和回测汇总；实时行情、新闻、市场热点、技术指标重算、个股回测明细和持仓查询请使用默认模型。', // 【页面】问股-Codex 可用范围消息
  'chat.codexLimitedTitle': 'Codex 当前可用范围', // 【页面】问股-Codex 可用范围标题
  'chat.codexUnavailableMessage': '当前设备的 Codex 基础环境暂不满足问股要求，请前往 Agent 设置检查安装和单 Agent 配置。', // 【页面】问股-Codex 不可用消息
  'chat.defaultBackendBadge': '默认模型', // 【页面】问股-默认模型徽标
  'chat.defaultUnavailableMessage': '默认模型问股当前不可用，请前往 Agent 设置检查模型配置。', // 【页面】问股-默认模型不可用消息
  'chat.emptyDescriptionCodex': '输入「分析 600519」或「历史分析整体表现如何」，Codex 将基于已保存的分析上下文和回测汇总回答。', // 【页面】问股-Codex 问股空状态描述
  'chat.emptyDescriptionDefault': '输入「分析 600519」或「茅台现在能买吗」，AI 将调用实时数据工具为您生成决策报告。', // 【页面】问股-默认问股空状态描述
  'chat.introCodex': '使用已保存的分析上下文和回测汇总，向 Codex 询问个股。', // 【页面】问股-Codex 问股引导文案
  'chat.introDefault': '向 AI 询问个股分析，获取基于技能视角的交易建议与实时决策报告。', // 【页面】问股-默认问股引导文案
  'chat.openAgentSettings': '前往 Agent 设置', // 【页面】问股-前往 Agent 设置按钮
  'chat.recheckAgentStatus': '重新检查', // 【页面】问股-重新检查按钮
  'chat.statusCheckingMessage': '这里只检查环境是否允许尝试，不会调用模型或读取股票数据。', // 【页面】问股-正在确认状态消息
  'chat.statusCheckingTitle': '正在确认问股运行环境', // 【页面】问股-正在确认状态标题
  'chat.statusUnavailableMessage': '当前无法确认问股运行环境，因此暂不发送。你可以手动重新检查，问题内容不会丢失。', // 【页面】问股-状态不可用消息
  'chat.statusUnavailableTitle': '暂时无法读取问股运行状态', // 【页面】问股-状态不可用标题
  'chat.stopAnalysis': '停止分析', // 【页面】问股-停止分析按钮
  'chat.stopRequestFailed': '停止请求未送达，分析仍在继续。请再次停止或稍后重试。', // 【页面】问股-停止请求失败提示
  'chat.stoppingAnalysis': '正在停止…', // 【页面】问股-正在停止状态
  // decisionSignals.*
  'decisionSignals.action': '动作', // 【页面】AI建议-信号动作标签
  'decisionSignals.active': '有效', // 【页面】AI建议-有效信号状态
  'decisionSignals.activeOnly': '默认展示 active 信号', // 【页面】AI建议-仅展示有效信号说明
  'decisionSignals.allActions': '全部动作', // 【页面】AI建议-全部动作筛选
  'decisionSignals.allMarkets': '全部市场', // 【页面】AI建议-全部市场筛选
  'decisionSignals.allPhases': '全部阶段', // 【页面】AI建议-全部阶段筛选
  'decisionSignals.allProfiles': '全部风格', // 【页面】AI建议-全部风格筛选
  'decisionSignals.allSources': '全部来源', // 【页面】AI建议-全部来源筛选
  'decisionSignals.allStatuses': '全部状态', // 【页面】AI建议-全部状态筛选
  'decisionSignals.archive': '归档', // 【页面】AI建议-归档按钮
  'decisionSignals.archiveConfirm': '确认将这条信号归档吗？归档后不会再作为当前 active 建议展示。', // 【页面】AI建议-归档确认提示
  'decisionSignals.archived': '已归档', // 【页面】AI建议-已归档状态
  'decisionSignals.catalystSummary': '催化', // 【页面】AI建议-催化因素摘要
  'decisionSignals.close': '关闭信号', // 【页面】AI建议-关闭信号按钮
  'decisionSignals.closeConfirm': '确认关闭这条信号吗？关闭表示你不再跟踪这条建议。', // 【页面】AI建议-关闭信号确认
  'decisionSignals.closed': '已关闭', // 【页面】AI建议-已关闭状态
  'decisionSignals.confidence': '置信度', // 【页面】AI建议-信号置信度
  'decisionSignals.confirmStatusTitle': '更新信号状态', // 【页面】AI建议-状态更新弹窗标题
  'decisionSignals.createdAt': '创建时间', // 【页面】AI建议-信号创建时间
  'decisionSignals.dataQuality': '数据质量', // 【页面】AI建议-数据质量标签
  'decisionSignals.description': '按股票、阶段、来源和状态查询结构化 AI 建议，并保留风险与数据质量上下文。', // 【页面】AI建议-AI 建议页面描述
  'decisionSignals.detailTitle': '信号详情', // 【页面】AI建议-信号详情标题
  'decisionSignals.directionExpected': '预期方向', // 【页面】AI建议-预期方向标签
  'decisionSignals.emptyDescription': '完成一次普通个股分析后，系统会从报告中沉淀可查询的结构化建议。', // 【页面】AI建议-信号空状态描述
  'decisionSignals.emptyTitle': '暂无决策信号', // 【页面】AI建议-信号空状态标题
  'decisionSignals.entryRange': '入场区间', // 【页面】AI建议-入场区间标签
  'decisionSignals.errorTitle': '决策信号加载失败', // 【页面】AI建议-信号加载失败标题
  'decisionSignals.evidence': '证据', // 【页面】AI建议-证据标签
  'decisionSignals.expired': '已过期', // 【页面】AI建议-已过期状态
  'decisionSignals.expiresAt': '过期时间', // 【页面】AI建议-过期时间标签
  'decisionSignals.feedback.not_useful': '无用', // 【页面】AI建议-无用反馈选项
  'decisionSignals.feedback.useful': '有用', // 【页面】AI建议-有用反馈选项
  'decisionSignals.feedbackNone': '暂无反馈', // 【页面】AI建议-无反馈状态
  'decisionSignals.feedbackTitle': '用户反馈', // 【页面】AI建议-用户反馈标题
  'decisionSignals.filter': '筛选', // 【页面】AI建议-筛选按钮
  'decisionSignals.horizon': '周期', // 【页面】AI建议-持仓周期标签
  'decisionSignals.horizon.10d': '10 日', // 【页面】AI建议-10 日周期
  'decisionSignals.horizon.1d': '1 日', // 【页面】AI建议-1 日周期
  'decisionSignals.horizon.3d': '3 日', // 【页面】AI建议-3 日周期
  'decisionSignals.horizon.5d': '5 日', // 【页面】AI建议-5 日周期
  'decisionSignals.horizon.intraday': '盘中', // 【页面】AI建议-盘中周期
  'decisionSignals.horizon.long': '长期', // 【页面】AI建议-长期周期
  'decisionSignals.horizon.swing': '波段', // 【页面】AI建议-波段周期
  'decisionSignals.invalidate': '标记失效', // 【页面】AI建议-标记失效按钮
  'decisionSignals.invalidateConfirm': '确认将这条信号标记为失效吗？失效后不会再作为当前 active 建议展示。', // 【页面】AI建议-标记失效确认
  'decisionSignals.invalidated': '已失效', // 【页面】AI建议-已失效状态
  'decisionSignals.invalidation': '失效条件', // 【页面】AI建议-信号失效条件
  'decisionSignals.latestDescription': '读取当前查看股票的最新 active 信号。', // 【页面】AI建议-查询最新说明
  'decisionSignals.latestTitle': '按股票查询最新信号', // 【页面】AI建议-按股票查询标题
  'decisionSignals.market': '市场', // 【页面】AI建议-市场标签
  'decisionSignals.market.cn': 'A 股', // 【页面】AI建议-A 股市场
  'decisionSignals.market.hk': '港股', // 【页面】AI建议-港股市场
  'decisionSignals.market.jp': '日股', // 【页面】AI建议-日股市场
  'decisionSignals.market.kr': '韩股', // 【页面】AI建议-韩股市场
  'decisionSignals.market.tw': '台股', // 【页面】AI建议-台股市场
  'decisionSignals.market.us': '美股', // 【页面】AI建议-美股市场
  'decisionSignals.marketPhase': '阶段', // 【页面】AI建议-市场阶段标签
  'decisionSignals.marketPhase.closing_auction': '集合竞价', // 【页面】AI建议-集合竞价阶段
  'decisionSignals.marketPhase.intraday': '盘中', // 【页面】AI建议-盘中阶段
  'decisionSignals.marketPhase.lunch_break': '午间休市', // 【页面】AI建议-午间休市阶段
  'decisionSignals.marketPhase.non_trading': '非交易时段', // 【页面】AI建议-非交易时段
  'decisionSignals.marketPhase.postmarket': '盘后', // 【页面】AI建议-盘后阶段
  'decisionSignals.marketPhase.premarket': '盘前', // 【页面】AI建议-盘前阶段
  'decisionSignals.marketPhase.unknown': '未知阶段', // 【页面】AI建议-未知阶段
  'decisionSignals.metadata': '元数据', // 【页面】AI建议-元数据标签
  'decisionSignals.noLatestDescription': '该股票当前没有 active 信号，或信号已过期。', // 【页面】AI建议-无最新信号说明
  'decisionSignals.noLatestTitle': '暂无最新有效信号', // 【页面】AI建议-无最新信号标题
  'decisionSignals.noOutcomes': '暂无后验结果', // 【页面】AI建议-无后验结果提示
  'decisionSignals.noReviewedStatsDescription': '当前已有 AI 建议时，也可能还没有形成可统计的后验复盘结果。', // 【页面】AI建议-无复盘样本说明
  'decisionSignals.noReviewedStatsTitle': '暂无已复盘样本', // 【页面】AI建议-无复盘样本标题
  'decisionSignals.outcome.hit': '命中', // 【页面】AI建议-命中后验结果
  'decisionSignals.outcome.miss': '未命中', // 【页面】AI建议-未命中后验结果
  'decisionSignals.outcome.neutral': '中性', // 【页面】AI建议-中性后验结果
  'decisionSignals.outcome.unable': '无法评估', // 【页面】AI建议-无法评估后验结果
  'decisionSignals.outcomes': '后验结果', // 【页面】AI建议-后验结果标签
  'decisionSignals.pageTitle': 'AI 建议 - HRS', // 【页面】AI建议-AI 建议页文档标题
  'decisionSignals.planQuality': '计划质量', // 【页面】AI建议-计划质量标签
  'decisionSignals.planQuality.complete': '完整', // 【页面】AI建议-完整计划质量
  'decisionSignals.planQuality.minimal': '最小', // 【页面】AI建议-最小计划质量
  'decisionSignals.planQuality.partial': '部分', // 【页面】AI建议-部分计划质量
  'decisionSignals.planQuality.unknown': '未知', // 【页面】AI建议-未知计划质量
  'decisionSignals.portfolioColumn': 'AI 建议', // 【页面】AI建议-持仓 AI 建议列名
  'decisionSignals.portfolioEmpty': '-', // 【页面】AI建议-持仓 AI 建议空值
  'decisionSignals.portfolioLoading': '加载中', // 【页面】AI建议-持仓 AI 建议加载中
  'decisionSignals.portfolioPartialWarning': 'AI 建议只加载了部分数据：{message}', // 【页面】AI建议-持仓 AI 建议部分加载警告
  'decisionSignals.portfolioWarningTitle': 'AI 建议降级', // 【页面】AI建议-持仓 AI 建议降级标题
  'decisionSignals.pricePlan': '价格计划', // 【页面】AI建议-价格计划标签
  'decisionSignals.profile': '风格', // 【页面】AI建议-决策风格标签
  'decisionSignals.profile.aggressive': '进取', // 【页面】AI建议-进取风格
  'decisionSignals.profile.balanced': '均衡', // 【页面】AI建议-均衡风格
  'decisionSignals.profile.conservative': '保守', // 【页面】AI建议-保守风格
  'decisionSignals.profile.unknown': '未知', // 【页面】AI建议-未知风格
  'decisionSignals.profileCalibrationAverageReturn': '标的平均区间涨跌', // 【页面】AI建议-风格校准平均涨跌
  'decisionSignals.profileCalibrationBreakdownLabel': '细分统计方式', // 【页面】AI建议-细分统计标签
  'decisionSignals.profileCalibrationByAction': '按建议动作', // 【页面】AI建议-按动作细分
  'decisionSignals.profileCalibrationByHorizon': '按复盘周期', // 【页面】AI建议-按周期细分
  'decisionSignals.profileCalibrationCompletedShort': '已完成 {count}', // 【页面】AI建议-已完成数量
  'decisionSignals.profileCalibrationDescription': '这些数据来自历史后验复盘，只用于描述，不代表某种风格更优，也不构成投资建议。', // 【页面】AI建议-风格校准说明
  'decisionSignals.profileCalibrationHitRate': '命中率', // 【页面】AI建议-风格校准命中率
  'decisionSignals.profileCalibrationInsufficient': '样本不足，仅供观察。', // 【页面】AI建议-样本不足提示
  'decisionSignals.profileCalibrationMae': '最大不利波动', // 【页面】AI建议-最大不利波动指标
  'decisionSignals.profileCalibrationMaeDescription': '最大不利波动表示复盘期间相对起始价最不利的一次波动，不代表未来风险上限。', // 【页面】AI建议-最大不利波动说明
  'decisionSignals.profileCalibrationMissRate': '未命中率', // 【页面】AI建议-未命中率
  'decisionSignals.profileCalibrationNoBreakdownSamples': '暂无可观察的细分样本。', // 【页面】AI建议-无细分样本提示
  'decisionSignals.profileCalibrationSampleCounts': '已完成 {completed} / 总评估 {total}', // 【页面】AI建议-样本数量统计
  'decisionSignals.profileCalibrationThreshold': '每个分组至少需要 {count} 个已完成样本才展示表现指标。', // 【页面】AI建议-展示阈值说明
  'decisionSignals.profileCalibrationTitle': '决策风格历史表现', // 【页面】AI建议-风格校准标题
  'decisionSignals.profileCalibrationUnableRate': '无法评估率', // 【页面】AI建议-无法评估率
  'decisionSignals.profileCalibrationUnavailable': '暂无可计算结果', // 【页面】AI建议-无可计算结果提示
  'decisionSignals.profileCalibrationUnknownDimension': '未知', // 【页面】AI建议-未知维度
  'decisionSignals.profileCalibrationUnknownNotice': '另有 {count} 条历史样本缺少决策风格标记，未计入三类风格。', // 【页面】AI建议-未知风格样本提示
  'decisionSignals.reason': '理由', // 【页面】AI建议-信号理由标签
  'decisionSignals.reassessBlockedNote': '该预览已被风控约束为非进攻展示动作。', // 【页面】AI建议-重评估被阻断说明
  'decisionSignals.reassessBlockedTitle': '预览被风控阻断', // 【页面】AI建议-重评估阻断标题
  'decisionSignals.reassessPersist': '确认保存', // 【页面】AI建议-确认保存重评估
  'decisionSignals.reassessPersistBlockedTitle': '保存被风控阻断', // 【页面】AI建议-保存被阻断标题
  'decisionSignals.reassessPersistConfirmMessage': '服务端将基于同一份历史报告快照重新计算，并保存通过风控的结果。', // 【页面】AI建议-保存重评估确认文案
  'decisionSignals.reassessPersistConfirmTitle': '保存重评估信号', // 【页面】AI建议-保存重评估确认标题
  'decisionSignals.reassessPersistedCreated': '已保存为新的 DecisionSignal #{id}。', // 【页面】AI建议-重评估新建成功提示
  'decisionSignals.reassessPersistedCreatedTitle': '重评估信号已保存', // 【页面】AI建议-重评估新建成功标题
  'decisionSignals.reassessPersistedExisting': '同一报告、风格和信号身份的 DecisionSignal #{id} 已存在，本次没有重复创建；展示其原始服务端记录。', // 【页面】AI建议-重评估复用现有信号提示
  'decisionSignals.reassessPersistedExistingTitle': '已复用现有信号', // 【页面】AI建议-重评估复用现有信号标题
  'decisionSignals.reassessPersistedRefreshed': '现有 DecisionSignal #{id} 已按存储契约完成过期续期或缺失维度补齐；原始创建来源保持不变，请以后端返回记录为准。', // 【页面】AI建议-重评估刷新信号提示
  'decisionSignals.reassessPersistedRefreshedTitle': '重评估信号已刷新', // 【页面】AI建议-重评估刷新信号标题
  'decisionSignals.reassessPersistedTerminalExisting': 'DecisionSignal #{id} 已处于“{status}”状态，本次没有新建或重新激活信号。', // 【页面】AI建议-重评估终态信号提示
  'decisionSignals.reassessPersistedTerminalTitle': '现有信号保持终态', // 【页面】AI建议-重评估终态信号标题
  'decisionSignals.reassessPersisting': '正在保存', // 【页面】AI建议-重评估保存中状态
  'decisionSignals.reassessPreview': '生成预览', // 【页面】AI建议-生成重评估预览按钮
  'decisionSignals.reassessProfile': '重评估风格', // 【页面】AI建议-重评估风格标签
  'decisionSignals.reassessRawFinal': '原始/最终', // 【页面】AI建议-原始与最终对比标签
  'decisionSignals.reassessSource': '来源报告 #{id}', // 【页面】AI建议-重评估来源报告
  'decisionSignals.reassessTitle': '决策风格重评估预览', // 【页面】AI建议-重评估预览标题
  'decisionSignals.reassessUnsupported': '该信号不支持重评估', // 【页面】AI建议-不支持重评估提示
  'decisionSignals.reassessUnsupportedTitle': '缺少来源报告', // 【页面】AI建议-不支持重评估标题
  'decisionSignals.reassessWarnings': '风控提示', // 【页面】AI建议-风控提示标签
  'decisionSignals.refresh': '刷新', // 【页面】AI建议-刷新按钮
  'decisionSignals.returnPct': '区间收益', // 【页面】AI建议-区间收益率
  'decisionSignals.riskSummary': '风险', // 【页面】AI建议-风险摘要标签
  'decisionSignals.score': '评分', // 【页面】AI建议-信号评分
  'decisionSignals.source': '来源', // 【页面】AI建议-信号来源标签
  'decisionSignals.sourceReport': '来源报告', // 【页面】AI建议-来源报告标签
  'decisionSignals.sourceReportId': '来源报告 ID', // 【页面】AI建议-来源报告 ID
  'decisionSignals.sourceType.agent': 'Agent', // 【页面】AI建议-Agent 来源
  'decisionSignals.sourceType.alert': '告警', // 【页面】AI建议-告警来源
  'decisionSignals.sourceType.analysis': '分析报告', // 【页面】AI建议-分析报告来源
  'decisionSignals.sourceType.manual': '手动', // 【页面】AI建议-手动来源
  'decisionSignals.sourceType.market_review': '大盘复盘', // 【页面】AI建议-大盘复盘来源
  'decisionSignals.statsDescription': '基于当前后验引擎版本统计信号表现，默认排除已归档信号。', // 【页面】AI建议-信号统计说明
  'decisionSignals.statsErrorTitle': '后验统计加载失败', // 【页面】AI建议-统计加载失败标题
  'decisionSignals.statsGlobalScope': '当前统计为全局已复盘 outcome 口径，不等于当前可见信号数量，也不随当前股票过滤。', // 【页面】AI建议-全局统计口径说明
  'decisionSignals.statsHitRate': '命中率', // 【页面】AI建议-命中率统计
  'decisionSignals.statsTitle': '信号表现统计', // 【页面】AI建议-信号统计标题
  'decisionSignals.statsTotal': '评估数', // 【页面】AI建议-评估总数
  'decisionSignals.status': '状态', // 【页面】AI建议-信号状态标签
  'decisionSignals.stockCode': '股票代码', // 【页面】AI建议-股票代码标签
  'decisionSignals.stockContextApply': '查看股票', // 【页面】AI建议-应用股票上下文按钮
  'decisionSignals.stockContextClear': '清空当前股票', // 【页面】AI建议-清空股票上下文按钮
  'decisionSignals.stockContextCurrent': '当前查看：{stock}', // 【页面】AI建议-当前股票上下文
  'decisionSignals.stockContextDescription': '选择一次股票后，最新信号和时间线会共享这个上下文。', // 【页面】AI建议-股票上下文说明
  'decisionSignals.stockContextEmpty': '尚未选择当前股票。', // 【页面】AI建议-未选股票提示
  'decisionSignals.stockContextGuideDescription': '先在页面顶部选择当前股票，再查看最新信号和时间线。', // 【页面】AI建议-股票上下文引导说明
  'decisionSignals.stockContextGuideTitle': '选择股票查看 AI 建议', // 【页面】AI建议-股票上下文引导标题
  'decisionSignals.stockContextNoCandidates': '暂无可用候选，可直接输入股票代码或名称。', // 【页面】AI建议-无候选股票提示
  'decisionSignals.stockContextPopular': '热门候选', // 【页面】AI建议-热门候选股票
  'decisionSignals.stockContextRecent': '最近分析', // 【页面】AI建议-最近分析股票
  'decisionSignals.stockContextTitle': '当前股票', // 【页面】AI建议-当前股票标题
  'decisionSignals.stopLoss': '止损', // 【页面】AI建议-止损价标签
  'decisionSignals.targetPrice': '目标价', // 【页面】AI建议-目标价标签
  'decisionSignals.timelineAlertShape': '菱形点表示 alert', // 【页面】AI建议-时间线告警形状说明
  'decisionSignals.timelineDescription': '按单支股票查看同一建议随时间变化的轨迹。', // 【页面】AI建议-时间线说明
  'decisionSignals.timelineEmptyDescription': '当前时间范围内没有该股票的信号。', // 【页面】AI建议-时间线空状态描述
  'decisionSignals.timelineEmptyTitle': '暂无时间线信号', // 【页面】AI建议-时间线空状态标题
  'decisionSignals.timelineErrorTitle': '时间线加载失败', // 【页面】AI建议-时间线加载失败标题
  'decisionSignals.timelineFamilyBullish': '偏多', // 【页面】AI建议-偏多信号族
  'decisionSignals.timelineFamilyDefensive': '防御', // 【页面】AI建议-防御信号族
  'decisionSignals.timelineFamilyNeutral': '中性', // 【页面】AI建议-中性信号族
  'decisionSignals.timelineGuideDescription': '调整时间范围、状态或市场后，点击查询时间线应用筛选。', // 【页面】AI建议-时间线引导说明
  'decisionSignals.timelineGuideTitle': '查询当前股票时间线', // 【页面】AI建议-时间线引导标题
  'decisionSignals.timelineMarket': '时间线市场', // 【页面】AI建议-时间线市场筛选
  'decisionSignals.timelineProfile': '时间线风格', // 【页面】AI建议-时间线风格筛选
  'decisionSignals.timelineRange': '时间范围', // 【页面】AI建议-时间线范围标签
  'decisionSignals.timelineRange.180d': '180 天', // 【页面】AI建议-180 天时间范围
  'decisionSignals.timelineRange.30d': '30 天', // 【页面】AI建议-30 天时间范围
  'decisionSignals.timelineRange.90d': '90 天', // 【页面】AI建议-90 天时间范围
  'decisionSignals.timelineSearch': '查询时间线', // 【页面】AI建议-查询时间线按钮
  'decisionSignals.timelineSelected': '已选第 {index} 个点', // 【页面】AI建议-时间线选中点提示
  'decisionSignals.timelineStatus': '时间线状态', // 【页面】AI建议-时间线状态筛选
  'decisionSignals.timelineStatus.active': '仅有效', // 【页面】AI建议-仅有效信号筛选
  'decisionSignals.timelineStatus.all': '全部历史', // 【页面】AI建议-全部历史筛选
  'decisionSignals.timelineTitle': '股票信号时间线', // 【页面】AI建议-时间线标题
  'decisionSignals.timelineTruncatedDescription': '仅展示最近 100 条信号，请缩小时间范围。', // 【页面】AI建议-时间线截断说明
  'decisionSignals.timelineTruncatedTitle': '时间线已截断', // 【页面】AI建议-时间线截断标题
  'decisionSignals.title': 'AI 建议', // 【页面】AI建议-AI 建议页面标题
  'decisionSignals.total': '共 {total} 条信号', // 【页面】AI建议-信号总数
  'decisionSignals.unableReason': '无法评估原因', // 【页面】AI建议-无法评估原因标签
  'decisionSignals.viewDetailsFor': '查看 {stock} AI 建议详情', // 【页面】AI建议-查看股票建议详情
  'decisionSignals.watchConditions': '观察条件', // 【页面】AI建议-观察条件标签
  // eodPicker.*
  'eodPicker.start.button': '开始分析', // 【页面】尾盘选股-开始分析按钮
  'eodPicker.start.editFilters': '点击编辑', // 【页面】尾盘选股-点击编辑筛选条件提示
  'eodPicker.start.resetFilters': '默认', // 【页面】尾盘选股-重置为默认筛选
  'eodPicker.filters.circMv': '流通市值', // 【页面】尾盘选股-筛选-流通市值
  'eodPicker.filters.volumeRatio': '量比', // 【页面】尾盘选股-筛选-量比
  'eodPicker.filters.changePct': '当日涨幅', // 【页面】尾盘选股-筛选-当日涨幅
  'eodPicker.filters.turnoverRate': '换手率', // 【页面】尾盘选股-筛选-换手率
  'eodPicker.filters.excludeSt': '过滤ST股票', // 【页面】尾盘选股-筛选-过滤ST开关
  'eodPicker.filters.strength': '分时强度', // 【页面】尾盘选股-筛选-分时强度
  'eodPicker.filters.title': '筛选条件', // 【页面】尾盘选股-筛选条件面板标题
  'eodPicker.filters.done': '完成', // 【页面】尾盘选股-筛选完成按钮
  'eodPicker.filters.on': '开启', // 【页面】尾盘选股-开关-开启
  'eodPicker.filters.off': '关闭', // 【页面】尾盘选股-开关-关闭
  'eodPicker.filters.unlimited': '不限', // 【页面】尾盘选股-筛选-不限
  'eodPicker.filters.cancel': '取消', // 【页面】尾盘选股-筛选取消按钮
  'eodPicker.running.title': '正在选股', // 【页面】尾盘选股-选股进行中标题
  'eodPicker.running.cancel': '取消', // 【页面】尾盘选股-取消选股按钮
  'eodPicker.running.stepBasic': '第一步 · 基础条件过滤', // 【页面】尾盘选股-进度步骤-基础条件过滤标题
  'eodPicker.running.stepStrength': '第二步 · 分时强度过滤', // 【页面】尾盘选股-进度步骤-分时强度过滤标题
  'eodPicker.running.stepPending': '筛选中…', // 【页面】尾盘选股-进度步骤-进行中占位
  'eodPicker.running.stepEmpty': '暂无结果', // 【页面】尾盘选股-进度步骤-无股票提示
  'eodPicker.running.stepCount': '{count} 只', // 【页面】尾盘选股-进度步骤-股票数量
  'eodPicker.result.title': '选股结果', // 【页面】尾盘选股-选股结果标题
  'eodPicker.result.basis': '基准交易日', // 【页面】尾盘选股-基准交易日标签
  'eodPicker.result.reanalyze': '重新分析', // 【页面】尾盘选股-重新分析按钮
  'eodPicker.result.empty': '未选出符合条件的股票，试试重新调整筛选条件', // 【页面】尾盘选股-结果为空提示
  'eodPicker.result.emptyDesc': '可尝试降低强度阈值，或放宽涨跌幅、换手率等条件后重新分析', // 【页面】尾盘选股-结果为空补充说明
  'eodPicker.result.sortBy': '排序', // 【页面】尾盘选股-排序标签
  'eodPicker.result.sort.strength': '分时强度', // 【页面】尾盘选股-按分时强度排序选项
  'eodPicker.EodStockCard.strength': '强度', // 【页面组件】EodStockCard，卡片展示的分时强度指标数值
  'eodPicker.EodStockCard.circMv': '流通市值', // 【页面组件】EodStockCard，卡片指标-流通市值
  'eodPicker.EodStockCard.volumeRatio': '量比', // 【页面组件】EodStockCard，卡片指标-量比
  'eodPicker.EodStockCard.turnoverRate': '换手率', // 【页面组件】EodStockCard，卡片指标-换手率
  'eodPicker.EodStockCard.amount': '成交额', // 【页面组件】EodStockCard，卡片指标-成交额
  'eodPicker.EodStockCard.currentPrice': '现价', // 【页面组件】EodStockCard，卡片指标-现价
  'eodPicker.EodStockCard.priceLegend': '价格', // 【页面组件】EodStockCard，分时价格线图例文字
  'eodPicker.EodStockCard.avgPriceLegend': '均价', // 【页面组件】EodStockCard，分时均价线图例文字
  'eodPicker.EodStockCard.addWatchlist': '加自选', // 【页面组件】EodStockCard，加自选按钮文案
  'eodPicker.EodStockCard.inWatchlist': '已自选', // 【页面组件】EodStockCard，已加入自选的状态文案
  'eodPicker.EodStockCard.openKline': '点击查看个股 K 线', // 【页面组件】EodStockCard，点击卡片跳转 K 线的提示
  'eodPicker.EodStockCard.prevClose': '昨收', // 【页面组件】EodStockCard，卡片指标-昨收
  'eodPicker.error.snapshot': '无法获取行情快照，可能为非交易日或数据源异常。', // 【页面】尾盘选股-行情快照获取失败提示
  'eodPicker.error.failed': '选股任务失败', // 【页面】尾盘选股-选股任务失败提示
  'eodPicker.error.generic': '操作失败，请稍后重试。', // 【页面】尾盘选股-通用操作失败提示
  'eodPicker.error.addWatchlist': '加入自选失败，请稍后重试。', // 【页面】尾盘选股-加入自选失败提示
  // scanner.*
  'scanner.pool.title': '股票池来源', // 【页面】信号扫描-股票池来源卡片标题
  'scanner.pool.watchlist': '自选股', // 【页面】信号扫描-股票池-自选股
  'scanner.pool.ranking': '榜单 TopN', // 【页面】信号扫描-股票池-榜单 TopN
  'scanner.pool.limitUp': '涨停池', // 【页面】信号扫描-股票池-涨停池
  'scanner.pool.watchlistHint': '使用全部自选分组的去重股票池', // 【页面】信号扫描-自选池说明
  'scanner.pool.rankingHint': '榜单来源为全市场 A 股实时行情', // 【页面】信号扫描-榜单池说明
  'scanner.pool.limitUpHint': '来源于涨停池，已按连板数与封板时间排序', // 【页面】信号扫描-涨停池说明
  'scanner.pool.emptyWatchlist': '自选股分组为空，请先添加自选股', // 【页面】信号扫描-自选池为空提示
  'scanner.pool.count': '股票池 {n} 只', // 【页面】信号扫描-股票池数量
  'scanner.rankingField.label': '排序字段', // 【页面】信号扫描-榜单排序字段标签
  'scanner.rankingField.amount': '成交额', // 【页面】信号扫描-榜单排序-成交额
  'scanner.rankingField.changePercent': '涨幅', // 【页面】信号扫描-榜单排序-涨幅
  'scanner.rankingField.turnoverRate': '换手率', // 【页面】信号扫描-榜单排序-换手率
  'scanner.topN': 'Top {n}', // 【页面】信号扫描-TopN 选项
  'scanner.signals.title': '信号模板', // 【页面】信号扫描-信号模板卡片标题
  'scanner.signals.empty': '请至少选择一个信号模板', // 【页面】信号扫描-未选信号提示
  'scanner.signal.ma_golden': 'MA金叉', // 【页面】信号扫描-信号-MA金叉
  'scanner.signal.ma_golden_desc': '短期均线上穿长期均线', // 【页面】信号扫描-信号-MA金叉说明
  'scanner.signal.ma_death': 'MA死叉', // 【页面】信号扫描-信号-MA死叉
  'scanner.signal.ma_death_desc': '短期均线下穿长期均线', // 【页面】信号扫描-信号-MA死叉说明
  'scanner.signal.macd_golden': 'MACD金叉', // 【页面】信号扫描-信号-MACD金叉
  'scanner.signal.macd_golden_desc': 'DIF 上穿 DEA', // 【页面】信号扫描-信号-MACD金叉说明
  'scanner.signal.macd_death': 'MACD死叉', // 【页面】信号扫描-信号-MACD死叉
  'scanner.signal.macd_death_desc': 'DIF 下穿 DEA', // 【页面】信号扫描-信号-MACD死叉说明
  'scanner.signal.rsi_oversold': 'RSI超卖', // 【页面】信号扫描-信号-RSI超卖
  'scanner.signal.rsi_oversold_desc': 'RSI 低于 30', // 【页面】信号扫描-信号-RSI超卖说明
  'scanner.signal.rsi_overbought': 'RSI超买', // 【页面】信号扫描-信号-RSI超买
  'scanner.signal.rsi_overbought_desc': 'RSI 高于 70', // 【页面】信号扫描-信号-RSI超买说明
  'scanner.signal.boll_upper': 'BOLL上轨', // 【页面】信号扫描-信号-BOLL突破上轨
  'scanner.signal.boll_upper_desc': '收盘价突破上轨', // 【页面】信号扫描-信号-BOLL突破上轨说明
  'scanner.signal.boll_lower': 'BOLL下轨', // 【页面】信号扫描-信号-BOLL跌破下轨
  'scanner.signal.boll_lower_desc': '收盘价跌破下轨', // 【页面】信号扫描-信号-BOLL跌破下轨说明
  'scanner.start': '开始扫描', // 【页面】信号扫描-开始扫描按钮
  'scanner.cancel': '取消扫描', // 【页面】信号扫描-取消扫描按钮
  'scanner.restart': '重新扫描', // 【页面】信号扫描-重新扫描按钮
  'scanner.progress.preparing': '准备中', // 【页面】信号扫描-进度未就绪占位
  'scanner.running.stepPool': '第一步·解析股票池', // 【页面】信号扫描-分步·解析股票池标题
  'scanner.running.stepSignal': '第二步·技术信号扫描', // 【页面】信号扫描-分步·技术信号扫描标题
  'scanner.running.stepPending': '扫描中…', // 【页面】信号扫描-分步·进行中占位
  'scanner.running.stepEmpty': '暂无结果', // 【页面】信号扫描-分步·无结果占位
  'scanner.running.stepCount': '{count} 只', // 【页面】信号扫描-分步·命中数量
  'scanner.cancelled': '已取消扫描', // 【页面】信号扫描-取消完成提示
  'scanner.result.title': '扫描结果', // 【页面】信号扫描-扫描结果标题
  'scanner.result.count': '{n} 个触发', // 【页面】信号扫描-结果计数
  'scanner.result.empty': '暂无扫描结果', // 【页面】信号扫描-结果为空提示
  'scanner.result.emptyDesc': '选择股票池和信号模板后开始扫描', // 【页面】信号扫描-结果为空补充说明
  'scanner.result.openKline': '点击查看个股 K 线', // 【页面】信号扫描-点击结果跳 K 线的提示
  'scanner.result.addWatchlist': '加自选', // 【页面】信号扫描-加自选按钮文案
  'scanner.result.inWatchlist': '已自选', // 【页面】信号扫描-已加入自选的状态文案
  'scanner.error.start': '提交扫描任务失败，请稍后重试。', // 【页面】信号扫描-提交任务失败提示
  'scanner.error.cancel': '取消扫描失败，请稍后重试。', // 【页面】信号扫描-取消失败提示
  'scanner.error.failed': '扫描任务失败', // 【页面】信号扫描-扫描任务失败提示
  'scanner.error.generic': '操作失败，请稍后重试。', // 【页面】信号扫描-通用操作失败提示
  'scanner.error.addWatchlist': '加入自选失败，请稍后重试。', // 【页面】信号扫描-加入自选失败提示
  // history.*
  'history.actionAdd': '加仓', // 【页面】分析历史-加仓动作
  'history.actionAlert': '预警', // 【页面】分析历史-预警动作
  'history.actionAvoid': '回避', // 【页面】分析历史-回避动作
  'history.actionBuy': '买入', // 【页面】分析历史-买入动作
  'history.actionHold': '持有', // 【页面】分析历史-持有动作
  'history.actionReduce': '减仓', // 【页面】分析历史-减仓动作
  'history.actionSell': '卖出', // 【页面】分析历史-卖出动作
  'history.actionWatch': '观望', // 【页面】分析历史-观望动作
  'history.analysisCount': '{count}次', // 【页面】分析历史-分析次数统计
  'history.bottomReached': '已到底部', // 【页面】分析历史-历史列表到底提示
  'history.defaultEmptyDescription': '完成首次分析后，这里会保留最近结果。', // 【页面】分析历史-历史空状态描述
  'history.defaultEmptyTitle': '暂无历史分析记录', // 【页面】分析历史-历史空状态标题
  'history.defaultTitle': '历史分析', // 【页面】分析历史-历史分析标题
  'history.deleteRecord': '删除 {name} 历史记录', // 【页面】分析历史-删除历史记录按钮
  'history.itemAria': '{name} {code} 历史记录', // 【页面】分析历史-历史记录项无障碍标签
  'history.loading': '加载历史记录中...', // 【页面】分析历史-历史加载中状态
  'history.selectAllHistoryAria': '全选当前已加载历史记录', // 【页面】分析历史-全选历史无障碍标签
  'history.selectAllStockAria': '全选当前个股', // 【页面】分析历史-全选个股无障碍标签
  'history.sentiment': '情绪', // 【页面】分析历史-情绪标签
  // kline.*
  'kline.error': 'K 线数据加载失败', // 【页面】个股K线-K 线加载失败提示
  'kline.empty': '暂无 K 线数据', // 【页面】个股K线-空态
  'kline.fullData': '全量数据', // 【页面】个股K线-全量数据选项
  'kline.info.amount': '成交额', // 【页面】个股K线-成交额
  'kline.info.amplitude': '振幅', // 【页面】个股K线-振幅
  'kline.info.high': '最高', // 【页面】个股K线-最高价
  'kline.info.low': '最低', // 【页面】个股K线-最低价
  'kline.info.open': '今开', // 【页面】个股K线-今日开盘价
  'kline.info.peRatioTTM': '市盈率(TTM)', // 【页面】个股K线-市盈率TTM
  'kline.info.prevClose': '昨收', // 【页面】个股K线-昨日收盘价
  'kline.info.totalMarketCap': '总市值', // 【页面】个股K线-总市值
  'kline.info.turnoverRate': '换手率', // 【页面】个股K线-换手率
  'kline.info.volume': '成交量', // 【页面】个股K线-成交量
  'kline.noStockSelected': '请搜索并选择一只股票查看 K 线', // 【页面】个股K线-未选择股票提示
  'kline.period.120m': '120 分', // 【页面】个股K线-120 分钟周期
  'kline.period.15m': '15 分', // 【页面】个股K线-15 分钟周期
  'kline.period.1m': '分时', // 【页面】个股K线-分时周期
  'kline.period.30m': '30 分', // 【页面】个股K线-30 分钟周期
  'kline.period.5d': '5日', // 【页面】个股K线-5日周期
  'kline.period.5m': '5 分', // 【页面】个股K线-5 分钟周期
  'kline.period.60m': '60 分', // 【页面】个股K线-60 分钟周期
  'kline.period.daily': '日K', // 【页面】个股K线-日K周期
  'kline.period.monthly': '月 K', // 【页面】个股K线-月 K 周期
  'kline.period.weekly': '周 K', // 【页面】个股K线-周 K 周期
  'kline.period.yearly': '年 K', // 【页面】个股K线-年 K 周期
  'kline.tooltip.amount': '成交额', // 【页面】个股K线-tooltip 成交额
  'kline.tooltip.change': '涨跌幅', // 【页面】个股K线-tooltip 涨跌幅
  'kline.tooltip.close': '收盘', // 【页面】个股K线-tooltip 收盘价
  'kline.tooltip.date': '日期', // 【页面】个股K线-tooltip 日期
  'kline.tooltip.dea': 'DEA', // 【页面】个股K线-tooltip DEA 指标
  'kline.tooltip.dif': 'DIF', // 【页面】个股K线-tooltip DIF 指标
  'kline.tooltip.high': '最高', // 【页面】个股K线-tooltip 最高价
  'kline.tooltip.low': '最低', // 【页面】个股K线-tooltip 最低价
  'kline.tooltip.ma10': 'MA10', // 【页面】个股K线-tooltip MA10 均线
  'kline.tooltip.ma30': 'MA30', // 【页面】个股K线-tooltip MA30 均线
  'kline.tooltip.ma5': 'MA5', // 【页面】个股K线-tooltip MA5 均线
  'kline.tooltip.ma60': 'MA60', // 【页面】个股K线-tooltip MA60 均线
  'kline.tooltip.macd': 'MACD', // 【页面】个股K线-tooltip MACD 指标
  'kline.tooltip.open': '开盘', // 【页面】个股K线-tooltip 开盘价
  'kline.tooltip.volume': '成交量', // 【页面】个股K线-tooltip 成交量
  // liveCalendar.*
  'liveCalendar.degradedTip.title': '数据源暂不可用', // 【页面】财经日历-降级提示条
  'liveCalendar.degradedTip.message': '当前展示本地缓存数据，请检查数据源的查询情况', // 【页面】财经日历-降级提示条
  'liveCalendar.loading': '正在加载日历…', // 【页面】财经日历-加载中文案
  'liveCalendar.refresh': '刷新日历', // 【页面】财经日历-手动刷新按钮
  'liveCalendar.refreshing': '刷新中', // 【页面】财经日历-刷新按钮加载态文案
  'liveCalendar.subtitle': '宏观、财报、新股、活动等重要事件的财经日历', // 【页面】财经日历-页面副标题
  'liveCalendar.tabs.activity': '活动', // 【页面】财经日历-分类 Tab：活动
  'liveCalendar.tabs.all': '全部', // 【页面】财经日历-分类 Tab：全部
  'liveCalendar.tabs.earnings': '财报', // 【页面】财经日历-分类 Tab：财报
  'liveCalendar.tabs.ipo': '新股', // 【页面】财经日历-分类 Tab：新股
  'liveCalendar.tabs.macro': '宏观', // 【页面】财经日历-分类 Tab：宏观
  'liveCalendar.title': '消息日历', // 【页面】财经日历-页面标题
  // liveNews.*
  'liveNews.channelTabs': '快讯频道', // 【页面】实时财经-频道 Tab 的无障碍标签
  'liveNews.dateAll': '全部日期', // 【页面】实时财经-日期筛选：不限
  'liveNews.dateToday': '今天', // 【页面】实时财经-日期筛选：今天
  'liveNews.dateYesterday': '昨天', // 【页面】实时财经-日期筛选：昨天
  'liveNews.degradedTip': '实时源暂不可用，当前为聚合降级数据（无频道分类与重要级）', // 【页面】实时财经-降级提示
  'liveNews.empty': '暂无快讯', // 【页面】实时财经-空态：当前频道无数据
  'liveNews.emptyDate': '该日期暂无快讯', // 【页面】实时财经-空态：指定日期无数据
  'liveNews.emptyImportant': '本频道暂无重要快讯', // 【页面】实时财经-空态：重要级筛选无结果（如科技频道实测无重要快讯）
  'liveNews.emptyKeyword': '未找到相关快讯', // 【页面】实时财经-空态：关键词搜索无结果
  'liveNews.expand': '展开', // 【页面】实时财经-快讯正文超 3 行时的展开按钮
  'liveNews.collapse': '收起', // 【页面】实时财经-快讯正文展开后的收起按钮
  'liveNews.importantOnly': '只看重要的', // 【页面】实时财经-重要级筛选开关
  'liveNews.importantTag': '重要', // 【页面】实时财经-重要快讯标签
  'liveNews.normalTag': '一般', // 【页面】实时财经-普通快讯标签
  'liveNews.loadMore': '加载更多', // 【页面】实时财经-加载更多按钮
  'liveNews.loading': '正在获取最新快讯…', // 【页面】实时财经-加载中文案
  'liveNews.refresh': '刷新资讯', // 【页面】实时财经-手动刷新按钮
  'liveNews.refreshing': '刷新资讯中', // 【页面】实时财经-刷新按钮加载态文案（HrsButton loadingText）
  'liveNews.searchPlaceholder': '搜索快讯…', // 【页面】实时财经-搜索框占位符
  'liveNews.subtitle': '7x24 小时财经快讯，覆盖要闻、A股、美股、港股、外汇、商品、债券与科技', // 【页面】实时财经-页面副标题
  'liveNews.title': '快讯中心', // 【页面】实时财经-快讯中心页面标题
  // notFound.*
  'notFound.backHome': '返回首页', // 【页面】404-404 返回首页
  'notFound.relogin': '重新登录', // 【页面】404-404 重新登录
  'notFound.description': '抱歉，您访问的页面不存在或已被移动', // 【页面】404-404 描述
  'notFound.documentTitle': '页面未找到 - HermesX', // 【页面】404-404 文档标题（document.title）
  'notFound.title': '页面未找到', // 【页面】404-404 标题
  // report.*
  'report.addToWatchlist': '加入自选', // 【页面】报告-报告加入自选按钮
  'report.removeFromWatchlist': '从自选删除', // 【页面】报告-报告移除自选按钮
  'report.watchlist': '自选', // 【页面】报告-报告自选标签
  // review.*
  'review.analyze': '分析', // 【页面】复盘-分析按钮
  'review.analyzing': '分析中', // 【页面】复盘-分析中状态
  'review.askAi': '追问 AI', // 【页面】复盘-追问 AI 按钮
  'review.defaultStrategyDescription': '沿用系统默认分析框架', // 【页面】复盘-默认策略描述
  'review.defaultStrategyName': '默认策略', // 【页面】复盘-默认策略名称
  'review.duplicateTask': '任务已存在', // 【页面】复盘-重复任务提示
  'review.fullReport': '完整分析报告', // 【页面】复盘-完整报告入口
  'review.goSettings': '去配置', // 【页面】复盘-跳转设置按钮
  'review.historyButton': '历史记录', // 【页面】复盘-历史记录按钮
  'review.historyTrend': '历史趋势', // 【页面】复盘-历史趋势入口
  'review.inputInvalid': '输入有误', // 【页面】复盘-输入无效提示
  'review.loadingReport': '加载报告中...', // 【页面】复盘-报告加载中状态
  'review.marketRegionAll': '全部市场', // 【页面】复盘-全部市场选项
  'review.marketRegionCn': 'A 股', // 【页面】复盘-A 股市场
  'review.marketRegionDefaultUnavailable': '由服务器在提交时决定', // 【页面】复盘-市场默认值不可用说明
  'review.marketRegionDescription': '选择本次复盘覆盖的市场，可单选或多选。', // 【页面】复盘-市场选择说明
  'review.marketRegionHk': '港股', // 【页面】复盘-港股市场
  'review.marketRegionJp': '日股', // 【页面】复盘-日股市场
  'review.marketRegionKr': '韩股', // 【页面】复盘-韩股市场
  'review.marketRegionOneTimeHint': '仅影响本次触发，不会修改全局配置。', // 【页面】复盘-市场选择一次性提示
  'review.marketRegionSelector': '选择大盘复盘市场', // 【页面】复盘-市场选择器标题
  'review.marketRegionServerDefault': '服务器默认', // 【页面】复盘-服务器默认市场
  'review.title': '大盘复盘', // 【页面】复盘-大盘复盘页标题
  'review.subtitle': '集成股票分析、大盘回顾与任务面板，基于收盘数据、行业数据、舆情数据自动定时形成分析复盘报告推送', // 【页面】复盘-首页副标题
  'review.marketRegionTitle': '本次复盘市场', // 【页面】复盘-本次复盘市场标题
  'review.marketRegionUs': '美股', // 【页面】复盘-美股市场
  'review.marketReview': '大盘复盘', // 【页面】复盘-大盘复盘入口
  'review.marketReviewCompleted': '大盘复盘已完成', // 【页面】复盘-大盘复盘完成提示
  'review.marketReviewCompletedWithReport': '大盘复盘任务已完成，结果如下：', // 【页面】复盘-大盘复盘完成含结果
  'review.marketReviewCompletedWithoutReport': '大盘复盘任务已完成，结果已生成并按配置推送。', // 【页面】复盘-大盘复盘完成无结果展示
  'review.marketReviewFailed': '大盘复盘执行失败。', // 【页面】复盘-大盘复盘失败提示
  'review.marketReviewInProgress': '大盘复盘进行中', // 【页面】复盘-大盘复盘进行中状态
  'review.marketReviewSubmitted': '大盘复盘已提交', // 【页面】复盘-大盘复盘已提交提示
  'review.marketReviewSubmittedWithRegion': '{message}；实际市场：{region}', // 【页面】复盘-大盘复盘提交含市场
  'review.marketReviewTimeout': '大盘复盘已超时', // 【页面】复盘-大盘复盘超时提示
  'review.marketReviewTimeoutMessage': '任务长时间未返回最终结果，请在任务列表/历史中查看。', // 【页面】复盘-大盘复盘超时说明
  'review.marketReviewUnknownStatus': '大盘复盘状态异常', // 【页面】复盘-大盘复盘状态异常提示
  'review.notify': '推送通知', // 【页面】复盘-推送通知选项
  'review.pageTitle': '每日选股分析 - HRS', // 【页面】复盘-首页文档标题
  'review.progressActive': '进行中', // 【页面】复盘-任务进行中状态
  'review.reanalyze': '重新分析', // 【页面】复盘-重新分析按钮
  'review.rerunMarketReview': '重新复盘', // 【页面】复盘-重新复盘按钮
  'review.setupIncomplete': '基础配置未完成', // 【页面】复盘-配置未完成提示
  'review.setupMissingGeneric': '还缺少基础配置，完成后即可开始最小可用分析。', // 【页面】复盘-缺少配置通用提示
  'review.setupMissingWithLabels': '还缺少 {labels}，完成后即可开始最小可用分析。', // 【页面】复盘-缺少配置含标签提示
  'review.startAnalysisDescription': '输入股票代码进行分析，或从左侧选择历史报告查看。', // 【页面】复盘-开始分析描述
  'review.startAnalysisTitle': '开始分析', // 【页面】复盘-开始分析标题
  'review.strategy': '策略', // 【页面】复盘-策略标签
  'review.submitMarketReview': '提交中', // 【页面】复盘-大盘复盘提交中状态
  'review.taskStatus': '任务状态：{status}（{progress}）', // 【页面】复盘-任务状态文案
  'review.taskStatusWithRegion': '任务状态：{status}（{progress}）；实际市场：{region}', // 【页面】复盘-任务状态含市场
  'review.unknownTaskStatus': '收到未知任务状态：{status}', // 【页面】复盘-未知任务状态提示
  // sector.*
  'sector.tab.board': '板块', // 【页面】板块-板块分析一级 TAB：板块
  'sector.tab.boardConcept': '概念板块', // 【页面】板块-「板块」二级 TAB：概念板块
  'sector.tab.boardIndustry': '行业板块', // 【页面】板块-「板块」二级 TAB：行业板块
  'sector.tab.cloudConcept': '概念云图', // 【页面】板块-「云图」二级 TAB：概念云图
  'sector.tab.cloudEtf': 'ETF 云图', // 【页面】板块-「云图」二级 TAB：ETF 云图
  'sector.tab.cloudMap': '云图', // 【页面】板块-板块分析一级 TAB：云图
  'sector.tab.cloudSector': '板块云图', // 【页面】板块-「云图」二级 TAB：板块云图
  'sector.tab.cloudStock': '个股云图', // 【页面】板块-「云图」二级 TAB：个股云图
  'sector.tab.fund': '资金', // 【页面】板块-板块分析一级 TAB：资金
  // settings.*
  'settings.actionSuccess': '操作成功', // 【页面】设置-设置操作成功提示
  'settings.activePanelDescription': '使用统一字段卡片维护当前分类的系统配置。', // 【页面】设置-当前分类配置说明
  'settings.activePanelTitle': '当前分类配置项', // 【页面】设置-当前分类配置标题
  'settings.agentBackendCanTry': '可以尝试', // 【页面】设置-可以尝试状态
  'settings.agentBackendCanTryDescription': '基础环境检查已通过。你可以回到问股页直接提问，首次问题会进行真实执行。', // 【页面】设置-可以尝试说明
  'settings.agentBackendCodexLabel': 'Codex Agent', // 【页面】设置-Codex Agent 标签
  'settings.agentBackendCodexNotice': 'Codex 目前只能读取已保存的分析上下文和回测汇总。实时行情、新闻、市场热点、技术指标重算、个股回测明细和持仓工具暂不开放；需要这些能力时，请选择“默认模型”。点击停止后，本次 Codex 和工具任务会一起结束。此选择只影响问股 Chat；Multi Agent、Deep Research、普通报告和定时任务保持原路径。Codex 不是离线模型，问题和工具结果可能由 Codex 配置的服务处理。', // 【页面】设置-Codex 本地 Agent 说明
  'settings.agentBackendCodexNoticeTitle': 'Codex 本地 Agent（实验）', // 【页面】设置-Codex 本地 Agent 标题
  'settings.agentBackendCommandNotFound': '运行 HRS 的设备找不到 Codex。请在该设备安装 Codex，并确保 HRS 后端进程可以从 PATH 找到它。', // 【页面】设置-Codex 未找到提示
  'settings.agentBackendDefaultLabel': '默认模型', // 【页面】设置-默认模型标签
  'settings.agentBackendEnableMode': '启用 Agent 模式', // 【页面】设置-启用 Agent 模式按钮
  'settings.agentBackendErrorCode': '错误代码', // 【页面】设置-错误代码标签
  'settings.agentBackendExperimental': '实验功能', // 【页面】设置-实验功能标签
  'settings.agentBackendInvalidTimeout': 'Codex 必须设置大于 0 的 Agent 整体时限，确保成功、失败、超时或停止都能明确结束。', // 【页面】设置-超时设置无效提示
  'settings.agentBackendModeDisabled': 'Agent 模式当前未启用。点击下方按钮修改页面草稿，然后保存设置后再使用问股。', // 【页面】设置-Agent 模式未启用提示
  'settings.agentBackendModeDisabledTitle': '需要启用 Agent 模式', // 【页面】设置-需启用 Agent 模式标题
  'settings.agentBackendNeedsAction': '需要处理', // 【页面】设置-需要处理状态
  'settings.agentBackendPlatformUnsupported': 'Codex 本地 Agent 当前不支持原生 Windows。可在 macOS、Linux，或让 HRS 后端完整运行于 WSL 后使用。', // 【页面】设置-平台不支持提示
  'settings.agentBackendRefresh': '刷新状态', // 【页面】设置-刷新状态按钮
  'settings.agentBackendRefreshing': '正在检查', // 【页面】设置-正在检查状态
  'settings.agentBackendSectionDescription': '在同一个问股页面中选择默认模型配置或本机 Codex，并在保存前预览当前草稿是否可运行。', // 【页面】设置-问股生成方式说明
  'settings.agentBackendSectionTitle': '问股生成方式', // 【页面】设置-问股生成方式标题
  'settings.agentBackendSingleOnly': 'Codex 本地 Agent 当前只支持单 Agent 问股。此操作只修改页面草稿，仍需点击保存。', // 【页面】设置-仅支持单 Agent 提示
  'settings.agentBackendSingleOnlyTitle': '需要切换为单 Agent', // 【页面】设置-需切换单 Agent 标题
  'settings.agentBackendStatus': '问股运行状态', // 【页面】设置-问股运行状态标题
  'settings.agentBackendStatusDescription': '这里只检查当前设置、本机 Codex 命令和问股所需协议是否允许尝试启动；不会登录、调用模型或读取股票数据。真正是否能完成问股，会在你发送问题时确认。', // 【页面】设置-问股运行状态说明
  'settings.agentBackendTechnicalDetails': '技术详情', // 【页面】设置-技术详情标签
  'settings.agentBackendUnavailableDescription': '当前问股方式暂不可用，请检查设置后重试。', // 【页面】设置-不可用说明
  'settings.agentBackendUseSingle': '切换为单 Agent', // 【页面】设置-切换为单 Agent 按钮
  'settings.agentBackendVersion': '版本', // 【页面】设置-版本标签
  'settings.agentSettings': 'Agent 设置', // 【页面】设置-Agent 设置入口
  'settings.alphaSift': 'AlphaSift 选股', // 【页面】设置-AlphaSift 选股标题
  'settings.alphaSiftDescription': '启用内置 AlphaSift 实验性质选股能力。', // 【页面】设置-AlphaSift 选股说明
  'settings.alphaSiftDisabled': '选股未开启', // 【页面】设置-选股未开启状态
  'settings.alphaSiftEnabled': '选股已开启', // 【页面】设置-选股已开启状态
  'settings.alphaSiftRisk': '实验功能与风险提示：选股结果仅用于研究和辅助判断，不构成投资建议；市场有风险，交易决策和损益由使用者自行承担。', // 【页面】设置-AlphaSift 风险提示
  'settings.alphaSiftSummary': '开启后左侧导航会显示“选股”；策略和候选生成来自 AlphaSift，HRS 会补充行情、基本面和新闻上下文。', // 【页面】设置-AlphaSift 概要说明
  'settings.authCurrentPassword': '当前管理员密码', // 【页面】设置-当前管理员密码标签
  'settings.authDescription': '管理管理员密码认证，保护您的系统配置安全。', // 【页面】设置-认证设置说明
  'settings.authDisabled': '未启用', // 【页面】设置-认证未启用状态
  'settings.authEnabled': '已启用', // 【页面】设置-认证已启用状态
  'settings.authFailure': '认证设置失败', // 【页面】设置-认证设置失败提示
  'settings.authHelperDefault': '管理员认证可保护 Web 设置页及 API 接口，防止未经授权的访问。', // 【页面】设置-认证默认帮助说明
  'settings.authHelperEnabled': '管理员认证已启用。如需更新密码，请使用下方的“修改密码”功能。', // 【页面】设置-认证已启用帮助说明
  'settings.authHelperNoPassword': '系统尚未设置密码。启用认证前请先设置初始管理员密码，设置后请妥善保管。', // 【页面】设置-无密码帮助说明
  'settings.authHelperPasswordRetained': '系统已保留之前设置的管理员密码。输入当前密码即可快速重新启用认证。', // 【页面】设置-密码已保留帮助说明
  'settings.authHelperTurnOff': '若当前登录会话仍有效，可直接关闭认证；若会话已失效，请输入当前管理员密码。', // 【页面】设置-关闭认证帮助说明
  'settings.authPasswordHintOff': '关闭认证前可能需要验证身份', // 【页面】设置-关闭认证提示
  'settings.authPasswordHintRetained': '输入旧密码以重新激活认证', // 【页面】设置-重新激活认证提示
  'settings.authPasswordPlaceholder': '请输入当前密码', // 【页面】设置-认证密码占位符
  'settings.authRequiredPassword': '设置新密码是必填项', // 【页面】设置-新密码必填提示
  'settings.authSetPassword': '设置管理员密码', // 【页面】设置-设置管理员密码按钮
  'settings.authSetPasswordPlaceholder': '输入新密码 (至少 6 位)', // 【页面】设置-新密码占位符
  'settings.authStatus': '管理员认证', // 【页面】设置-管理员认证状态
  'settings.authSuccessDisabled': '认证已关闭', // 【页面】设置-认证关闭成功提示
  'settings.authSuccessUpdated': '认证设置已更新', // 【页面】设置-认证更新成功提示
  'settings.authTitle': '认证与登录保护', // 【页面】设置-认证设置标题
  'settings.categoryNavDescription': '按模块整理系统设置与认证能力。', // 【页面】设置-分类导航说明
  'settings.categoryNavTitle': '配置分类', // 【页面】设置-配置分类标题
  'settings.dataSourceSectionTitle': '统一数据源配置', // 【页面】设置-数据源摘要卡片标题
  'settings.dataSourceSectionDescription': '集中查看 StockDB 本地源状态，以及 K 线、基础信息、代码搜索三类统一能力的主源与回退策略。', // 【页面】设置-数据源摘要卡片说明
  'settings.dataSourceStatusLabel': '本地源状态', // 【页面】设置-本地源状态标签
  'settings.dataSourceBaseUrlLabel': '服务地址', // 【页面】设置-本地源地址标签
  'settings.dataSourcePrimarySourcesLabel': '主源策略', // 【页面】设置-主源策略标签
  'settings.dataSourceFallbackLabel': '自动回退', // 【页面】设置-自动回退标签
  'settings.dataSourceKlineLabel': 'K 线', // 【页面】设置-K 线能力标签
  'settings.dataSourceStockInfoLabel': '基础信息', // 【页面】设置-基础信息能力标签
  'settings.dataSourceCodeSearchLabel': '代码搜索', // 【页面】设置-代码搜索能力标签
  'settings.dataSourceOpenStockData': '打开本地行情页', // 【页面】设置-打开本地行情页按钮
  'settings.changePasswordConfirm': '确认新密码', // 【页面】设置-确认新密码标签
  'settings.changePasswordConfirmPlaceholder': '再次输入新密码', // 【页面】设置-确认新密码占位符
  'settings.changePasswordCurrent': '当前密码', // 【页面】设置-当前密码标签
  'settings.changePasswordCurrentPlaceholder': '输入当前密码', // 【页面】设置-当前密码占位符
  'settings.changePasswordDescription': '更新当前管理员登录密码。修改成功后，后续登录请使用新密码。', // 【页面】设置-修改密码说明
  'settings.changePasswordFailure': '修改失败', // 【页面】设置-修改密码失败提示
  'settings.changePasswordNew': '新密码', // 【页面】设置-新密码标签
  'settings.changePasswordNewHint': '至少 6 位。', // 【页面】设置-新密码要求提示
  'settings.changePasswordNewPlaceholder': '输入新密码', // 【页面】设置-新密码占位符
  'settings.changePasswordRequiredCurrent': '请输入当前密码', // 【页面】设置-当前密码必填提示
  'settings.changePasswordRequiredNew': '请输入新密码', // 【页面】设置-新密码必填提示
  'settings.changePasswordSave': '保存新密码', // 【页面】设置-保存新密码按钮
  'settings.changePasswordShort': '新密码至少 6 位', // 【页面】设置-密码过短提示
  'settings.changePasswordSuccess': '修改成功', // 【页面】设置-修改密码成功提示
  'settings.changePasswordSuccessMessage': '管理员密码已更新。', // 【页面】设置-修改密码成功消息
  'settings.changePasswordTitle': '修改密码', // 【页面】设置-修改密码标题
  'settings.checkDesktopUpdate': '检查更新', // 【页面】设置-检查桌面端更新按钮
  'settings.checkingDesktopUpdate': '检查中...', // 【页面】设置-检查更新中状态
  'settings.configBackup': '配置备份', // 【页面】设置-配置备份标题
  'settings.configBackupDescription': '导出当前已保存的 .env 备份，或从备份文件恢复配置。导入会覆盖备份中出现的键并立即重载。', // 【页面】设置-配置备份说明
  'settings.currentCategoryEmptyDescription': '当前分类没有可编辑字段；可切换左侧分类继续查看其它系统配置。', // 【页面】设置-当前分类空状态描述
  'settings.currentCategoryEmptyTitle': '当前分类下暂无配置项', // 【页面】设置-当前分类空状态标题
  'settings.desktopCheckError': '检查更新失败', // 【页面】设置-桌面端检查更新失败
  'settings.desktopChecking': '正在检查更新', // 【页面】设置-桌面端检查更新中
  'settings.desktopCurrentNoStatus': '当前尚无更新状态，应用启动后会在后台自动检查。', // 【页面】设置-桌面端无更新状态
  'settings.desktopDownload': '前往下载', // 【页面】设置-前往下载按钮
  'settings.desktopDownloaded': '更新已下载', // 【页面】设置-更新已下载状态
  'settings.desktopDownloading': '正在下载更新', // 【页面】设置-更新下载中状态
  'settings.desktopInstall': '重启安装', // 【页面】设置-重启安装按钮
  'settings.desktopInstalling': '正在安装更新', // 【页面】设置-安装更新中状态
  'settings.desktopLatest': '最新版本', // 【页面】设置-最新版本标签
  'settings.desktopManualUnsupported': '当前桌面端不支持自动安装更新，请前往发布页手动更新。', // 【页面】设置-不支持自动更新提示
  'settings.desktopUpToDate': '已是最新版本', // 【页面】设置-已是最新版本状态
  'settings.desktopUpToDateMessage': '当前桌面端已是最新版本。', // 【页面】设置-已是最新版本消息
  'settings.desktopUpdate': '桌面端更新', // 【页面】设置-桌面端更新标题
  'settings.desktopUpdateAvailable': '发现新版本', // 【页面】设置-发现新版本提示
  'settings.desktopUpdateCheckingMessage': '正在检查 GitHub Releases 中是否有可用新版本。', // 【页面】设置-检查更新中消息
  'settings.desktopUpdateDescription': '启动后会自动检查 GitHub Releases 最新正式版；Windows 安装版会后台下载更新，确认后静默重启安装。', // 【页面】设置-桌面端更新说明
  'settings.desktopUpdateDownloadedMessage': '新版本已下载，可重启应用完成安装。', // 【页面】设置-更新已下载消息
  'settings.desktopUpdateDownloadingMessage': '正在后台下载桌面端更新{percent}。', // 【页面】设置-更新下载中消息
  'settings.desktopUpdateErrorMessage': '无法完成更新检查，请稍后重试。', // 【页面】设置-更新检查错误消息
  'settings.desktopUpdateInstallingMessage': '正在重启并安装更新。', // 【页面】设置-安装更新消息
  'settings.desktopUpdateMessage': '当前 {current}，最新 {latest}。{message}', // 【页面】设置-更新状态消息
  'settings.desktopUpdateReleaseMessage': '可前往 GitHub Releases 下载更新。', // 【页面】设置-发布页下载消息
  'settings.diagnosticHintWeb': '请查看浏览器开发者工具控制台与后端日志，并补充 release 版本、浏览器版本和触发入口。', // 【页面】设置-Web 端诊断提示
  'settings.disableAlphaSift': '关闭选股', // 【页面】设置-关闭选股按钮
  'settings.disableAuth': '关闭认证', // 【页面】设置-关闭认证按钮
  'settings.disabledAlphaSiftSuccess': '已关闭 AlphaSift 选股。', // 【页面】设置-关闭选股成功提示
  'settings.disabledAuthBackupWarning': '当前 Web 端未开启管理员鉴权，导出/导入 `.env` 备份功能已停用；请先将 `ADMIN_AUTH_ENABLED` 设为 `true` 并完成管理员登录后再使用。', // 【页面】设置-未启用认证时备份警告
  'settings.disablingAlphaSift': '关闭中...', // 【页面】设置-关闭选中状态
  'settings.enableAlphaSift': '开启选股', // 【页面】设置-开启选股按钮
  'settings.enableAuth': '开启认证', // 【页面】设置-开启认证按钮
  'settings.enabledAlphaSiftSuccess': '已开启 AlphaSift 选股。', // 【页面】设置-开启选股成功提示
  'settings.enablingAlphaSift': '开启中...', // 【页面】设置-开启选中状态
  'settings.envDockerNote': 'Docker 部署中，`--env-file` / Compose `env_file` 只会在启动时注入环境变量；此处导出/导入的是后端当前活跃的 `.env` 文件。若需要让 WebUI 保存值随容器重建保留，请将 `ENV_FILE` 指向 `/app/data/runtime.env` 等可写数据卷文件，并避免启动环境里继续保留同名旧值。', // 【页面】设置-Docker 环境变量说明
  'settings.envExportNote': '导出内容仅包含当前已保存配置，不包含页面上尚未保存的本地草稿。', // 【页面】设置-导出说明
  'settings.envExported': '已导出当前已保存的 .env 备份。', // 【页面】设置-导出成功提示
  'settings.envImported': '已导入 .env 备份并重新加载配置。', // 【页面】设置-导入成功提示
  'settings.envImportedRefreshFailedMessage': '备份已导入，但重新加载配置失败，请手动重载页面。', // 【页面】设置-导入后刷新失败消息
  'settings.envImportedRefreshFailedRaw': 'Env import succeeded but config refresh failed', // 【页面】设置-导入后刷新失败原始信息
  'settings.envImportedRefreshFailedTitle': '配置已导入但刷新失败', // 【页面】设置-导入后刷新失败标题
  'settings.exportEnv': '导出 .env', // 【页面】设置-导出 .env 按钮
  'settings.exportingEnv': '导出中...', // 【页面】设置-导出中状态
  'settings.fallbackVersionWarning': '当前构建未提供发布版本，页面显示为 development；可结合代码版本和构建时间确认静态资源是否已更新。', // 【页面】设置-版本回退警告
  'settings.fieldAddKey': '添加 Key', // 【页面】设置-添加 Key 按钮
  'settings.fieldDelete': '删除', // 【页面】设置-删除字段按钮
  'settings.fieldSensitiveHint': '敏感内容默认隐藏，可点击眼睛图标查看明文。', // 【页面】设置-敏感字段提示
  'settings.fieldSensitiveMultiHint': ' 支持添加多个输入框进行增删。', // 【页面】设置-敏感多值字段提示
  'settings.generationBackendConcurrency': '并发 {count}', // 【页面】设置-并发数显示
  'settings.generationBackendFallback': '备用后端', // 【页面】设置-备用后端标签
  'settings.generationBackendGenerationOnly': '仅生成', // 【页面】设置-仅生成标签
  'settings.generationBackendHealthFailed': '检测失败', // 【页面】设置-检测失败状态
  'settings.generationBackendHealthPassed': '检测通过', // 【页面】设置-检测通过状态
  'settings.generationBackendHealthSkipped': '已跳过', // 【页面】设置-已跳过状态
  'settings.generationBackendLiteLLMDescription': '当前后端用于报告生成；问股工具调用仍沿用 LiteLLM Agent 路径。', // 【页面】设置-LiteLLM 后端说明
  'settings.generationBackendLocalCliDescription': '本地 CLI 只用于报告和文本生成，不支持问股工具调用。', // 【页面】设置-本地 CLI 后端说明
  'settings.generationBackendNeedsAction': '需要处理', // 【页面】设置-需要处理状态
  'settings.generationBackendPrimary': '主后端', // 【页面】设置-主后端标签
  'settings.generationBackendRefresh': '刷新', // 【页面】设置-刷新按钮
  'settings.generationBackendRefreshing': '刷新中', // 【页面】设置-刷新中状态
  'settings.generationBackendRunnable': '可尝试运行', // 【页面】设置-可尝试运行状态
  'settings.generationBackendSmokeFailed': '冒烟测试失败', // 【页面】设置-冒烟测试失败状态
  'settings.generationBackendSmokePassed': '冒烟测试通过', // 【页面】设置-冒烟测试通过状态
  'settings.generationBackendSmokePassedMessage': '生成后端冒烟测试通过。', // 【页面】设置-冒烟测试通过消息
  'settings.generationBackendSmokeTest': 'JSON 冒烟测试', // 【页面】设置-JSON 冒烟测试按钮
  'settings.generationBackendSmokeTesting': '测试中', // 【页面】设置-测试中状态
  'settings.generationBackendStatus': '生成后端状态', // 【页面】设置-生成后端状态标题
  'settings.generationBackendStatusDescription': '快速检查只读取配置，并检查本地 CLI 可执行文件是否可见；要确认真实请求是否能跑通，请运行 JSON 冒烟测试。', // 【页面】设置-生成后端状态说明
  'settings.generationBackendToolsSupported': '工具调用', // 【页面】设置-工具调用支持标签
  'settings.helpClose': '关闭配置说明', // 【页面】设置-关闭配置说明按钮
  'settings.helpExamples': '配置样例', // 【页面】设置-配置样例标签
  'settings.helpImpact': '影响范围', // 【页面】设置-影响范围标签
  'settings.helpNotes': '注意事项', // 【页面】设置-注意事项标签
  'settings.helpPurpose': '用途', // 【页面】设置-用途标签
  'settings.helpRelatedDocs': '相关文档', // 【页面】设置-相关文档标签
  'settings.helpTooltip': '查看配置说明', // 【页面】设置-查看配置说明提示
  'settings.helpValueNotes': '取值说明', // 【页面】设置-取值说明标签
  'settings.importConfirmContinue': '继续导入', // 【页面】设置-继续导入按钮
  'settings.importConfirmMessage': '当前页面还有未保存修改。继续导入会丢弃这些本地草稿，并立即用备份文件中的键值更新已保存配置。', // 【页面】设置-导入确认消息
  'settings.importConfirmTitle': '导入会覆盖当前草稿', // 【页面】设置-导入确认标题
  'settings.importEnv': '导入 .env', // 【页面】设置-导入 .env 按钮
  'settings.importingEnv': '导入中...', // 【页面】设置-导入中状态
  'settings.intelligentImport': '智能导入', // 【页面】设置-智能导入标题
  'settings.intelligentImportChooseFile': '选择文件', // 【页面】设置-选择文件按钮
  'settings.intelligentImportChooseImage': '选择图片', // 【页面】设置-选择图片按钮
  'settings.intelligentImportClear': '清空', // 【页面】设置-清空按钮
  'settings.intelligentImportConfigUpdated': '配置已更新，请再次点击「合并到自选股」', // 【页面】设置-配置已更新提示
  'settings.intelligentImportDescription': '从图片、文件或剪贴板中提取股票代码，并合并到自选股列表。', // 【页面】设置-智能导入说明
  'settings.intelligentImportFileSizeError': '文件不超过 2MB', // 【页面】设置-文件大小错误提示
  'settings.intelligentImportHint': '图片识别需预先配置 Vision 模型。建议先人工核对解析结果，再合并到自选股。', // 【页面】设置-智能导入提示
  'settings.intelligentImportImageSizeError': '图片不超过 5MB', // 【页面】设置-图片大小错误提示
  'settings.intelligentImportImageTypeError': '图片仅支持 JPG、PNG、WebP、GIF', // 【页面】设置-图片类型错误提示
  'settings.intelligentImportLoadConfigFirst': '请先加载配置后再合并', // 【页面】设置-先加载配置提示
  'settings.intelligentImportMergeFailed': '合并保存失败', // 【页面】设置-合并保存失败提示
  'settings.intelligentImportMergeToWatchlist': '合并到自选股', // 【页面】设置-合并到自选股按钮
  'settings.intelligentImportParse': '解析', // 【页面】设置-解析按钮
  'settings.intelligentImportParseFailed': '解析失败', // 【页面】设置-解析失败提示
  'settings.intelligentImportPastePlaceholder': '或粘贴 CSV/Excel 复制的文本...', // 【页面】设置-粘贴文本占位符
  'settings.intelligentImportRateLimited': '请求过于频繁，请稍后再试', // 【页面】设置-请求频繁提示
  'settings.intelligentImportRecognitionFailed': '识别失败，请重试', // 【页面】设置-识别失败提示
  'settings.intelligentImportReviewWarning': '建议人工逐条核对后再合并。高置信度默认勾选，中/低置信度需手动确认。', // 【页面】设置-人工核对警告
  'settings.intelligentImportSelectionSummary': '共 {valid} 条可合并，已勾选 {checked} 条', // 【页面】设置-选择摘要
  'settings.intelligentImportSupportedInputs': '支持图片、CSV/Excel 文件与剪贴板文本', // 【页面】设置-智能导入支持输入类型
  'settings.intelligentImportTextSizeError': '粘贴文本不超过 100KB', // 【页面】设置-文本大小错误提示
  'settings.intelligentImportTimeout': '请求超时，请检查网络后重试', // 【页面】设置-请求超时提示
  'settings.keepAuthDisabled': '保持已关闭', // 【页面】设置-保持已关闭按钮
  'settings.keepAuthEnabled': '保持已开启', // 【页面】设置-保持已开启按钮
  'settings.llmAccess': 'AI 模型接入', // 【页面】设置-AI 模型接入标题
  'settings.llmAccessDescription': '统一管理模型渠道、基础地址、API Key、主模型与备选模型。', // 【页面】设置-AI 模型接入说明
  'settings.notificationSettings': '通知设置', // 【页面】设置-通知设置标题
  'settings.notificationTest': '通知测试', // 【页面】设置-通知测试标题
  'settings.notificationTestBody': '正文', // 【页面】设置-通知测试正文标签
  'settings.notificationTestChannel': '渠道', // 【页面】设置-通知测试渠道标签
  'settings.notificationTestContent': '这是一条来自 HRS Web 设置页的通知测试消息。', // 【页面】设置-通知测试内容
  'settings.notificationTestDescription': '使用当前页面草稿发送一条真实测试通知；测试不会保存配置。', // 【页面】设置-通知测试说明
  'settings.notificationTestFailure': '测试失败', // 【页面】设置-测试失败提示
  'settings.notificationTestSend': '发送测试', // 【页面】设置-发送测试按钮
  'settings.notificationTestSuccess': '测试成功', // 【页面】设置-测试成功提示
  'settings.notificationTestTimeout': '超时秒数', // 【页面】设置-超时秒数标签
  'settings.notificationTestTitle': '标题', // 【页面】设置-通知测试标题标签
  'settings.notificationTestTitleValue': 'HRS 通知测试', // 【页面】设置-通知测试标题值
  'settings.notificationTesting': '测试中...', // 【页面】设置-测试中状态
  'settings.pageDescription': '统一管理模型、数据源、通知、安全认证与导入能力。', // 【页面】设置-设置页描述
  'settings.pageTitle': '系统设置', // 【页面】设置-系统设置标题
  'settings.eyebrow': 'Settings', // 【页面】设置-系统设置页眉标签
  'settings.pageTitleDocument': '系统设置 - HRS', // 【页面】设置-系统设置文档标题
  'settings.promptCacheAdvancedDescription': '维护 provider prompt cache 的观测、主动 hint 与脱敏诊断；默认配置已适合普通使用。', // 【页面】设置-Prompt Cache 高级设置说明
  'settings.promptCacheAdvancedTitle': 'Provider Prompt Cache 高级设置', // 【页面】设置-Prompt Cache 高级设置标题
  'settings.reload': '重新加载', // 【页面】设置-重新加载按钮
  'settings.reset': '重置', // 【页面】设置-重置按钮
  'settings.revert': '还原', // 【页面】设置-还原按钮
  'settings.saveConfig': '保存配置', // 【页面】设置-保存配置按钮
  'settings.saveConfigWithCount': '保存配置 ({count})', // 【页面】设置-保存配置含数量按钮
  'settings.saveRetry': '重试保存', // 【页面】设置-重试保存按钮
  'settings.saving': '保存中...', // 【页面】设置-保存中状态
  'settings.schedulerAddTime': '添加时间', // 【页面】设置-添加时间按钮
  'settings.schedulerDescription': '配置自动分析的每日执行时间，保存后长运行的 Web/API/Desktop 进程会按新配置生效。', // 【页面】设置-定时任务说明
  'settings.schedulerDisabled': '未启用', // 【页面】设置-定时任务未启用状态
  'settings.schedulerEffectiveTimes': '生效时间', // 【页面】设置-生效时间列表
  'settings.schedulerEnable': '启用定时任务', // 【页面】设置-启用定时任务按钮
  'settings.schedulerEnableDescription': '开启后会按下方时间自动执行分析任务。', // 【页面】设置-启用定时任务说明
  'settings.schedulerEnabled': '已启用', // 【页面】设置-定时任务已启用状态
  'settings.schedulerLastError': '最近错误', // 【页面】设置-最近错误时间
  'settings.schedulerLastSuccess': '上次成功', // 【页面】设置-上次成功时间
  'settings.schedulerNextRun': '下次执行', // 【页面】设置-下次执行时间
  'settings.schedulerRefresh': '刷新状态', // 【页面】设置-刷新状态按钮
  'settings.schedulerRefreshing': '刷新中...', // 【页面】设置-刷新中状态
  'settings.schedulerRemoveTime': '删除时间', // 【页面】设置-删除时间按钮
  'settings.schedulerRunAccepted': '已提交执行请求。', // 【页面】设置-执行请求已提交提示
  'settings.schedulerRunNow': '立即执行一次', // 【页面】设置-立即执行一次按钮
  'settings.schedulerRunning': '运行中', // 【页面】设置-运行中状态
  'settings.schedulerRunningNow': '执行中...', // 【页面】设置-执行中状态
  'settings.schedulerStatus': '当前状态', // 【页面】设置-当前状态标签
  'settings.schedulerTimeInputAria': '定时执行时间 {index}', // 【页面】设置-定时执行时间无障碍标签
  'settings.schedulerTimes': '定时执行时间', // 【页面】设置-定时执行时间列表
  'settings.schedulerTitle': '定时任务', // 【页面】设置-定时任务标题
  'settings.setupGuideAddStocks': '维护自选股', // 【页面】设置-维护自选股按钮
  'settings.setupGuideCheckingSummary': '正在读取配置状态，完成后会显示缺失项和试跑入口。', // 【页面】设置-正在检查配置摘要
  'settings.setupGuideCheckingTitle': '正在检查首次启动配置', // 【页面】设置-正在检查配置标题
  'settings.setupGuideCompleteTitle': '基础配置已满足最小可用分析', // 【页面】设置-基础配置已完成标题
  'settings.setupGuideConfigureLlm': '配置模型', // 【页面】设置-配置模型按钮
  'settings.setupGuideConfigureNotification': '配置通知', // 【页面】设置-配置通知按钮
  'settings.setupGuideDescription': '按最小可用分析流程检查自选股、模型渠道和通知配置，完成后可直接发起一次简短试跑。', // 【页面】设置-首次启动配置检查说明
  'settings.setupGuideHiddenDescription': '需要重新检查基础配置、模型和通知时，可再次展开。', // 【页面】设置-配置检查已隐藏描述
  'settings.setupGuideHiddenTitle': '首次启动配置检查已隐藏', // 【页面】设置-配置检查已隐藏标题
  'settings.setupGuideHide': '暂时隐藏', // 【页面】设置-暂时隐藏按钮
  'settings.setupGuideIncompleteTitle': '还有基础配置需要处理', // 【页面】设置-基础配置未完成标题
  'settings.setupGuideMissingSummary': '还缺少 {count} 项：{labels}', // 【页面】设置-缺少配置项摘要
  'settings.setupGuideOpen': '展开检查', // 【页面】设置-展开检查按钮
  'settings.setupGuideReadySummary': '所有必需项已就绪，可运行一次简短分析验证链路。', // 【页面】设置-配置就绪摘要
  'settings.setupGuideRefresh': '刷新检查', // 【页面】设置-刷新检查按钮
  'settings.setupGuideRefreshing': '刷新中...', // 【页面】设置-刷新中状态
  'settings.setupGuideRunSmoke': '简短试跑', // 【页面】设置-简短试跑按钮
  'settings.setupGuideSmokeAccepted': '已提交 {stock} 的简短分析任务。', // 【页面】设置-试跑已提交
  'settings.setupGuideSmokeAcceptedWithTask': '已提交 {stock} 的简短分析任务：{taskId}', // 【页面】设置-试跑已提交含任务
  'settings.setupGuideSmokeNeedsStock': '需要至少一个自选股代码后才能试跑。', // 【页面】设置-试跑需要自选股提示
  'settings.setupGuideSmokeNotReady': '请先完成必需配置后再运行试跑。', // 【页面】设置-试跑未就绪提示
  'settings.setupGuideSmokeRunning': '提交中...', // 【页面】设置-提交中状态
  'settings.setupGuideSmokeUnavailableTitle': '暂不能试跑', // 【页面】设置-暂不能试跑标题
  'settings.setupGuideTitle': '首次启动配置检查', // 【页面】设置-首次启动配置检查标题
  'settings.setupGuideUnknownSummary': '配置状态读取失败。可先检查或修改设置项，稍后刷新检查结果。', // 【页面】设置-无法判断配置状态摘要
  'settings.setupGuideUnknownTitle': '暂无法判断配置状态', // 【页面】设置-无法判断配置状态标题
  'settings.setupStatusConfigured': '已配置', // 【页面】设置-已配置状态
  'settings.setupStatusInherited': '已继承', // 【页面】设置-已继承状态
  'settings.setupStatusNeedsAction': '待处理', // 【页面】设置-待处理状态
  'settings.setupStatusOptional': '可选', // 【页面】设置-可选状态
  'settings.updateBuildDescription': '重新执行前端构建或 Docker 镜像构建后，此处的代码版本和构建时间会更新，可用来确认当前页面资源是否已切换。', // 【页面】设置-更新构建说明
  'settings.versionBuildTime': '构建时间', // 【页面】设置-构建时间标签
  'settings.versionDesktop': '桌面端版本', // 【页面】设置-桌面端版本标签
  'settings.versionInfo': '版本信息', // 【页面】设置-版本信息标题
  'settings.versionInfoDescription': '用于确认当前 WebUI 静态资源是否已经切换到最新构建。', // 【页面】设置-版本信息说明
  'settings.versionRevision': '代码版本', // 【页面】设置-代码版本标签
  'settings.versionWebui': 'WebUI 版本', // 【页面】设置-WebUI 版本标签
  'settings.viewConfigItems': '查看配置项', // 【页面】设置-查看配置项按钮
  // stockBar.*
  'stockBar.emptyDescription': '完成首次分析后，这里将按股票展示最新分析结果。', // 【页面】个股工具条-个股栏空状态描述
  'stockBar.emptyTitle': '暂无个股记录', // 【页面】个股工具条-个股栏空状态标题
  'stockBar.loading': '加载个股中...', // 【页面】个股工具条-个股栏加载中状态
  'stockBar.market': '大盘', // 【页面】个股工具条-个股栏大盘入口
  'stockBar.title': '个股栏', // 【页面】个股工具条-个股栏标题
  // stockTrend.*
  'stockTrend.allHistory': '全部历史', // 【页面】个股趋势-全部历史选项
  'stockTrend.averageScore': '平均分 {score}', // 【页面】个股趋势-平均分显示
  'stockTrend.backToCurrentReport': '返回当前报告', // 【页面】个股趋势-返回当前报告按钮
  'stockTrend.changePct': '涨跌幅', // 【页面】个股趋势-涨跌幅标签
  'stockTrend.currentAdvice': '当前观点', // 【页面】个股趋势-当前观点标签
  'stockTrend.currentScore': '当前分数', // 【页面】个股趋势-当前分数标签
  'stockTrend.historyModelCount': '历史模型 {count} 种', // 【页面】个股趋势-历史模型数量
  'stockTrend.latestTime': '最近一次 {time}', // 【页面】个股趋势-最近一次时间
  'stockTrend.loadFailed': '历史趋势加载失败', // 【页面】个股趋势-历史趋势加载失败提示
  'stockTrend.loadMore': '加载更多', // 【页面】个股趋势-加载更多按钮
  'stockTrend.loadedSummary': '已加载 {loaded} / {total} 条 · 排序：最新优先 · 模型：全部', // 【页面】个股趋势-加载摘要
  'stockTrend.loading': '加载同股历史中...', // 【页面】个股趋势-同股历史加载中
  'stockTrend.loadingMore': '加载中...', // 【页面】个股趋势-加载更多中状态
  'stockTrend.model': '模型', // 【页面】个股趋势-模型标签
  'stockTrend.modelCountSuffix': '{count}次', // 【页面】个股趋势-模型次数后缀
  'stockTrend.moreEmptyDescription': '完成多次分析后，这里会展示观点变化、评分走势和模型记录。', // 【页面】个股趋势-更多历史空状态描述
  'stockTrend.moreEmptyTitle': '暂无更多同股历史分析', // 【页面】个股趋势-更多历史空状态标题
  'stockTrend.neverRecorded': '未记录', // 【页面】个股趋势-未记录提示
  'stockTrend.noModelTitle': '未记录模型', // 【页面】个股趋势-未记录模型标题
  'stockTrend.records': '历史分析记录', // 【页面】个股趋势-历史记录标签
  'stockTrend.reload': '重新加载', // 【页面】个股趋势-重新加载按钮
  'stockTrend.report': '查看报告', // 【页面】个股趋势-查看报告按钮
  'stockTrend.result': '分析结果', // 【页面】个股趋势-分析结果标签
  'stockTrend.score': '分数', // 【页面】个股趋势-分数标签
  'stockTrend.stockPrice': '股价', // 【页面】个股趋势-股价标签
  'stockTrend.table.action': '操作', // 【页面】个股趋势-趋势表格操作列
  'stockTrend.time': '时间', // 【页面】个股趋势-趋势表格时间列
  'stockTrend.title': '历史趋势', // 【页面】个股趋势-历史趋势标题
  'stockTrend.turnoverRate': '换手率', // 【页面】个股趋势-换手率标签
  'stockTrend.volumeRatio': '量比', // 【页面】个股趋势-量比标签
  'stockTrend.window30': '近30天', // 【页面】个股趋势-近 30 天窗口
  'stockTrend.window90': '近90天', // 【页面】个股趋势-近 90 天窗口
  // stockUnit.*
  'stockUnit.amountWanYi': '万亿', // 【页面】个股单位-金额单位万亿
  'stockUnit.amountYi': '亿', // 【页面】个股单位-金额单位亿
  'stockUnit.volumeHundredMillionLots': '亿手', // 【页面】个股单位-成交量单位亿手
  'stockUnit.volumeTenThousandLots': '万手', // 【页面】个股单位-成交量单位万手
  // usage.*
  'usage.breakdown': 'Breakdown', // 【页面】用量-用量明细标签
  'usage.callType.agent': '问股 Agent', // 【页面】用量-问股调用类型
  'usage.callType.analysis': '个股分析', // 【页面】用量-个股分析调用类型
  'usage.callType.marketReview': '大盘复盘', // 【页面】用量-大盘复盘调用类型
  'usage.callType.unknown': '{type}', // 【页面】用量-未知调用类型
  'usage.callTypeDetail': '{calls} 次 · Prompt {prompt} · Completion {completion}', // 【页面】用量-调用类型明细文案
  'usage.callTypeTitle': '调用类型', // 【页面】用量-调用类型标题
  'usage.calls': '{count} 次调用', // 【页面】用量-调用次数统计
  'usage.completionTokens': 'Completion tokens', // 【页面】用量-Completion token 数量
  'usage.completionTokensHint': '模型输出消耗', // 【页面】用量-Completion token 说明
  'usage.dateRange': '{from} 至 {to}', // 【页面】用量-日期范围
  'usage.description': '查看 LLM 调用次数、Prompt/Completion Token 消耗、模型用量和最近调用明细。', // 【页面】用量-用量页面描述
  'usage.emptyDescription': '完成一次分析、大盘复盘或问股调用后，这里会显示模型用量。', // 【页面】用量-用量空状态描述
  'usage.emptyTitle': '暂无 Token 用量记录', // 【页面】用量-用量空状态标题
  'usage.error.message': 'Token 用量数据加载失败', // 【页面】用量-用量加载失败提示
  'usage.error.title': 'Token 用量加载失败', // 【页面】用量-用量加载失败标题
  'usage.eyebrow': 'Usage', // 【页面】用量-用量页面眉标
  'usage.maxSingleCall': '单次峰值', // 【页面】用量-单次调用 token 峰值
  'usage.modelUsage': '模型用量', // 【页面】用量-模型用量区块标题
  'usage.modelUsageDescription': '按模型聚合 Token 消耗、调用次数和单次峰值。', // 【页面】用量-模型用量说明
  'usage.noRecentCalls': '暂无最近调用记录', // 【页面】用量-最近调用空状态
  'usage.period.all': '全部', // 【页面】用量-全部时间范围
  'usage.period.month': '本月', // 【页面】用量-本月时间范围
  'usage.period.today': '今日', // 【页面】用量-今日时间范围
  'usage.period.label': '时间范围', // 【页面】用量-时间范围切换标签（无障碍）
  'usage.promptTokens': 'Prompt tokens', // 【页面】用量-Prompt token 数量
  'usage.promptTokensHint': '输入上下文消耗', // 【页面】用量-Prompt token 说明
  'usage.recentCalls': '最近调用', // 【页面】用量-最近调用区块标题
  'usage.recentCallsDescription': '最近 50 条 LLM token 审计记录。', // 【页面】用量-最近调用说明
  'usage.refresh': '刷新', // 【页面】用量-刷新按钮
  'usage.table.model': '模型', // 【页面】用量-调用表格模型列
  'usage.table.time': '时间', // 【页面】用量-调用表格时间列
  'usage.table.type': '类型', // 【页面】用量-调用表格类型列
  'usage.title': 'Token 用量监控', // 【页面】用量-用量页面标题
  'usage.totalCalls': '调用次数', // 【页面】用量-总调用次数
  'usage.totalCallsHint': '已记录的 LLM 调用', // 【页面】用量-总调用次数说明
  'usage.totalTokens': '总 tokens', // 【页面】用量-总 token 数量
  // watchlist.*
  'watchlist.add': '添加自选股', // 【页面】自选-添加自选股按钮
  'watchlist.addPlaceholder': '添加代码，如 600519', // 【页面】自选-添加自选股占位符
  'watchlist.analyzeAll': '分析全部', // 【页面】自选-分析全部自选股
  'watchlist.analyzePending': '仅未分析', // 【页面】自选-仅分析未分析自选股
  'watchlist.analyzedToday': '今日已分析', // 【页面】自选-今日已分析状态
  'watchlist.batchFailed': '自选股批量分析提交失败', // 【页面】自选-批量分析失败提示
  'watchlist.batchIncompleteResponse': '批量接口本组请求 {requested} 只，仅确认 {confirmed} 只，返回结果不完整', // 【页面】自选-批量响应不完整提示
  'watchlist.batchPartiallySubmitted': '已确认提交 {accepted} 个任务，{duplicates} 个正在运行；另有 {unconfirmed} 只未确认，已停止后续提交并刷新任务列表。原因：{error}', // 【页面】自选-批量部分提交提示
  'watchlist.batchSubmitted': '已提交 {accepted} 个任务，{duplicates} 个正在运行', // 【页面】自选-批量提交成功提示
  'watchlist.emptyDescription': '在报告详情或这里添加股票后，可一键运行整组自选股。', // 【页面】自选-自选股空状态描述
  'watchlist.emptyTitle': '暂无自选股', // 【页面】自选-自选股空状态标题
  'watchlist.listHint': '按自选顺序展示，今日状态实时标记', // 【页面】自选-自选股列表说明
  'watchlist.loading': '加载自选股中...', // 【页面】自选-自选股加载中状态
  'watchlist.noPendingAnalyze': '今天没有待分析的自选股。', // 【页面】自选-无待分析自选股提示
  'watchlist.noStocksAnalyze': '请先添加自选股。', // 【页面】自选-无自选股提示
  'watchlist.notAnalyzedToday': '今日未分析', // 【页面】自选-今日未分析状态
  'watchlist.pendingStatusUnavailable': '自选股今日状态仍有未知项，请刷新后再提交仅未分析。', // 【页面】自选-待分析状态不可用提示
  'watchlist.pendingToday': '今日待分析', // 【页面】自选-今日待分析状态
  'watchlist.refresh': '刷新自选股', // 【页面】自选-刷新自选股按钮
  'watchlist.removeAria': '从自选股移除 {code}', // 【页面】自选-移除自选股无障碍标签
  'watchlist.submitting': '提交中', // 【页面】自选-自选股提交中状态
  'watchlist.tabHistory': '历史', // 【页面】自选-自选股历史标签页
  'watchlist.tabToday': '今日', // 【页面】自选-自选股今日标签页
  'watchlist.tabWatchlist': '自选', // 【页面】自选-自选股自选标签页
  'watchlist.taskRunning': '任务{status}', // 【页面】自选-自选股任务运行状态
  'watchlist.title': '自选股', // 【页面】自选-自选股标题
  'watchlist.todayCoverage': '今日覆盖', // 【页面】自选-今日分析覆盖率
  'watchlist.todayEmptyDescription': '今天完成分析后，这里会按评分显示股票排行。', // 【页面】自选-今日空状态描述
  'watchlist.todayEmptyTitle': '今天还没有分析结果', // 【页面】自选-今日空状态标题
  'watchlist.todayLoadErrorDescription': '完整历史分页加载失败，为避免展示不完整排行，请刷新后重试。', // 【页面】自选-今日排行加载失败描述
  'watchlist.todayLoadErrorTitle': '今日排行加载失败', // 【页面】自选-今日排行加载失败标题
  'watchlist.todaySortHint': '按情绪分优先排序', // 【页面】自选-今日排序提示
  'watchlist.todayStatusLoading': '确认今日状态中', // 【页面】自选-今日状态确认中
  'watchlist.todayStatusUnavailable': '今日状态未知', // 【页面】自选-今日状态未知提示
  'watchlist.todayTitle': '今日分析', // 【页面】自选-今日分析标题
  'watchlist.topScore': '最高分', // 【页面】自选-最高分标签
  'watchlist.watchlistCoverage': '自选覆盖' // 【页面】自选-自选覆盖率

} as const;

export type UiTextKey = keyof typeof zh;

export default zh;

