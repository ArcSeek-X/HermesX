/**
 * 简体中文（zh）文案：导航菜单 layout.nav 类别。
 * 由 uiText-zh.ts 按类别拆分，经 uiText-zh/index.ts 聚合；key 与三语主字典保持一致。
 */

export const navZh = {
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
  'emotion.board.col.turnoverRate': '换手率', // 涨跌停榜单表头：换手率
  'emotion.board.col.industry': '所属行业', // 涨跌停榜单表头：所属行业
  'emotion.board.col.limitDownTime': '跌停时间', // 跌停榜单表头：跌停时间
  'emotion.board.kpi.limitUpCount': '涨停数量', // 涨停榜 KPI：涨停家数
  'emotion.board.kpi.maxBoards': '连板高度', // 涨停榜 KPI：最高连板数
  'emotion.board.kpi.sealAmount': '封单总额', // 涨停榜 KPI：封单资金合计
  'emotion.board.kpi.breakRate': '炸板率', // 涨停榜 KPI：炸板率（炸板股池数据待接入）
  'emotion.board.kpi.previousPremium': '昨日涨停溢价', // 涨停榜 KPI：昨日涨停股今日溢价（昨日涨停池数据待接入）
  'emotion.board.kpi.limitDownCount': '跌停数量', // 跌停榜 KPI：跌停家数
  'emotion.board.kpi.maxDownBoards': '跌停连板高度', // 跌停榜 KPI：最高连续跌停数
  'emotion.board.kpi.downSealAmount': '封停单总额', // 跌停榜 KPI：封停单资金合计
  'emotion.board.kpi.downTurnoverAmount': '跌停成交额', // 跌停榜 KPI：跌停股成交总额
  'emotion.board.kpi.avgTurnoverRate': '平均换手率', // 跌停榜 KPI：跌停股平均换手率
  'emotion.board.kpi.liquidityNote': '流动性参考', // 跌停榜 KPI：平均换手率辅助说明
  'emotion.board.kpi.boardsValue': '{count} 板', // 涨跌停榜单 KPI：连板高度取值
  'emotion.board.kpi.prevDayDelta': '较前日 {delta}', // 涨跌停榜单 KPI：较前一交易日变化
  'emotion.board.kpi.topBoardStock': '最高标 {name}', // 涨跌停榜单 KPI：最高连板标的名称
  'emotion.board.kpi.sealRatio': '占成交 {ratio}', // 涨跌停榜单 KPI：封单总额占成交额比例
  'emotion.board.openKline': '查看 K 线', // 涨跌停榜单：代码/名称列点击跳转 K 线页提示
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
  'layout.nav.stockMetricView.title': '股票度量视图', // 股票度量视图导航项
  'layout.nav.stockMetricView.description': '浏览全市场股票度量数据，支持筛选、排序与导出', // 股票度量视图导航项描述
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

  'layout.nav.userManagement.title': '用户管理', // 系统管理-用户管理导航项
  'layout.nav.userManagement.description': '管理系统用户与账号信息', // 用户管理导航项描述
  'layout.nav.orgManagement.title': '组织管理', // 系统管理-组织管理导航项
  'layout.nav.orgManagement.description': '管理部门与组织层级结构', // 组织管理导航项描述
  'layout.nav.menuManagement.title': '菜单管理', // 系统管理-菜单管理导航项
  'layout.nav.menuManagement.description': '维护系统菜单与页面入口', // 菜单管理导航项描述

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
  'layout.nav.development.docsCountryMarketSelect.title': '国家/市场选择', // 国家/市场选择组件文档导航项
  'layout.nav.development.docsCountryMarketSelect.description': 'CountryMarketSelect 国家/市场单选与多选下拉组件演示与用法', // 国家市场选择导航项描述
  'layout.nav.development.docsChip.title': '标签芯片', // 标签芯片组件文档导航项
  'layout.nav.development.docsChip.description': 'Chip 圆角胶囊标签组件演示与用法', // 标签芯片导航项描述
  'layout.nav.development.docsEmptyState.title': '空状态', // 空状态组件文档导航项
  'layout.nav.development.docsEmptyState.description': 'EmptyState 空状态组件演示与用法', // 空状态导航项描述

} as const;
