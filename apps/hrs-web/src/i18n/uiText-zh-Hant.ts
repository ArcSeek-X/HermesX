/**
 * @file uiText-zh-Hant.ts
 * @description 繁體中文（zh-Hant）界面文案配置，键值结构与 uiText-zh.ts 保持一致
 * @module i18n
 */

const zhHant = {

  // ---- 第 1 类 全局 common ----
  'common.cancel': '取消', // 通用取消按鈕文案
  'common.clear': '清除', // 通用清除文案
  'common.clearing': '清除中', // 清除中狀態
  'common.close': '關閉', // 通用關閉按鈕文案
  'common.closeDrawer': '關閉抽屉', // 關閉抽屉組件
  'common.confirm': '確定', // 通用確認按鈕文案
  'common.copied': '已複製!', // 複製成功提示
  'common.copy': '複製', // 複製按鈕文案
  'common.delete': '刪除', // 通用刪除按鈕文案
  'common.deleting': '刪除中', // 刪除進行中狀態
  'common.details': '查看詳情', // 查看詳情入口
  'common.disabled': '未啟用', // 功能未啟用狀態
  'common.enabled': '已啟用', // 功能已啟用狀態
  'common.failure': '失敗', // 通用失敗狀態
  'common.hideContent': '隱藏內容', // 隱藏敏感內容
  'common.itemsCount': '{count}只', // 条目數量統計
  'common.loading': '正在載入', // 通用載入中文案
  'common.noData': '暫无數據', // 通用空數據提示
  'common.processing': '處理中...', // 通用處理中狀態
  'common.readOnly': '只讀', // 只讀模式標识
  'common.retry': '重試', // 通用重試按鈕
  'common.selectAllCurrent': '全選目前', // 全選目前列表項
  'common.selectPlaceholder': '請選擇', // 選擇器占位符
  'common.selectedCount': '已選 {count}', // 已選數量統計
  'common.sensitive': '敏感', // 敏感字段標识
  'common.showContent': '顯示內容', // 顯示敏感內容
  'common.success': '成功', // 通用成功狀態

  // ---- 第 2 类 语言 language ----
  'language.chineseSimplified': '簡體中文', // 簡體中文語言選項
  'language.chineseTraditional': '繁體中文', // 繁體中文語言選項
  'language.current': '繁體中文', // 目前界面語言名稱
  'language.english': 'English', // 英文語言選項
  'language.short.en': 'EN', // 英文語言簡寫
  'language.short.zh': '中', // 中文語言簡寫
  'language.short.zhHant': '繁', // 繁體中文語言簡寫
  'language.toggle': '切換界面語言', // 切換語言按鈕提示
  'language.uiLanguage': '界面語言', // 界面語言設定項標題

  // ---- 第 3 类 主题 theme ----
  'theme.dark': '深色', // 深色主題名稱
  'theme.light': '淺色', // 淺色主題名稱
  'theme.menu': '主題模式', // 主題模式菜單標題
  'theme.primary': '主色', // 主題主色配置標簽
  'theme.reset': '重置', // 重置主題主色按鈕
  'theme.save': '儲存', // 儲存主題設定按鈕
  'theme.system': '跟随系統', // 跟随系統主題
  'theme.theme': '主題', // 主題通用標簽
  'theme.toggle': '切換主題', // 切換主題按鈕提示

  // ---- 第 4 类 布局与菜单 layout ----
  // 布局直属 layout.*
  'layout.appFallbackDescription': 'Web workspace', // 應用回退描述文案
  'layout.appFallbackTitle': 'HermesX', // 應用回退標題
  'layout.collapseSidebar': '折叠側邊欄', // 折叠側邊欄按鈕
  'layout.desktopSidebar': '桌面側邊導航', // 桌面端側邊欄標簽
  'layout.expandSidebar': '展開側邊欄', // 展開側邊欄按鈕
  'layout.logout': '登出', // 登出登入按鈕
  'layout.logoutConfirm': '確認登出', // 登出確認按鈕
  'layout.logoutMessage': '確認登出目前登入狀態吗？登出後需要重新輸入密碼登入。', // 登出確認提示文案
  'layout.logoutTitle': '登出登入', // 登出登入弹窗標題
  'layout.mainNav': '主導航', // 主導航區域標簽
  'layout.navMenu': '導航菜單', // 導航菜單標簽
  'layout.newChatMessage': '問股有新消息', // 問股新消息提示
  'layout.openNav': '打開導航菜單', // 打開導航菜單提示
  // 头部操作区 layout.header.*
  'layout.header.language': '界面語言', // 頭部中英文切換按鈕
  'layout.header.themeSettings': '主題設定', // 頭部主題設定按鈕
  'layout.header.userSettings': '個人設定', // 頭部個人設定按鈕
  // 导航菜单 layout.nav.*
  'layout.nav.alerts.title': '告警', // 告警導航項
  'layout.nav.alerts.description': '規則、觸發記錄與通知嘗試', // 告警导航项描述
  'layout.nav.backtest.title': '回測', // 回測導航項
  'layout.nav.backtest.description': '回測任務與結果瀏覽', // 回测导航项描述
  'layout.nav.chat.title': '問股', // 問股導航項
  'layout.nav.chat.description': '多輪策略問答與歷史會話管理', // 问股导航项描述
  'layout.nav.codeTest.title': '測試', // 測試頁導航項
  'layout.nav.codeTest.description': '元件展示與聯調測試頁', // 测试导航项描述
  'layout.nav.dashboard.title': '總覽', // 總覽導航項
  'layout.nav.dashboard.description': '市場行情與核心指標總覽', // 总览导航项描述
  'layout.nav.decisionSignals.title': 'AI 建议', // AI 建议導航項
  'layout.nav.decisionSignals.description': 'AI 建議、風險與觀察條件', // AI 建议导航项描述
  'layout.nav.home.title': '首頁', // 首頁導航項
  'layout.nav.home.description': '股票分析與歷史報告工作臺', // 首页导航项描述
  'layout.nav.kline.title': 'K 线', // K 线導航項
  'layout.nav.kline.description': '個股 K 線走勢、技術指標與多週期分析', // K 线导航项描述
  'layout.nav.liveNews.title': '快訊', // 即時快訊導航項
  'layout.nav.liveNews.description': '7x24 財經快訊，依頻道篩選與重要級過濾', // 快讯导航项描述
  'layout.nav.portfolio.title': '持倉', // 持倉導航項
  'layout.nav.portfolio.description': '組合快照、手工錄入與風險分析', // 持仓导航项描述
  'layout.nav.review.title': '復盤', // 復盤導航項
  'layout.nav.review.description': '歷史復盤與大盤回顧', // 复盘导航项描述
  'layout.nav.screening.title': '選股', // 選股導航項
  'layout.nav.screening.description': 'AlphaSift 策略選股與候選研究', // 选股导航项描述
  'layout.nav.sectorAnalysis.title': '板塊', // 板塊分析導航項
  'layout.nav.sectorAnalysis.description': '板塊漲跌、資金流向與熱點追蹤', // 板块导航项描述
  'layout.nav.settings.title': '設定', // 設定導航項
  'layout.nav.settings.description': '系統配置、模型與認證管理', // 设置导航项描述
  'layout.nav.stockCloud.title': '個股雲圖', // 個股雲圖導航項
  'layout.nav.stockCloud.description': '個股雲圖與板塊分佈視覺化', // 个股云图导航项描述
  'layout.nav.usage.title': '用量', // 用量導航項
  'layout.nav.usage.description': 'LLM Token 消耗與模型呼叫明細', // 用量导航项描述
  'layout.nav.watchlist.title': '自選', // 自選導航項
  'layout.nav.watchlist.description': '自選股列表與行情追蹤', // 自选导航项描述

  // ---- 第 5 类 组件 component ----
  // component.runFlow.*
  'component.runFlow.drawerTitle': '运行流', // 运行流抽屉標題
  'component.runFlow.durationMinutes': '{value} 分鐘', // 分鐘耗時顯示
  'component.runFlow.durationMs': '{value} ms', // 毫秒耗時顯示
  'component.runFlow.durationSeconds': '{value} 秒', // 秒耗時顯示
  'component.runFlow.edge.control': '控製', // 控製邊類型
  'component.runFlow.edge.data': '數據', // 數據邊類型
  'component.runFlow.edge.fallback': '降級回退', // 回退邊類型
  'component.runFlow.edge.retry': '重試', // 重試邊類型
  'component.runFlow.edgeLabel.details': '詳情', // 詳情邊標簽
  'component.runFlow.edgeLabel.invoke': '調用', // 調用邊標簽
  'component.runFlow.emptyDescription': '請選擇一個活跃任務或歷史報告查看运行流。', // 运行流空狀態描述
  'component.runFlow.emptySnapshotDescription': '目前快照沒有節點或事件；缺少 diagnostics 時會顯示骨架或空狀態。', // 运行流快照空描述
  'component.runFlow.emptySnapshotTitle': '暫无运行流細節', // 运行流快照空標題
  'component.runFlow.emptyTitle': '暫无运行流', // 运行流空狀態標題
  'component.runFlow.errorTitle': '运行流載入失敗', // 运行流載入失敗標題
  'component.runFlow.events.count': '{count} 条事件', // 事件數量
  'component.runFlow.events.empty': '目前篩選下暫无事件。', // 事件空狀態
  'component.runFlow.events.filter.all': '全部', // 全部事件篩選
  'component.runFlow.events.filter.cancelled': '取消', // 取消事件篩選
  'component.runFlow.events.filter.fallback': '降級回退/重試', // 回退重試事件篩選
  'component.runFlow.events.filter.important': '關键', // 關键事件篩選
  'component.runFlow.events.filter.problems': '失敗/告警', // 失敗告警事件篩選
  'component.runFlow.events.filters': '事件篩選', // 事件篩選標簽
  'component.runFlow.events.openNode': '查看事件 {title} 關联節點', // 查看事件關联節點
  'component.runFlow.events.title': '事件流', // 事件流標題
  'component.runFlow.eyebrow': '运行流', // 运行流眉標
  'component.runFlow.graph.collapse': '收合', // 收合節點按鈕
  'component.runFlow.graph.collapseNode': '收合 {label} 运行尝試', // 收合節點尝試
  'component.runFlow.graph.description': '自動分层展示入口、數據来源、分析引擎和产物鏈路。', // 运行拓扑圖說明
  'component.runFlow.graph.expand': '展開', // 展開節點按鈕
  'component.runFlow.graph.expandNode': '展開 {label} 运行尝試', // 展開節點尝試
  'component.runFlow.graph.nodeAria': '{label} 節點，狀態 {status}', // 拓扑節點无障碍標簽
  'component.runFlow.graph.startedAt': '開始', // 拓扑開始時間標簽
  'component.runFlow.graph.title': '运行拓扑', // 运行拓扑圖標題
  'component.runFlow.historyDrawerTitle': '{stock} 歷史运行流', // 歷史运行流抽屉標題
  'component.runFlow.loadingDescription': '正在讀取任務快照、运行诊断和事件鏈路。', // 运行流載入說明
  'component.runFlow.loadingTitle': '正在載入运行流', // 运行流載入標題
  'component.runFlow.nodeDetails.attemptList': '运行尝試', // 运行尝試列表
  'component.runFlow.nodeDetails.attempts': '尝試次數', // 節點尝試次數
  'component.runFlow.nodeDetails.blockScores': '數據塊评分', // 數據塊评分
  'component.runFlow.nodeDetails.close': '關閉節點詳情', // 關閉節點詳情按鈕
  'component.runFlow.nodeDetails.collapseAttempts': '收合尝試', // 收合尝試按鈕
  'component.runFlow.nodeDetails.column.duration': '耗時', // 尝試列表耗時列
  'component.runFlow.nodeDetails.column.name': '名稱', // 尝試列表名稱列
  'component.runFlow.nodeDetails.column.records': '記錄', // 尝試列表記錄列
  'component.runFlow.nodeDetails.column.status': '狀態', // 尝試列表狀態列
  'component.runFlow.nodeDetails.column.time': '時間', // 尝試列表時間列
  'component.runFlow.nodeDetails.contextBlocks': '上下文輸入', // 上下文輸入塊
  'component.runFlow.nodeDetails.contextQuality': '上下文质量', // 上下文质量標簽
  'component.runFlow.nodeDetails.count.available': '可用', // 可用數量
  'component.runFlow.nodeDetails.count.degraded': '部分降級', // 降級數量
  'component.runFlow.nodeDetails.count.fallback': '降級回退', // 回退數量
  'component.runFlow.nodeDetails.count.missing': '缺失', // 缺失數量
  'component.runFlow.nodeDetails.count.partial': '部分', // 部分數量
  'component.runFlow.nodeDetails.count.skipped': '跳過', // 跳過數量
  'component.runFlow.nodeDetails.duration': '耗時', // 節點耗時標簽
  'component.runFlow.nodeDetails.empty': '選擇一個節點查看詳情。', // 節點詳情空狀態
  'component.runFlow.nodeDetails.endedAt': '結束時間', // 節點結束時間
  'component.runFlow.nodeDetails.expandAttempts': '展開尝試', // 展開尝試按鈕
  'component.runFlow.nodeDetails.kind': '類型', // 節點類型標簽
  'component.runFlow.nodeDetails.metadata': '元數據', // 節點元數據
  'component.runFlow.nodeDetails.overallScore': '综合评分', // 综合评分
  'component.runFlow.nodeDetails.provider': '提供方', // 節點提供方標簽
  'component.runFlow.nodeDetails.qualityLevel': '等級', // 质量等級
  'component.runFlow.nodeDetails.recordCount': '記錄數', // 節點記錄數
  'component.runFlow.nodeDetails.startedAt': '開始時間', // 節點開始時間
  'component.runFlow.nodeDetails.title': '節點詳情', // 節點詳情標題
  'component.runFlow.nodeDetails.version': '版本', // 節點版本標簽
  'component.runFlow.nodeKind.analysis': '分析', // 分析節點類型
  'component.runFlow.nodeKind.artifact': '产物', // 产物節點類型
  'component.runFlow.nodeKind.dataSource': '數據源', // 數據源節點類型
  'component.runFlow.nodeKind.entry': '入口', // 入口節點類型
  'component.runFlow.nodeKind.model': '模型', // 模型節點類型
  'component.runFlow.nodeKind.notification': '通知', // 通知節點類型
  'component.runFlow.nodeKind.queue': '队列', // 队列節點類型
  'component.runFlow.open': '查看运行流', // 查看运行流入口
  'component.runFlow.openHistoryAria': '查看歷史記錄 {recordId} 运行流', // 查看歷史运行流无障碍標簽
  'component.runFlow.refresh': '重新整理', // 运行流重新整理按鈕
  'component.runFlow.refreshing': '重新整理中', // 运行流重新整理中狀態
  'component.runFlow.retry': '重新載入', // 运行流重新載入
  'component.runFlow.severity.danger': '危險', // 危險級別
  'component.runFlow.severity.info': '信息', // 信息級別
  'component.runFlow.severity.success': '成功', // 成功級別
  'component.runFlow.severity.warning': '告警', // 告警級別
  'component.runFlow.status.cancelRequested': '請求取消', // 运行流請求取消狀態
  'component.runFlow.status.cancelled': '已取消', // 运行流已取消狀態
  'component.runFlow.status.degraded': '部分降級', // 运行流降級狀態
  'component.runFlow.status.failed': '失敗', // 运行流失敗狀態
  'component.runFlow.status.fallback': '降級回退', // 运行流回退狀態
  'component.runFlow.status.pending': '等待中', // 运行流等待狀態
  'component.runFlow.status.running': '运行中', // 运行流运行狀態
  'component.runFlow.status.skipped': '已跳過', // 运行流已跳過狀態
  'component.runFlow.status.success': '成功', // 运行流成功狀態
  'component.runFlow.status.timeout': '超時', // 运行流超時狀態
  'component.runFlow.status.unknown': '未知', // 运行流未知狀態
  'component.runFlow.summary.dataSources': '數據源', // 數據源數量
  'component.runFlow.summary.elapsed': '總耗時', // 运行流總耗時
  'component.runFlow.summary.failedAttempts': '失敗尝試', // 失敗尝試次數
  'component.runFlow.summary.fallbackCount': '降級回退/重試', // 回退重試次數
  'component.runFlow.summary.generatedAt': '生成時間', // 运行流生成時間
  'component.runFlow.summary.model': '模型', // 模型標识
  'component.runFlow.summary.task': 'Task', // 任務標识
  'component.runFlow.summary.trace': 'Trace', // 追踪標识
  'component.runFlow.taskDrawerTitle': '{stock} 运行流', // 任務运行流抽屉標題
  'component.runFlow.title': '數據流與信息流', // 运行流主標題
  'component.runFlow.valueUnavailable': '未記錄', // 运行流值不可用
  // component.stockSearch.*
  'component.stockSearch.placeholder': '輸入股票代碼或名稱', // 股票搜尋框默認占位符
  // component.taskPanel.*
  'component.taskPanel.cancelRequested': '請求取消', // 任務請求取消狀態
  'component.taskPanel.cancelRequestedAria': '任務請求取消', // 請求取消无障碍標簽
  'component.taskPanel.cancelled': '已取消', // 任務已取消狀態
  'component.taskPanel.diagnostics': '运行诊断', // 运行诊断按鈕
  'component.taskPanel.openRunFlow': '查看运行流', // 查看运行流按鈕
  'component.taskPanel.openRunFlowAria': '查看 {stock} 运行流', // 查看运行流无障碍標簽
  'component.taskPanel.pending': '等待中', // 任務等待中狀態
  'component.taskPanel.pendingAria': '任務等待中', // 任務等待中无障碍標簽
  'component.taskPanel.pendingTasks': '{count} 等待中', // 等待中任務數量
  'component.taskPanel.processing': '分析中', // 任務分析中狀態
  'component.taskPanel.processingAria': '任務進行中', // 任務進行中无障碍標簽
  'component.taskPanel.processingTasks': '{count} 進行中', // 進行中任務數量
  'component.taskPanel.statusAria': '任務狀態：{status}', // 任務狀態无障碍標簽
  'component.taskPanel.title': '分析任務', // 任務面板標題

  // ---- 第 6 类 登录/注册 auth ----
  'auth.login.adminLogin': '管理员登入', // 管理员登入標題
  'auth.login.adminPassword': '管理员密碼', // 管理员密碼標簽
  'auth.login.confirmPassword': '確認密碼', // 確認密碼標簽
  'auth.login.confirmPasswordPlaceholder': '再次確認管理员密碼', // 確認密碼占位符
  'auth.login.hidePassword': '隱藏密碼', // 隱藏密碼按鈕提示
  'auth.login.loginDescription': '訪問 HRS 量化决策引擎需要有效的身份凭證。', // 登入頁描述
  'auth.login.loginFailed': '登入失敗', // 登入失敗提示
  'auth.login.loginPassword': '登入密碼', // 登入密碼標簽
  'auth.login.loginPasswordPlaceholder': '請輸入密碼', // 登入密碼占位符
  'auth.login.loginSubmit': '授權進入工作臺', // 登入提交按鈕
  'auth.login.loginSubmitting': '正在建立連接...', // 登入提交中狀態
  'auth.login.pageTitle': '登入 - HRS', // 登入頁標題
  'auth.login.passwordMismatch': '两次輸入的密碼不一致', // 密碼不一致提示
  'auth.login.passwordRequired': '請輸入密碼', // 密碼必填校驗提示
  'auth.login.setupDescription': '首次啟用認證，請為系統工作臺設定管理员密碼。', // 初始密碼設定描述
  'auth.login.setupFailed': '配置失敗', // 初始設定失敗提示
  'auth.login.setupPasswordPlaceholder': '請設定 6 位以上密碼', // 初始密碼占位符
  'auth.login.setupSubmit': '完成設定並登入', // 初始設定提交按鈕
  'auth.login.setupSubmitting': '初始化中...', // 初始設定提交中狀態
  'auth.login.setupTitle': '設定初始密碼', // 初始密碼設定標題
  'auth.login.showPassword': '顯示密碼', // 顯示密碼按鈕提示
  'auth.login.username': '帳號', // 帳號標簽
  'auth.login.usernamePlaceholder': '請輸入帳號', // 帳號占位符
  'auth.login.usernameRequired': '請輸入帳號', // 帳號必填校驗提示
  'auth.login.validationFailed': '驗證未通過', // 驗證失敗提示

  // ---- 第 7 类 页面 ----
  // alerts.*
  'alerts.pageTitle': '告警中心 - HRS', // 告警頁文件標題
  // chat.*
  'chat.agentBackendUnavailableTitle': '目前問股方式不可用', // 問股方式不可用標題
  'chat.agentModeDisabled': 'Agent 模式尚未啟用，請前往 Agent 設定啟用並儲存後再試。', // Agent 模式未啟用提示
  'chat.agentPlatformUnsupported': 'Codex 本地 Agent 目前不支援原生 Windows，請改用預設模型問股，或在支援的系統上运行 HRS 後端。', // 平臺不支援提示
  'chat.analysisStopped': '本次分析已停止，後臺任務也已結束。', // 分析已停止提示
  'chat.analysisTimedOut': '本次分析已超時並結束，請縮小問題範圍後重試。', // 分析已超時提示
  'chat.codexBackendBadge': 'Codex Agent · 實驗', // Codex Agent 徽標
  'chat.codexChangeBackend': '切換問股方式', // 切換問股方式按鈕
  'chat.codexLimitedMessage': '可讀取已儲存的分析上下文和回測匯總；即時行情、新聞、市场热點、技術指標重算、個股回測明細和持倉查询請使用預設模型。', // Codex 可用範圍消息
  'chat.codexLimitedTitle': 'Codex 目前可用範圍', // Codex 可用範圍標題
  'chat.codexUnavailableMessage': '目前設備的 Codex 基础環境暫不满足問股要求，請前往 Agent 設定检查安装和單 Agent 配置。', // Codex 不可用消息
  'chat.defaultBackendBadge': '預設模型', // 預設模型徽標
  'chat.defaultUnavailableMessage': '預設模型問股目前不可用，請前往 Agent 設定检查模型配置。', // 預設模型不可用消息
  'chat.emptyDescriptionCodex': '輸入「分析 600519」或「歷史分析整體表现如何」，Codex 將基於已儲存的分析上下文和回測匯總回答。', // Codex 問股空狀態描述
  'chat.emptyDescriptionDefault': '輸入「分析 600519」或「茅臺现在能买吗」，AI 將調用即時數據工具為您生成决策報告。', // 預設問股空狀態描述
  'chat.introCodex': '使用已儲存的分析上下文和回測匯總，向 Codex 询問個股。', // Codex 問股引導文案
  'chat.introDefault': '向 AI 询問個股分析，获取基於技能視角的交易建议與即時决策報告。', // 預設問股引導文案
  'chat.openAgentSettings': '前往 Agent 設定', // 前往 Agent 設定按鈕
  'chat.recheckAgentStatus': '重新检查', // 重新检查按鈕
  'chat.statusCheckingMessage': '這裡只检查環境是否允許尝試，不會調用模型或讀取股票數據。', // 正在確認狀態消息
  'chat.statusCheckingTitle': '正在確認問股运行環境', // 正在確認狀態標題
  'chat.statusUnavailableMessage': '目前无法確認問股运行環境，因此暫不發送。你可以手動重新检查，問題內容不會丢失。', // 狀態不可用消息
  'chat.statusUnavailableTitle': '暫時无法讀取問股运行狀態', // 狀態不可用標題
  'chat.stopAnalysis': '停止分析', // 停止分析按鈕
  'chat.stopRequestFailed': '停止請求未送达，分析仍在繼續。請再次停止或稍後重試。', // 停止請求失敗提示
  'chat.stoppingAnalysis': '正在停止…', // 正在停止狀態
  // decisionSignals.*
  'decisionSignals.action': '動作', // 信號動作標簽
  'decisionSignals.active': '有效', // 有效信號狀態
  'decisionSignals.activeOnly': '預設展示 active 信號', // 仅展示有效信號說明
  'decisionSignals.allActions': '全部動作', // 全部動作篩選
  'decisionSignals.allMarkets': '全部市场', // 全部市场篩選
  'decisionSignals.allPhases': '全部阶段', // 全部阶段篩選
  'decisionSignals.allProfiles': '全部風格', // 全部風格篩選
  'decisionSignals.allSources': '全部来源', // 全部来源篩選
  'decisionSignals.allStatuses': '全部狀態', // 全部狀態篩選
  'decisionSignals.archive': '归檔', // 归檔按鈕
  'decisionSignals.archiveConfirm': '確認將這条信號归檔吗？归檔後不會再作為目前 active 建议展示。', // 归檔確認提示
  'decisionSignals.archived': '已归檔', // 已归檔狀態
  'decisionSignals.catalystSummary': '催化', // 催化因素摘要
  'decisionSignals.close': '關閉信號', // 關閉信號按鈕
  'decisionSignals.closeConfirm': '確認關閉這条信號吗？關閉表示你不再跟踪這条建议。', // 關閉信號確認
  'decisionSignals.closed': '已關閉', // 已關閉狀態
  'decisionSignals.confidence': '置信度', // 信號置信度
  'decisionSignals.confirmStatusTitle': '更新信號狀態', // 狀態更新弹窗標題
  'decisionSignals.createdAt': '建立時間', // 信號建立時間
  'decisionSignals.dataQuality': '數據质量', // 數據质量標簽
  'decisionSignals.description': '按股票、阶段、来源和狀態查询結構化 AI 建议，並保留風險與數據质量上下文。', // AI 建议頁面描述
  'decisionSignals.detailTitle': '信號詳情', // 信號詳情標題
  'decisionSignals.directionExpected': '預期方向', // 預期方向標簽
  'decisionSignals.emptyDescription': '完成一次普通個股分析後，系統會從報告中沉淀可查询的結構化建议。', // 信號空狀態描述
  'decisionSignals.emptyTitle': '暫无决策信號', // 信號空狀態標題
  'decisionSignals.entryRange': '入场區間', // 入场區間標簽
  'decisionSignals.errorTitle': '决策信號載入失敗', // 信號載入失敗標題
  'decisionSignals.evidence': '證據', // 證據標簽
  'decisionSignals.expired': '已過期', // 已過期狀態
  'decisionSignals.expiresAt': '過期時間', // 過期時間標簽
  'decisionSignals.feedback.not_useful': '无用', // 无用反馈選項
  'decisionSignals.feedback.useful': '有用', // 有用反馈選項
  'decisionSignals.feedbackNone': '暫无反馈', // 无反馈狀態
  'decisionSignals.feedbackTitle': '用戶反馈', // 用戶反馈標題
  'decisionSignals.filter': '篩選', // 篩選按鈕
  'decisionSignals.horizon': '週期', // 持倉週期標簽
  'decisionSignals.horizon.10d': '10 日', // 10 日週期
  'decisionSignals.horizon.1d': '1 日', // 1 日週期
  'decisionSignals.horizon.3d': '3 日', // 3 日週期
  'decisionSignals.horizon.5d': '5 日', // 5 日週期
  'decisionSignals.horizon.intraday': '盘中', // 盘中週期
  'decisionSignals.horizon.long': '长期', // 长期週期
  'decisionSignals.horizon.swing': '波段', // 波段週期
  'decisionSignals.invalidate': '標記失效', // 標記失效按鈕
  'decisionSignals.invalidateConfirm': '確認將這条信號標記為失效吗？失效後不會再作為目前 active 建议展示。', // 標記失效確認
  'decisionSignals.invalidated': '已失效', // 已失效狀態
  'decisionSignals.invalidation': '失效条件', // 信號失效条件
  'decisionSignals.latestButton': '查询最新', // 查询最新信號按鈕
  'decisionSignals.latestDescription': '讀取目前查看股票的最新 active 信號。', // 查询最新說明
  'decisionSignals.latestInput': '最新股票代碼', // 最新股票代碼輸入標簽
  'decisionSignals.latestPlaceholder': '例如 600519、HK00700、AAPL', // 最新股票代碼占位符
  'decisionSignals.latestTitle': '按股票查询最新信號', // 按股票查询標題
  'decisionSignals.market': '市场', // 市场標簽
  'decisionSignals.market.cn': 'A 股', // A 股市场
  'decisionSignals.market.hk': '港股', // 港股市场
  'decisionSignals.market.jp': '日股', // 日股市场
  'decisionSignals.market.kr': '韩股', // 韩股市场
  'decisionSignals.market.tw': '臺股', // 臺股市场
  'decisionSignals.market.us': '美股', // 美股市场
  'decisionSignals.marketPhase': '阶段', // 市场阶段標簽
  'decisionSignals.marketPhase.closing_auction': '集合竞价', // 集合竞价阶段
  'decisionSignals.marketPhase.intraday': '盘中', // 盘中阶段
  'decisionSignals.marketPhase.lunch_break': '午間休市', // 午間休市阶段
  'decisionSignals.marketPhase.non_trading': '非交易時段', // 非交易時段
  'decisionSignals.marketPhase.postmarket': '盘後', // 盘後阶段
  'decisionSignals.marketPhase.premarket': '盘前', // 盘前阶段
  'decisionSignals.marketPhase.unknown': '未知阶段', // 未知阶段
  'decisionSignals.metadata': '元數據', // 元數據標簽
  'decisionSignals.noLatestDescription': '该股票目前沒有 active 信號，或信號已過期。', // 无最新信號說明
  'decisionSignals.noLatestTitle': '暫无最新有效信號', // 无最新信號標題
  'decisionSignals.noOutcomes': '暫无後驗結果', // 无後驗結果提示
  'decisionSignals.noReviewedStatsDescription': '目前已有 AI 建议時，也可能还沒有形成可統計的後驗復盘結果。', // 无復盘樣本說明
  'decisionSignals.noReviewedStatsTitle': '暫无已復盘樣本', // 无復盘樣本標題
  'decisionSignals.noStatsDescription': '触發一次信號後驗計算後，這裡會顯示命中、未命中和无法评估統計。', // 无後驗統計說明
  'decisionSignals.noStatsTitle': '暫无後驗統計', // 无後驗統計標題
  'decisionSignals.outcome.hit': '命中', // 命中後驗結果
  'decisionSignals.outcome.miss': '未命中', // 未命中後驗結果
  'decisionSignals.outcome.neutral': '中性', // 中性後驗結果
  'decisionSignals.outcome.unable': '无法评估', // 无法评估後驗結果
  'decisionSignals.outcomes': '後驗結果', // 後驗結果標簽
  'decisionSignals.pageTitle': 'AI 建议 - HRS', // AI 建议頁文檔標題
  'decisionSignals.planQuality': '計划质量', // 計划质量標簽
  'decisionSignals.planQuality.complete': '完整', // 完整計划质量
  'decisionSignals.planQuality.minimal': '最小', // 最小計划质量
  'decisionSignals.planQuality.partial': '部分', // 部分計划质量
  'decisionSignals.planQuality.unknown': '未知', // 未知計划质量
  'decisionSignals.portfolioColumn': 'AI 建议', // 持倉 AI 建议列名
  'decisionSignals.portfolioEmpty': '-', // 持倉 AI 建议空值
  'decisionSignals.portfolioLoading': '載入中', // 持倉 AI 建议載入中
  'decisionSignals.portfolioPartialWarning': 'AI 建议只載入了部分數據：{message}', // 持倉 AI 建议部分載入警告
  'decisionSignals.portfolioWarningTitle': 'AI 建议降級', // 持倉 AI 建议降級標題
  'decisionSignals.pricePlan': '价格計划', // 价格計划標簽
  'decisionSignals.profile': '風格', // 决策風格標簽
  'decisionSignals.profile.aggressive': '进取', // 进取風格
  'decisionSignals.profile.balanced': '均衡', // 均衡風格
  'decisionSignals.profile.conservative': '保守', // 保守風格
  'decisionSignals.profile.unknown': '未知', // 未知風格
  'decisionSignals.profileCalibrationAverageReturn': '標的平均區間漲跌', // 風格校準平均漲跌
  'decisionSignals.profileCalibrationBreakdownLabel': '細分統計方式', // 細分統計標簽
  'decisionSignals.profileCalibrationByAction': '按建议動作', // 按動作細分
  'decisionSignals.profileCalibrationByHorizon': '按復盘週期', // 按週期細分
  'decisionSignals.profileCalibrationCompletedShort': '已完成 {count}', // 已完成數量
  'decisionSignals.profileCalibrationDescription': '這些數據来自歷史後驗復盘，只用於描述，不代表某种風格更優，也不構成投資建议。', // 風格校準說明
  'decisionSignals.profileCalibrationHitRate': '命中率', // 風格校準命中率
  'decisionSignals.profileCalibrationInsufficient': '樣本不足，仅供观察。', // 樣本不足提示
  'decisionSignals.profileCalibrationMae': '最大不利波動', // 最大不利波動指標
  'decisionSignals.profileCalibrationMaeDescription': '最大不利波動表示復盘期間相對起始价最不利的一次波動，不代表未来風險上限。', // 最大不利波動說明
  'decisionSignals.profileCalibrationMissRate': '未命中率', // 未命中率
  'decisionSignals.profileCalibrationNoBreakdownSamples': '暫无可观察的細分樣本。', // 无細分樣本提示
  'decisionSignals.profileCalibrationSampleCounts': '已完成 {completed} / 總评估 {total}', // 樣本數量統計
  'decisionSignals.profileCalibrationThreshold': '每個分組至少需要 {count} 個已完成樣本才展示表现指標。', // 展示阈值說明
  'decisionSignals.profileCalibrationTitle': '决策風格歷史表现', // 風格校準標題
  'decisionSignals.profileCalibrationUnableRate': '无法评估率', // 无法评估率
  'decisionSignals.profileCalibrationUnavailable': '暫无可計算結果', // 无可計算結果提示
  'decisionSignals.profileCalibrationUnknownDimension': '未知', // 未知維度
  'decisionSignals.profileCalibrationUnknownNotice': '另有 {count} 条歷史樣本缺少决策風格標記，未計入三類風格。', // 未知風格樣本提示
  'decisionSignals.reason': '理由', // 信號理由標簽
  'decisionSignals.reassessBlockedNote': '该預覽已被風控约束為非进攻展示動作。', // 重评估被阻断說明
  'decisionSignals.reassessBlockedTitle': '預覽被風控阻断', // 重评估阻断標題
  'decisionSignals.reassessPersist': '確認儲存', // 確認儲存重评估
  'decisionSignals.reassessPersistBlockedTitle': '儲存被風控阻断', // 儲存被阻断標題
  'decisionSignals.reassessPersistConfirmMessage': '服務端將基於同一份歷史報告快照重新計算，並儲存通過風控的結果。', // 儲存重评估確認文案
  'decisionSignals.reassessPersistConfirmTitle': '儲存重评估信號', // 儲存重评估確認標題
  'decisionSignals.reassessPersistedCreated': '已儲存為新的 DecisionSignal #{id}。', // 重评估新建成功提示
  'decisionSignals.reassessPersistedCreatedTitle': '重评估信號已儲存', // 重评估新建成功標題
  'decisionSignals.reassessPersistedExisting': '同一報告、風格和信號身份的 DecisionSignal #{id} 已存在，本次沒有重復建立；展示其原始服務端記錄。', // 重评估復用现有信號提示
  'decisionSignals.reassessPersistedExistingTitle': '已復用现有信號', // 重评估復用现有信號標題
  'decisionSignals.reassessPersistedRefreshed': '现有 DecisionSignal #{id} 已按存储契约完成過期續期或缺失維度补齐；原始建立来源保持不變，請以後端返回記錄為準。', // 重评估重新整理信號提示
  'decisionSignals.reassessPersistedRefreshedTitle': '重评估信號已重新整理', // 重评估重新整理信號標題
  'decisionSignals.reassessPersistedTerminalExisting': 'DecisionSignal #{id} 已處於“{status}”狀態，本次沒有新建或重新激活信號。', // 重评估终態信號提示
  'decisionSignals.reassessPersistedTerminalTitle': '现有信號保持终態', // 重评估终態信號標題
  'decisionSignals.reassessPersisting': '正在儲存', // 重评估儲存中狀態
  'decisionSignals.reassessPreview': '生成預覽', // 生成重评估預覽按鈕
  'decisionSignals.reassessProfile': '重评估風格', // 重评估風格標簽
  'decisionSignals.reassessRawFinal': '原始/最终', // 原始與最终對比標簽
  'decisionSignals.reassessSource': '来源報告 #{id}', // 重评估来源報告
  'decisionSignals.reassessTitle': '决策風格重评估預覽', // 重评估預覽標題
  'decisionSignals.reassessUnsupported': '该信號不支援重评估', // 不支援重评估提示
  'decisionSignals.reassessUnsupportedTitle': '缺少来源報告', // 不支援重评估標題
  'decisionSignals.reassessWarnings': '風控提示', // 風控提示標簽
  'decisionSignals.refresh': '重新整理', // 重新整理按鈕
  'decisionSignals.returnPct': '區間收益', // 區間收益率
  'decisionSignals.riskSummary': '風險', // 風險摘要標簽
  'decisionSignals.score': '评分', // 信號评分
  'decisionSignals.source': '来源', // 信號来源標簽
  'decisionSignals.sourceReport': '来源報告', // 来源報告標簽
  'decisionSignals.sourceReportId': '来源報告 ID', // 来源報告 ID
  'decisionSignals.sourceType.agent': 'Agent', // Agent 来源
  'decisionSignals.sourceType.alert': '告警', // 告警来源
  'decisionSignals.sourceType.analysis': '分析報告', // 分析報告来源
  'decisionSignals.sourceType.manual': '手動', // 手動来源
  'decisionSignals.sourceType.market_review': '大盤復盘', // 大盤復盘来源
  'decisionSignals.statsDescription': '基於目前後驗引擎版本統計信號表现，預設排除已归檔信號。', // 信號統計說明
  'decisionSignals.statsErrorTitle': '後驗統計載入失敗', // 統計載入失敗標題
  'decisionSignals.statsGlobalScope': '目前統計為全局已復盘 outcome 口徑，不等於目前可見信號數量，也不随目前股票過滤。', // 全局統計口徑說明
  'decisionSignals.statsHitRate': '命中率', // 命中率統計
  'decisionSignals.statsTitle': '信號表现統計', // 信號統計標題
  'decisionSignals.statsTotal': '评估數', // 评估總數
  'decisionSignals.status': '狀態', // 信號狀態標簽
  'decisionSignals.stockCode': '股票代碼', // 股票代碼標簽
  'decisionSignals.stockContextApply': '查看股票', // 應用股票上下文按鈕
  'decisionSignals.stockContextClear': '清空目前股票', // 清空股票上下文按鈕
  'decisionSignals.stockContextCurrent': '目前查看：{stock}', // 目前股票上下文
  'decisionSignals.stockContextDescription': '選擇一次股票後，最新信號和時間线會共享這個上下文。', // 股票上下文說明
  'decisionSignals.stockContextEmpty': '尚未選擇目前股票。', // 未選股票提示
  'decisionSignals.stockContextGuideDescription': '先在頁面頂部選擇目前股票，再查看最新信號和時間线。', // 股票上下文引導說明
  'decisionSignals.stockContextGuideTitle': '選擇股票查看 AI 建议', // 股票上下文引導標題
  'decisionSignals.stockContextInput': '目前股票', // 目前股票輸入標簽
  'decisionSignals.stockContextNoCandidates': '暫无可用候選，可直接輸入股票代碼或名稱。', // 无候選股票提示
  'decisionSignals.stockContextPlaceholder': '輸入股票代碼或名稱，如 600519、贵州茅臺、AAPL', // 股票上下文輸入占位符
  'decisionSignals.stockContextPopular': '热门候選', // 热门候選股票
  'decisionSignals.stockContextRecent': '最近分析', // 最近分析股票
  'decisionSignals.stockContextTitle': '目前股票', // 目前股票標題
  'decisionSignals.stopLoss': '止损', // 止损价標簽
  'decisionSignals.targetPrice': '目標价', // 目標价標簽
  'decisionSignals.timelineAlertShape': '菱形點表示 alert', // 時間线告警形狀說明
  'decisionSignals.timelineDescription': '按單支股票查看同一建议随時間變化的轨迹。', // 時間线說明
  'decisionSignals.timelineEmptyDescription': '目前時間範圍內沒有该股票的信號。', // 時間线空狀態描述
  'decisionSignals.timelineEmptyTitle': '暫无時間线信號', // 時間线空狀態標題
  'decisionSignals.timelineErrorTitle': '時間线載入失敗', // 時間线載入失敗標題
  'decisionSignals.timelineFamilyBullish': '偏多', // 偏多信號族
  'decisionSignals.timelineFamilyDefensive': '防御', // 防御信號族
  'decisionSignals.timelineFamilyNeutral': '中性', // 中性信號族
  'decisionSignals.timelineGuideDescription': '調整時間範圍、狀態或市场後，點击查询時間线應用篩選。', // 時間线引導說明
  'decisionSignals.timelineGuideTitle': '查询目前股票時間线', // 時間线引導標題
  'decisionSignals.timelineMarket': '時間线市场', // 時間线市场篩選
  'decisionSignals.timelineProfile': '時間线風格', // 時間线風格篩選
  'decisionSignals.timelineRange': '時間範圍', // 時間线範圍標簽
  'decisionSignals.timelineRange.180d': '180 天', // 180 天時間範圍
  'decisionSignals.timelineRange.30d': '30 天', // 30 天時間範圍
  'decisionSignals.timelineRange.90d': '90 天', // 90 天時間範圍
  'decisionSignals.timelineSearch': '查询時間线', // 查询時間线按鈕
  'decisionSignals.timelineSelected': '已選第 {index} 個點', // 時間线選中點提示
  'decisionSignals.timelineStatus': '時間线狀態', // 時間线狀態篩選
  'decisionSignals.timelineStatus.active': '仅有效', // 仅有效信號篩選
  'decisionSignals.timelineStatus.all': '全部歷史', // 全部歷史篩選
  'decisionSignals.timelineStockCode': '時間线股票代碼', // 時間线股票代碼標簽
  'decisionSignals.timelineStockPlaceholder': '例如 600519、HK00700、AAPL', // 時間线股票占位符
  'decisionSignals.timelineTitle': '股票信號時間线', // 時間线標題
  'decisionSignals.timelineTruncatedDescription': '仅展示最近 100 条信號，請縮小時間範圍。', // 時間线截断說明
  'decisionSignals.timelineTruncatedTitle': '時間线已截断', // 時間线截断標題
  'decisionSignals.title': 'AI 建议', // AI 建议頁面標題
  'decisionSignals.total': '共 {total} 条信號', // 信號總數
  'decisionSignals.unableReason': '无法评估原因', // 无法评估原因標簽
  'decisionSignals.viewDetailsFor': '查看 {stock} AI 建议詳情', // 查看股票建议詳情
  'decisionSignals.watchConditions': '观察条件', // 观察条件標簽
  // history.*
  'history.actionAdd': '加仓', // 加仓動作
  'history.actionAlert': '預警', // 預警動作
  'history.actionAvoid': '回避', // 回避動作
  'history.actionBuy': '买入', // 买入動作
  'history.actionHold': '持有', // 持有動作
  'history.actionReduce': '减仓', // 减仓動作
  'history.actionSell': '卖出', // 卖出動作
  'history.actionWatch': '观望', // 观望動作
  'history.analysisCount': '{count}次', // 分析次數統計
  'history.bottomReached': '已到底部', // 歷史列表到底提示
  'history.defaultEmptyDescription': '完成首次分析後，這裡會保留最近結果。', // 歷史空狀態描述
  'history.defaultEmptyTitle': '暫无歷史分析記錄', // 歷史空狀態標題
  'history.defaultTitle': '歷史分析', // 歷史分析標題
  'history.deleteRecord': '刪除 {name} 歷史記錄', // 刪除歷史記錄按鈕
  'history.itemAria': '{name} {code} 歷史記錄', // 歷史記錄項无障碍標簽
  'history.loading': '載入歷史記錄中...', // 歷史載入中狀態
  'history.selectAllHistoryAria': '全選目前已載入歷史記錄', // 全選歷史无障碍標簽
  'history.selectAllStockAria': '全選目前個股', // 全選個股无障碍標簽
  'history.sentiment': '情绪', // 情绪標簽
  // kline.*
  'kline.error': 'K 线數據載入失敗', // K 线載入失敗提示
  'kline.fullData': '全量數據', // 全量數據選項
  'kline.info.amount': '成交額', // 成交額
  'kline.info.amplitude': '振幅', // 振幅
  'kline.info.high': '最高', // 最高价
  'kline.info.low': '最低', // 最低价
  'kline.info.open': '今開', // 今日開盤价
  'kline.info.peRatioTTM': '本益比(TTM)', // 本益比TTM
  'kline.info.prevClose': '昨收', // 昨日收盤价
  'kline.info.totalMarketCap': '總市值', // 總市值
  'kline.info.turnoverRate': '換手率', // 換手率
  'kline.info.volume': '成交量', // 成交量
  'kline.loading': '正在載入 K 线數據', // K 线載入中文案
  'kline.noStockSelected': '請搜尋並選擇一只股票查看 K 线', // 未選擇股票提示
  'kline.period.120m': '120 分', // 120 分鐘週期
  'kline.period.15m': '15 分', // 15 分鐘週期
  'kline.period.1m': '分時', // 分時週期
  'kline.period.30m': '30 分', // 30 分鐘週期
  'kline.period.5d': '5日', // 5日週期
  'kline.period.5m': '5 分', // 5 分鐘週期
  'kline.period.60m': '60 分', // 60 分鐘週期
  'kline.period.daily': '日K', // 日K週期
  'kline.period.monthly': '月 K', // 月 K 週期
  'kline.period.weekly': '週 K', // 週 K 週期
  'kline.period.yearly': '年 K', // 年 K 週期
  'kline.searchPlaceholder': '輸入股票代碼、名稱、拼音或簡拼', // K 线搜尋框占位符
  'kline.title': '個股 K 线', // K 线頁面標題
  'kline.tooltip.amount': '成交額', // tooltip 成交額
  'kline.tooltip.change': '漲跌幅', // tooltip 漲跌幅
  'kline.tooltip.close': '收盤', // tooltip 收盤价
  'kline.tooltip.date': '日期', // tooltip 日期
  'kline.tooltip.dea': 'DEA', // tooltip DEA 指標
  'kline.tooltip.dif': 'DIF', // tooltip DIF 指標
  'kline.tooltip.high': '最高', // tooltip 最高价
  'kline.tooltip.kline': 'K 线', // K 线 tooltip 標簽
  'kline.tooltip.low': '最低', // tooltip 最低价
  'kline.tooltip.ma10': 'MA10', // tooltip MA10 均线
  'kline.tooltip.ma30': 'MA30', // tooltip MA30 均线
  'kline.tooltip.ma5': 'MA5', // tooltip MA5 均线
  'kline.tooltip.ma60': 'MA60', // tooltip MA60 均线
  'kline.tooltip.macd': 'MACD', // tooltip MACD 指標
  'kline.tooltip.open': '開盤', // tooltip 開盤价
  'kline.tooltip.volume': '成交量', // tooltip 成交量
  // liveNews.*
  'liveNews.channelTabs': '快訊頻道', // 頻道 Tab 的無障礙標籤
  'liveNews.dateAll': '全部日期', // 日期篩選：不限
  'liveNews.dateToday': '今天', // 日期篩選：今天
  'liveNews.dateYesterday': '昨天', // 日期篩選：昨天
  'liveNews.degradedTip': '即時來源暫不可用，目前為聚合降級資料（無頻道分類與重要級）', // 降級提示
  'liveNews.empty': '暫無快訊', // 空態：目前頻道無資料
  'liveNews.emptyDate': '該日期暫無快訊', // 空態：指定日期無資料
  'liveNews.emptyImportant': '本頻道暫無重要快訊', // 空態：重要級篩選無結果
  'liveNews.emptyKeyword': '未找到相關快訊', // 空態：關鍵詞搜尋無結果
  'liveNews.importantOnly': '只看重要的', // 重要級篩選開關
  'liveNews.importantTag': '重要', // 重要快訊標籤
  'liveNews.loadMore': '載入更多', // 載入更多按鈕
  'liveNews.loading': '正在取得最新快訊…', // 載入中文案
  'liveNews.refresh': '刷新資訊', // 手動刷新按鈕
  'liveNews.refreshing': '刷新資訊中', // 刷新按鈕載入態文案（HrsButton loadingText）
  'liveNews.searchPlaceholder': '搜尋快訊…', // 搜尋框占位符
  'liveNews.subtitle': '7x24 小時財經快訊，覆蓋要聞、A股、美股、港股、外匯、商品、債券與科技', // 頁面副標題
  'liveNews.title': '快訊中心', // 快訊中心頁面標題
  // notFound.*
  'notFound.backHome': '返回首頁', // 404 返回首頁
  'notFound.description': '抱歉，您訪問的頁面不存在或已被移動', // 404 描述
  'notFound.pageTitle': '頁面未找到 - HermesX', // 404 頁面標題
  'notFound.title': '頁面未找到', // 404 標題
  // report.*
  'report.addToWatchlist': '加入自選', // 報告加入自選按鈕
  'report.removeFromWatchlist': '從自選刪除', // 報告移除自選按鈕
  'report.watchlist': '自選', // 報告自選標簽
  // review.*
  'review.analyze': '分析', // 分析按鈕
  'review.analyzing': '分析中', // 分析中狀態
  'review.askAi': '追問 AI', // 追問 AI 按鈕
  'review.defaultStrategyDescription': '沿用系統預設分析框架', // 預設策略描述
  'review.defaultStrategyName': '預設策略', // 預設策略名稱
  'review.duplicateTask': '任務已存在', // 重復任務提示
  'review.fullReport': '完整分析報告', // 完整報告入口
  'review.goSettings': '去配置', // 跳轉設定按鈕
  'review.historyButton': '歷史記錄', // 歷史記錄按鈕
  'review.historyTrend': '歷史趨勢', // 歷史趨勢入口
  'review.inputInvalid': '輸入有誤', // 輸入无效提示
  'review.loadingReport': '載入報告中...', // 報告載入中狀態
  'review.marketRegionAll': '全部市场', // 全部市场選項
  'review.marketRegionCn': 'A 股', // A 股市场
  'review.marketRegionDefaultUnavailable': '由伺服器在提交時决定', // 市场預設值不可用說明
  'review.marketRegionDescription': '選擇本次復盘覆盖的市场，可單選或多選。', // 市场選擇說明
  'review.marketRegionHk': '港股', // 港股市场
  'review.marketRegionJp': '日股', // 日股市场
  'review.marketRegionKr': '韩股', // 韩股市场
  'review.marketRegionOneTimeHint': '仅影响本次触發，不會修改全局配置。', // 市场選擇一次性提示
  'review.marketRegionSelector': '選擇大盤復盘市场', // 市场選擇器標題
  'review.marketRegionServerDefault': '伺服器預設', // 伺服器預設市场
  'review.marketRegionTitle': '本次復盘市场', // 本次復盘市场標題
  'review.marketRegionUs': '美股', // 美股市场
  'review.marketReview': '大盤復盘', // 大盤復盘入口
  'review.marketReviewCompleted': '大盤復盘已完成', // 大盤復盘完成提示
  'review.marketReviewCompletedWithReport': '大盤復盘任務已完成，結果如下：', // 大盤復盘完成含結果
  'review.marketReviewCompletedWithoutReport': '大盤復盘任務已完成，結果已生成並按配置推送。', // 大盤復盘完成无結果展示
  'review.marketReviewFailed': '大盤復盘執行失敗。', // 大盤復盘失敗提示
  'review.marketReviewHistoryEmptyDescription': '运行大盤復盘後，這裡會集中展示歷史記錄。', // 大盤復盘歷史空狀態描述
  'review.marketReviewHistoryEmptyTitle': '暫无大盤復盘', // 大盤復盘歷史空狀態標題
  'review.marketReviewHistoryTitle': '大盤復盘歷史', // 大盤復盘歷史標題
  'review.marketReviewInProgress': '大盤復盘進行中', // 大盤復盘進行中狀態
  'review.marketReviewSubmitted': '大盤復盘已提交', // 大盤復盘已提交提示
  'review.marketReviewSubmittedWithRegion': '{message}；實际市场：{region}', // 大盤復盘提交含市场
  'review.marketReviewTimeout': '大盤復盘已超時', // 大盤復盘超時提示
  'review.marketReviewTimeoutMessage': '任務长時間未返回最终結果，請在任務列表/歷史中查看。', // 大盤復盘超時說明
  'review.marketReviewUnknownStatus': '大盤復盘狀態異常', // 大盤復盘狀態異常提示
  'review.notify': '推送通知', // 推送通知選項
  'review.pageTitle': '每日選股分析 - HRS', // 首頁文檔標題
  'review.placeholder': '輸入股票代碼或名稱，如 600519、贵州茅臺、AAPL', // 股票輸入框占位符
  'review.progressActive': '進行中', // 任務進行中狀態
  'review.reanalyze': '重新分析', // 重新分析按鈕
  'review.rerunMarketReview': '重新復盘', // 重新復盘按鈕
  'review.setupIncomplete': '基础配置未完成', // 配置未完成提示
  'review.setupMissingGeneric': '还缺少基础配置，完成後即可開始最小可用分析。', // 缺少配置通用提示
  'review.setupMissingWithLabels': '还缺少 {labels}，完成後即可開始最小可用分析。', // 缺少配置含標簽提示
  'review.startAnalysisDescription': '輸入股票代碼進行分析，或從左側選擇歷史報告查看。', // 開始分析描述
  'review.startAnalysisTitle': '開始分析', // 開始分析標題
  'review.strategy': '策略', // 策略標簽
  'review.submitMarketReview': '提交中', // 大盤復盘提交中狀態
  'review.taskStatus': '任務狀態：{status}（{progress}）', // 任務狀態文案
  'review.taskStatusWithRegion': '任務狀態：{status}（{progress}）；實际市场：{region}', // 任務狀態含市场
  'review.unknownTaskStatus': '收到未知任務狀態：{status}', // 未知任務狀態提示
  // routeError.*
  'routeError.backHome': '返回首頁', // 路由錯誤返回首頁
  'routeError.description': '目前頁面資源或組件未能正常載入，可能是網絡中断或頁面版本已更新。請重新載入頁面，或返回首頁後再試。', // 路由錯誤描述
  'routeError.reload': '重新載入頁面', // 路由錯誤重新載入
  'routeError.title': '頁面載入失敗', // 路由錯誤標題
  // sector.*
  'sector.tab.board': '板塊', // 板塊分析一級 TAB：板塊
  'sector.tab.boardConcept': '概念板塊', // 「板塊」二級 TAB：概念板塊
  'sector.tab.boardIndustry': '行業板塊', // 「板塊」二級 TAB：行業板塊
  'sector.tab.cloudConcept': '概念雲圖', // 「雲圖」二級 TAB：概念雲圖
  'sector.tab.cloudEtf': 'ETF 雲圖', // 「雲圖」二級 TAB：ETF 雲圖
  'sector.tab.cloudMap': '雲圖', // 板塊分析一級 TAB：雲圖
  'sector.tab.cloudSector': '板塊雲圖', // 「雲圖」二級 TAB：板塊雲圖
  'sector.tab.cloudStock': '個股雲圖', // 「雲圖」二級 TAB：個股雲圖
  'sector.tab.fund': '資金', // 板塊分析一級 TAB：資金
  // settings.*
  'settings.actionSuccess': '操作成功', // 設定操作成功提示
  'settings.activePanelDescription': '使用統一字段卡片維護目前分類的系統配置。', // 目前分類配置說明
  'settings.activePanelTitle': '目前分類配置項', // 目前分類配置標題
  'settings.agentBackendCanTry': '可以尝試', // 可以尝試狀態
  'settings.agentBackendCanTryDescription': '基础環境检查已通過。你可以回到問股頁直接提問，首次問題會進行真實執行。', // 可以尝試說明
  'settings.agentBackendCodexLabel': 'Codex Agent', // Codex Agent 標簽
  'settings.agentBackendCodexNotice': 'Codex 目前只能讀取已儲存的分析上下文和回測匯總。即時行情、新聞、市场热點、技術指標重算、個股回測明細和持倉工具暫不開放；需要這些能力時，請選擇“預設模型”。點击停止後，本次 Codex 和工具任務會一起結束。此選擇只影响問股 Chat；Multi Agent、Deep Research、普通報告和定時任務保持原路徑。Codex 不是离线模型，問題和工具結果可能由 Codex 配置的服務處理。', // Codex 本地 Agent 說明
  'settings.agentBackendCodexNoticeTitle': 'Codex 本地 Agent（實驗）', // Codex 本地 Agent 標題
  'settings.agentBackendCommandNotFound': '运行 HRS 的設備找不到 Codex。請在该設備安装 Codex，並確保 HRS 後端进程可以從 PATH 找到它。', // Codex 未找到提示
  'settings.agentBackendDefaultLabel': '預設模型', // 預設模型標簽
  'settings.agentBackendEnableMode': '啟用 Agent 模式', // 啟用 Agent 模式按鈕
  'settings.agentBackendErrorCode': '錯誤代碼', // 錯誤代碼標簽
  'settings.agentBackendExperimental': '實驗功能', // 實驗功能標簽
  'settings.agentBackendInvalidTimeout': 'Codex 必須設定大於 0 的 Agent 整體時限，確保成功、失敗、超時或停止都能明確結束。', // 超時設定无效提示
  'settings.agentBackendModeDisabled': 'Agent 模式目前未啟用。點击下方按鈕修改頁面草稿，然後儲存設定後再使用問股。', // Agent 模式未啟用提示
  'settings.agentBackendModeDisabledTitle': '需要啟用 Agent 模式', // 需啟用 Agent 模式標題
  'settings.agentBackendNeedsAction': '需要處理', // 需要處理狀態
  'settings.agentBackendPlatformUnsupported': 'Codex 本地 Agent 目前不支援原生 Windows。可在 macOS、Linux，或讓 HRS 後端完整运行於 WSL 後使用。', // 平臺不支援提示
  'settings.agentBackendRefresh': '重新整理狀態', // 重新整理狀態按鈕
  'settings.agentBackendRefreshing': '正在检查', // 正在检查狀態
  'settings.agentBackendSectionDescription': '在同一個問股頁面中選擇預設模型配置或本機 Codex，並在儲存前預覽目前草稿是否可运行。', // 問股生成方式說明
  'settings.agentBackendSectionTitle': '問股生成方式', // 問股生成方式標題
  'settings.agentBackendSingleOnly': 'Codex 本地 Agent 目前只支援單 Agent 問股。此操作只修改頁面草稿，仍需點击儲存。', // 仅支援單 Agent 提示
  'settings.agentBackendSingleOnlyTitle': '需要切換為單 Agent', // 需切換單 Agent 標題
  'settings.agentBackendStatus': '問股运行狀態', // 問股运行狀態標題
  'settings.agentBackendStatusDescription': '這裡只检查目前設定、本機 Codex 命令和問股所需协议是否允許尝試啟動；不會登入、調用模型或讀取股票數據。真正是否能完成問股，會在你發送問題時確認。', // 問股运行狀態說明
  'settings.agentBackendTechnicalDetails': '技术詳情', // 技术詳情標簽
  'settings.agentBackendUnavailableDescription': '目前問股方式暫不可用，請检查設定後重試。', // 不可用說明
  'settings.agentBackendUseSingle': '切換為單 Agent', // 切換為單 Agent 按鈕
  'settings.agentBackendVersion': '版本', // 版本標簽
  'settings.agentSettings': 'Agent 設定', // Agent 設定入口
  'settings.alphaSift': 'AlphaSift 選股', // AlphaSift 選股標題
  'settings.alphaSiftDescription': '啟用內置 AlphaSift 實驗性质選股能力。', // AlphaSift 選股說明
  'settings.alphaSiftDisabled': '選股未開啟', // 選股未開啟狀態
  'settings.alphaSiftEnabled': '選股已開啟', // 選股已開啟狀態
  'settings.alphaSiftRisk': '實驗功能與風險提示：選股結果仅用於研究和辅助判断，不構成投資建议；市场有風險，交易决策和损益由使用者自行承担。', // AlphaSift 風險提示
  'settings.alphaSiftSummary': '開啟後左側導航會顯示“選股”；策略和候選生成来自 AlphaSift，HRS 會补充行情、基本面和新聞上下文。', // AlphaSift 概要說明
  'settings.authCurrentPassword': '目前管理员密碼', // 目前管理员密碼標簽
  'settings.authDescription': '管理管理员密碼認證，保护您的系統配置安全。', // 認證設定說明
  'settings.authDisabled': '未啟用', // 認證未啟用狀態
  'settings.authEnabled': '已啟用', // 認證已啟用狀態
  'settings.authFailure': '認證設定失敗', // 認證設定失敗提示
  'settings.authHelperDefault': '管理员認證可保护 Web 設定頁及 API 接口，防止未經授權的訪問。', // 認證預設幫助說明
  'settings.authHelperEnabled': '管理员認證已啟用。如需更新密碼，請使用下方的“修改密碼”功能。', // 認證已啟用幫助說明
  'settings.authHelperNoPassword': '系統尚未設定密碼。啟用認證前請先設定初始管理员密碼，設定後請妥善保管。', // 无密碼幫助說明
  'settings.authHelperPasswordRetained': '系統已保留之前設定的管理员密碼。輸入目前密碼即可快速重新啟用認證。', // 密碼已保留幫助說明
  'settings.authHelperTurnOff': '若目前登入會话仍有效，可直接關閉認證；若會话已失效，請輸入目前管理员密碼。', // 關閉認證幫助說明
  'settings.authPasswordHintOff': '關閉認證前可能需要驗證身份', // 關閉認證提示
  'settings.authPasswordHintRetained': '輸入旧密碼以重新激活認證', // 重新激活認證提示
  'settings.authPasswordPlaceholder': '請輸入目前密碼', // 認證密碼占位符
  'settings.authRequiredPassword': '設定新密碼是必填項', // 新密碼必填提示
  'settings.authSetPassword': '設定管理员密碼', // 設定管理员密碼按鈕
  'settings.authSetPasswordPlaceholder': '輸入新密碼 (至少 6 位)', // 新密碼占位符
  'settings.authStatus': '管理员認證', // 管理员認證狀態
  'settings.authSuccessDisabled': '認證已關閉', // 認證關閉成功提示
  'settings.authSuccessUpdated': '認證設定已更新', // 認證更新成功提示
  'settings.authTitle': '認證與登入保护', // 認證設定標題
  'settings.categoryNavDescription': '按模塊整理系統設定與認證能力。', // 分類導航說明
  'settings.categoryNavTitle': '配置分類', // 配置分類標題
  'settings.changePasswordConfirm': '確認新密碼', // 確認新密碼標簽
  'settings.changePasswordConfirmPlaceholder': '再次輸入新密碼', // 確認新密碼占位符
  'settings.changePasswordCurrent': '目前密碼', // 目前密碼標簽
  'settings.changePasswordCurrentPlaceholder': '輸入目前密碼', // 目前密碼占位符
  'settings.changePasswordDescription': '更新目前管理员登入密碼。修改成功後，後續登入請使用新密碼。', // 修改密碼說明
  'settings.changePasswordFailure': '修改失敗', // 修改密碼失敗提示
  'settings.changePasswordNew': '新密碼', // 新密碼標簽
  'settings.changePasswordNewHint': '至少 6 位。', // 新密碼要求提示
  'settings.changePasswordNewPlaceholder': '輸入新密碼', // 新密碼占位符
  'settings.changePasswordRequiredCurrent': '請輸入目前密碼', // 目前密碼必填提示
  'settings.changePasswordRequiredNew': '請輸入新密碼', // 新密碼必填提示
  'settings.changePasswordSave': '儲存新密碼', // 儲存新密碼按鈕
  'settings.changePasswordShort': '新密碼至少 6 位', // 密碼過短提示
  'settings.changePasswordSuccess': '修改成功', // 修改密碼成功提示
  'settings.changePasswordSuccessMessage': '管理员密碼已更新。', // 修改密碼成功消息
  'settings.changePasswordTitle': '修改密碼', // 修改密碼標題
  'settings.checkDesktopUpdate': '检查更新', // 检查桌面端更新按鈕
  'settings.checkingDesktopUpdate': '检查中...', // 检查更新中狀態
  'settings.configBackup': '配置備份', // 配置備份標題
  'settings.configBackupDescription': '匯出目前已儲存的 .env 備份，或從備份文件恢復配置。匯入會覆盖備份中出现的键並立即重載。', // 配置備份說明
  'settings.currentCategoryEmptyDescription': '目前分類沒有可編輯字段；可切換左側分類繼續查看其它系統配置。', // 目前分類空狀態描述
  'settings.currentCategoryEmptyTitle': '目前分類下暫无配置項', // 目前分類空狀態標題
  'settings.desktopCheckError': '检查更新失敗', // 桌面端检查更新失敗
  'settings.desktopChecking': '正在检查更新', // 桌面端检查更新中
  'settings.desktopCurrentNoStatus': '目前尚无更新狀態，應用啟動後會在後臺自動检查。', // 桌面端无更新狀態
  'settings.desktopDownload': '前往下載', // 前往下載按鈕
  'settings.desktopDownloaded': '更新已下載', // 更新已下載狀態
  'settings.desktopDownloading': '正在下載更新', // 更新下載中狀態
  'settings.desktopInstall': '重新啟動安装', // 重新啟動安装按鈕
  'settings.desktopInstalling': '正在安装更新', // 安装更新中狀態
  'settings.desktopLatest': '最新版本', // 最新版本標簽
  'settings.desktopManualUnsupported': '目前桌面端不支援自動安装更新，請前往發佈頁手動更新。', // 不支援自動更新提示
  'settings.desktopUpToDate': '已是最新版本', // 已是最新版本狀態
  'settings.desktopUpToDateMessage': '目前桌面端已是最新版本。', // 已是最新版本消息
  'settings.desktopUpdate': '桌面端更新', // 桌面端更新標題
  'settings.desktopUpdateAvailable': '發现新版本', // 發现新版本提示
  'settings.desktopUpdateCheckingMessage': '正在检查 GitHub Releases 中是否有可用新版本。', // 检查更新中消息
  'settings.desktopUpdateDescription': '啟動後會自動检查 GitHub Releases 最新正式版；Windows 安装版會後臺下載更新，確認後静默重新啟動安装。', // 桌面端更新說明
  'settings.desktopUpdateDownloadedMessage': '新版本已下載，可重新啟動應用完成安装。', // 更新已下載消息
  'settings.desktopUpdateDownloadingMessage': '正在後臺下載桌面端更新{percent}。', // 更新下載中消息
  'settings.desktopUpdateErrorMessage': '无法完成更新检查，請稍後重試。', // 更新检查錯誤消息
  'settings.desktopUpdateInstallingMessage': '正在重新啟動並安装更新。', // 安装更新消息
  'settings.desktopUpdateMessage': '目前 {current}，最新 {latest}。{message}', // 更新狀態消息
  'settings.desktopUpdateReleaseMessage': '可前往 GitHub Releases 下載更新。', // 發佈頁下載消息
  'settings.diagnosticHintDesktop': '請查看並提供桌面端日誌 desktop.log，同時补充 release 版本、Windows 版本和触發入口。', // 桌面端诊断提示
  'settings.diagnosticHintWeb': '請查看瀏覽器開發者工具控製臺與後端日誌，並补充 release 版本、瀏覽器版本和触發入口。', // Web 端诊断提示
  'settings.disableAlphaSift': '關閉選股', // 關閉選股按鈕
  'settings.disableAuth': '關閉認證', // 關閉認證按鈕
  'settings.disabledAlphaSiftSuccess': '已關閉 AlphaSift 選股。', // 關閉選股成功提示
  'settings.disabledAuthBackupWarning': '目前 Web 端未開啟管理员鉴權，匯出/匯入 `.env` 備份功能已停用；請先將 `ADMIN_AUTH_ENABLED` 設為 `true` 並完成管理员登入後再使用。', // 未啟用認證時備份警告
  'settings.disablingAlphaSift': '關閉中...', // 關閉選中狀態
  'settings.enableAlphaSift': '開啟選股', // 開啟選股按鈕
  'settings.enableAuth': '開啟認證', // 開啟認證按鈕
  'settings.enabledAlphaSiftSuccess': '已開啟 AlphaSift 選股。', // 開啟選股成功提示
  'settings.enablingAlphaSift': '開啟中...', // 開啟選中狀態
  'settings.envDockerNote': 'Docker 部署中，`--env-file` / Compose `env_file` 只會在啟動時註入環境變量；此處匯出/匯入的是後端目前活跃的 `.env` 文件。若需要讓 WebUI 儲存值随容器重建保留，請將 `ENV_FILE` 指向 `/app/data/runtime.env` 等可寫數據卷文件，並避免啟動環境裡繼續保留同名旧值。', // Docker 環境變量說明
  'settings.envExportNote': '匯出內容仅包含目前已儲存配置，不包含頁面上尚未儲存的本地草稿。', // 匯出說明
  'settings.envExported': '已匯出目前已儲存的 .env 備份。', // 匯出成功提示
  'settings.envImported': '已匯入 .env 備份並重新載入配置。', // 匯入成功提示
  'settings.envImportedRefreshFailedMessage': '備份已匯入，但重新載入配置失敗，請手動重載頁面。', // 匯入後重新整理失敗消息
  'settings.envImportedRefreshFailedRaw': 'Env import succeeded but config refresh failed', // 匯入後重新整理失敗原始信息
  'settings.envImportedRefreshFailedTitle': '配置已匯入但重新整理失敗', // 匯入後重新整理失敗標題
  'settings.exportEnv': '匯出 .env', // 匯出 .env 按鈕
  'settings.exportingEnv': '匯出中...', // 匯出中狀態
  'settings.fallbackVersionWarning': '目前建置未提供發佈版本，頁面顯示為 development；可結合代碼版本和建置時間確認静態資源是否已更新。', // 版本回退警告
  'settings.fieldAddKey': '添加 Key', // 添加 Key 按鈕
  'settings.fieldDelete': '刪除', // 刪除字段按鈕
  'settings.fieldSensitiveHint': '敏感內容預設隱藏，可點击眼睛圖標查看明文。', // 敏感字段提示
  'settings.fieldSensitiveMultiHint': ' 支援添加多個輸入框進行增刪。', // 敏感多值字段提示
  'settings.generationBackendConcurrency': '並發 {count}', // 並發數顯示
  'settings.generationBackendFallback': '備用後端', // 備用後端標簽
  'settings.generationBackendGenerationOnly': '仅生成', // 仅生成標簽
  'settings.generationBackendHealthFailed': '检測失敗', // 检測失敗狀態
  'settings.generationBackendHealthPassed': '检測通過', // 检測通過狀態
  'settings.generationBackendHealthSkipped': '已跳過', // 已跳過狀態
  'settings.generationBackendLiteLLMDescription': '目前後端用於報告生成；問股工具調用仍沿用 LiteLLM Agent 路徑。', // LiteLLM 後端說明
  'settings.generationBackendLocalCliDescription': '本地 CLI 只用於報告和文本生成，不支援問股工具調用。', // 本地 CLI 後端說明
  'settings.generationBackendNeedsAction': '需要處理', // 需要處理狀態
  'settings.generationBackendPrimary': '主後端', // 主後端標簽
  'settings.generationBackendRefresh': '重新整理', // 重新整理按鈕
  'settings.generationBackendRefreshing': '重新整理中', // 重新整理中狀態
  'settings.generationBackendRunnable': '可尝試运行', // 可尝試运行狀態
  'settings.generationBackendSmokeFailed': '冒烟測試失敗', // 冒烟測試失敗狀態
  'settings.generationBackendSmokePassed': '冒烟測試通過', // 冒烟測試通過狀態
  'settings.generationBackendSmokePassedMessage': '生成後端冒烟測試通過。', // 冒烟測試通過消息
  'settings.generationBackendSmokeTest': 'JSON 冒烟測試', // JSON 冒烟測試按鈕
  'settings.generationBackendSmokeTesting': '測試中', // 測試中狀態
  'settings.generationBackendStatus': '生成後端狀態', // 生成後端狀態標題
  'settings.generationBackendStatusDescription': '快速检查只讀取配置，並检查本地 CLI 可執行文件是否可見；要確認真實請求是否能跑通，請运行 JSON 冒烟測試。', // 生成後端狀態說明
  'settings.generationBackendToolsSupported': '工具調用', // 工具調用支援標簽
  'settings.helpClose': '關閉配置說明', // 關閉配置說明按鈕
  'settings.helpExamples': '配置樣例', // 配置樣例標簽
  'settings.helpImpact': '影响範圍', // 影响範圍標簽
  'settings.helpNotes': '註意事項', // 註意事項標簽
  'settings.helpPurpose': '用途', // 用途標簽
  'settings.helpRelatedDocs': '相關文檔', // 相關文檔標簽
  'settings.helpTitleFallback': '配置說明', // 配置說明預設標題
  'settings.helpTooltip': '查看配置說明', // 查看配置說明提示
  'settings.helpValueNotes': '取值說明', // 取值說明標簽
  'settings.importConfirmContinue': '繼續匯入', // 繼續匯入按鈕
  'settings.importConfirmMessage': '目前頁面还有未儲存修改。繼續匯入會丢弃這些本地草稿，並立即用備份文件中的键值更新已儲存配置。', // 匯入確認消息
  'settings.importConfirmTitle': '匯入會覆盖目前草稿', // 匯入確認標題
  'settings.importEnv': '匯入 .env', // 匯入 .env 按鈕
  'settings.importingEnv': '匯入中...', // 匯入中狀態
  'settings.intelligentImport': '智能匯入', // 智能匯入標題
  'settings.intelligentImportChooseFile': '選擇文件', // 選擇文件按鈕
  'settings.intelligentImportChooseImage': '選擇圖片', // 選擇圖片按鈕
  'settings.intelligentImportClear': '清空', // 清空按鈕
  'settings.intelligentImportConfigUpdated': '配置已更新，請再次點击「合並到自選股」', // 配置已更新提示
  'settings.intelligentImportDescription': '從圖片、文件或剪貼板中提取股票代碼，並合並到自選股列表。', // 智能匯入說明
  'settings.intelligentImportFileSizeError': '文件不超過 2MB', // 文件大小錯誤提示
  'settings.intelligentImportHint': '圖片识別需預先配置 Vision 模型。建议先人工核對解析結果，再合並到自選股。', // 智能匯入提示
  'settings.intelligentImportImageSizeError': '圖片不超過 5MB', // 圖片大小錯誤提示
  'settings.intelligentImportImageTypeError': '圖片仅支援 JPG、PNG、WebP、GIF', // 圖片類型錯誤提示
  'settings.intelligentImportLoadConfigFirst': '請先載入配置後再合並', // 先載入配置提示
  'settings.intelligentImportMergeFailed': '合並儲存失敗', // 合並儲存失敗提示
  'settings.intelligentImportMergeToWatchlist': '合並到自選股', // 合並到自選股按鈕
  'settings.intelligentImportParse': '解析', // 解析按鈕
  'settings.intelligentImportParseFailed': '解析失敗', // 解析失敗提示
  'settings.intelligentImportPastePlaceholder': '或貼上 CSV/Excel 複製的文本...', // 貼上文本占位符
  'settings.intelligentImportRateLimited': '請求過於頻繁，請稍後再試', // 請求頻繁提示
  'settings.intelligentImportRecognitionFailed': '识別失敗，請重試', // 识別失敗提示
  'settings.intelligentImportReviewWarning': '建议人工逐条核對後再合並。高置信度預設勾選，中/低置信度需手動確認。', // 人工核對警告
  'settings.intelligentImportSelectionSummary': '共 {valid} 条可合並，已勾選 {checked} 条', // 選擇摘要
  'settings.intelligentImportSupportedInputs': '支援圖片、CSV/Excel 文件與剪貼板文本', // 智能匯入支援輸入類型
  'settings.intelligentImportTextSizeError': '貼上文本不超過 100KB', // 文本大小錯誤提示
  'settings.intelligentImportTimeout': '請求超時，請检查網絡後重試', // 請求超時提示
  'settings.keepAuthDisabled': '保持已關閉', // 保持已關閉按鈕
  'settings.keepAuthEnabled': '保持已開啟', // 保持已開啟按鈕
  'settings.llmAccess': 'AI 模型接入', // AI 模型接入標題
  'settings.llmAccessDescription': '統一管理模型渠道、基础地址、API Key、主模型與備選模型。', // AI 模型接入說明
  'settings.notificationSettings': '通知設定', // 通知設定標題
  'settings.notificationTest': '通知測試', // 通知測試標題
  'settings.notificationTestBody': '正文', // 通知測試正文標簽
  'settings.notificationTestChannel': '渠道', // 通知測試渠道標簽
  'settings.notificationTestContent': '這是一条来自 HRS Web 設定頁的通知測試消息。', // 通知測試內容
  'settings.notificationTestDescription': '使用目前頁面草稿發送一条真實測試通知；測試不會儲存配置。', // 通知測試說明
  'settings.notificationTestFailure': '測試失敗', // 測試失敗提示
  'settings.notificationTestSend': '發送測試', // 發送測試按鈕
  'settings.notificationTestSuccess': '測試成功', // 測試成功提示
  'settings.notificationTestTimeout': '超時秒數', // 超時秒數標簽
  'settings.notificationTestTitle': '標題', // 通知測試標題標簽
  'settings.notificationTestTitleValue': 'HRS 通知測試', // 通知測試標題值
  'settings.notificationTesting': '測試中...', // 測試中狀態
  'settings.openConfigItems': '查看配置項', // 查看配置項按鈕
  'settings.pageDescription': '統一管理模型、數據源、通知、安全認證與匯入能力。', // 設定頁描述
  'settings.pageTitle': '系統設定', // 系統設定標題
  'settings.pageTitleDocument': '系統設定 - HRS', // 系統設定文檔標題
  'settings.promptCacheAdvancedDescription': '維護 provider prompt cache 的观測、主動 hint 與脱敏诊断；預設配置已適合普通使用。', // Prompt Cache 高級設定說明
  'settings.promptCacheAdvancedTitle': 'Provider Prompt Cache 高級設定', // Prompt Cache 高級設定標題
  'settings.reload': '重新載入', // 重新載入按鈕
  'settings.reset': '重置', // 重置按鈕
  'settings.revert': '还原', // 还原按鈕
  'settings.saveConfig': '儲存配置', // 儲存配置按鈕
  'settings.saveConfigWithCount': '儲存配置 ({count})', // 儲存配置含數量按鈕
  'settings.saveRetry': '重試儲存', // 重試儲存按鈕
  'settings.saving': '儲存中...', // 儲存中狀態
  'settings.schedulerAddTime': '添加時間', // 添加時間按鈕
  'settings.schedulerDescription': '配置自動分析的每日執行時間，儲存後长运行的 Web/API/Desktop 进程會按新配置生效。', // 定時任務說明
  'settings.schedulerDisabled': '未啟用', // 定時任務未啟用狀態
  'settings.schedulerEffectiveTimes': '生效時間', // 生效時間列表
  'settings.schedulerEnable': '啟用定時任務', // 啟用定時任務按鈕
  'settings.schedulerEnableDescription': '開啟後會按下方時間自動執行分析任務。', // 啟用定時任務說明
  'settings.schedulerEnabled': '已啟用', // 定時任務已啟用狀態
  'settings.schedulerLastError': '最近錯誤', // 最近錯誤時間
  'settings.schedulerLastSuccess': '上次成功', // 上次成功時間
  'settings.schedulerNextRun': '下次執行', // 下次執行時間
  'settings.schedulerRefresh': '重新整理狀態', // 重新整理狀態按鈕
  'settings.schedulerRefreshing': '重新整理中...', // 重新整理中狀態
  'settings.schedulerRemoveTime': '刪除時間', // 刪除時間按鈕
  'settings.schedulerRunAccepted': '已提交執行請求。', // 執行請求已提交提示
  'settings.schedulerRunNow': '立即執行一次', // 立即執行一次按鈕
  'settings.schedulerRunning': '运行中', // 运行中狀態
  'settings.schedulerRunningNow': '執行中...', // 執行中狀態
  'settings.schedulerStatus': '目前狀態', // 目前狀態標簽
  'settings.schedulerTimeInputAria': '定時執行時間 {index}', // 定時執行時間无障碍標簽
  'settings.schedulerTimes': '定時執行時間', // 定時執行時間列表
  'settings.schedulerTitle': '定時任務', // 定時任務標題
  'settings.setupGuideAddStocks': '維護自選股', // 維護自選股按鈕
  'settings.setupGuideCheckingSummary': '正在讀取配置狀態，完成後會顯示缺失項和試跑入口。', // 正在检查配置摘要
  'settings.setupGuideCheckingTitle': '正在检查首次啟動配置', // 正在检查配置標題
  'settings.setupGuideCompleteTitle': '基础配置已满足最小可用分析', // 基础配置已完成標題
  'settings.setupGuideConfigureLlm': '配置模型', // 配置模型按鈕
  'settings.setupGuideConfigureNotification': '配置通知', // 配置通知按鈕
  'settings.setupGuideDescription': '按最小可用分析流程检查自選股、模型渠道和通知配置，完成後可直接發起一次簡短試跑。', // 首次啟動配置检查說明
  'settings.setupGuideHiddenDescription': '需要重新检查基础配置、模型和通知時，可再次展開。', // 配置检查已隱藏描述
  'settings.setupGuideHiddenTitle': '首次啟動配置检查已隱藏', // 配置检查已隱藏標題
  'settings.setupGuideHide': '暫時隱藏', // 暫時隱藏按鈕
  'settings.setupGuideIncompleteTitle': '还有基础配置需要處理', // 基础配置未完成標題
  'settings.setupGuideMissingSummary': '还缺少 {count} 項：{labels}', // 缺少配置項摘要
  'settings.setupGuideOpen': '展開检查', // 展開检查按鈕
  'settings.setupGuideReadySummary': '所有必需項已就绪，可运行一次簡短分析驗證鏈路。', // 配置就绪摘要
  'settings.setupGuideRefresh': '重新整理检查', // 重新整理检查按鈕
  'settings.setupGuideRefreshing': '重新整理中...', // 重新整理中狀態
  'settings.setupGuideRunSmoke': '簡短試跑', // 簡短試跑按鈕
  'settings.setupGuideSmokeAccepted': '已提交 {stock} 的簡短分析任務。', // 試跑已提交
  'settings.setupGuideSmokeAcceptedWithTask': '已提交 {stock} 的簡短分析任務：{taskId}', // 試跑已提交含任務
  'settings.setupGuideSmokeNeedsStock': '需要至少一個自選股代碼後才能試跑。', // 試跑需要自選股提示
  'settings.setupGuideSmokeNotReady': '請先完成必需配置後再运行試跑。', // 試跑未就绪提示
  'settings.setupGuideSmokeRunning': '提交中...', // 提交中狀態
  'settings.setupGuideSmokeUnavailableTitle': '暫不能試跑', // 暫不能試跑標題
  'settings.setupGuideTitle': '首次啟動配置检查', // 首次啟動配置检查標題
  'settings.setupGuideUnknownSummary': '配置狀態讀取失敗。可先检查或修改設定項，稍後重新整理检查結果。', // 无法判断配置狀態摘要
  'settings.setupGuideUnknownTitle': '暫无法判断配置狀態', // 无法判断配置狀態標題
  'settings.setupStatusConfigured': '已配置', // 已配置狀態
  'settings.setupStatusInherited': '已繼承', // 已繼承狀態
  'settings.setupStatusNeedsAction': '待處理', // 待處理狀態
  'settings.setupStatusOptional': '可選', // 可選狀態
  'settings.updateBuildDescription': '重新執行前端建置或 Docker 镜像建置後，此處的代碼版本和建置時間會更新，可用来確認目前頁面資源是否已切換。', // 更新建置說明
  'settings.versionBuildTime': '建置時間', // 建置時間標簽
  'settings.versionDesktop': '桌面端版本', // 桌面端版本標簽
  'settings.versionInfo': '版本信息', // 版本信息標題
  'settings.versionInfoDescription': '用於確認目前 WebUI 静態資源是否已經切換到最新建置。', // 版本信息說明
  'settings.versionRevision': '代碼版本', // 代碼版本標簽
  'settings.versionWebui': 'WebUI 版本', // WebUI 版本標簽
  'settings.viewConfigItems': '查看配置項', // 查看配置項按鈕
  // stockBar.*
  'stockBar.emptyDescription': '完成首次分析後，這裡將按股票展示最新分析結果。', // 個股欄空狀態描述
  'stockBar.emptyTitle': '暫无個股記錄', // 個股欄空狀態標題
  'stockBar.loading': '載入個股中...', // 個股欄載入中狀態
  'stockBar.market': '大盤', // 個股欄大盤入口
  'stockBar.title': '個股欄', // 個股欄標題
  // stockTrend.*
  'stockTrend.allHistory': '全部歷史', // 全部歷史選項
  'stockTrend.averageScore': '平均分 {score}', // 平均分顯示
  'stockTrend.backToCurrentReport': '返回目前報告', // 返回目前報告按鈕
  'stockTrend.changePct': '漲跌幅', // 漲跌幅標簽
  'stockTrend.currentAdvice': '目前观點', // 目前观點標簽
  'stockTrend.currentScore': '目前分數', // 目前分數標簽
  'stockTrend.historyModelCount': '歷史模型 {count} 种', // 歷史模型數量
  'stockTrend.latestTime': '最近一次 {time}', // 最近一次時間
  'stockTrend.loadFailed': '歷史趨勢載入失敗', // 歷史趨勢載入失敗提示
  'stockTrend.loadMore': '載入更多', // 載入更多按鈕
  'stockTrend.loadedSummary': '已載入 {loaded} / {total} 条 · 排序：最新優先 · 模型：全部', // 載入摘要
  'stockTrend.loading': '載入同股歷史中...', // 同股歷史載入中
  'stockTrend.loadingMore': '載入中...', // 載入更多中狀態
  'stockTrend.model': '模型', // 模型標簽
  'stockTrend.modelCountSuffix': '{count}次', // 模型次數後缀
  'stockTrend.moreEmptyDescription': '完成多次分析後，這裡會展示观點變化、评分走勢和模型記錄。', // 更多歷史空狀態描述
  'stockTrend.moreEmptyTitle': '暫无更多同股歷史分析', // 更多歷史空狀態標題
  'stockTrend.neverRecorded': '未記錄', // 未記錄提示
  'stockTrend.noModelTitle': '未記錄模型', // 未記錄模型標題
  'stockTrend.records': '歷史分析記錄', // 歷史記錄標簽
  'stockTrend.reload': '重新載入', // 重新載入按鈕
  'stockTrend.report': '查看報告', // 查看報告按鈕
  'stockTrend.result': '分析結果', // 分析結果標簽
  'stockTrend.score': '分數', // 分數標簽
  'stockTrend.stockPrice': '股价', // 股价標簽
  'stockTrend.table.action': '操作', // 趨勢表格操作列
  'stockTrend.time': '時間', // 趨勢表格時間列
  'stockTrend.title': '歷史趨勢', // 歷史趨勢標題
  'stockTrend.turnoverRate': '換手率', // 換手率標簽
  'stockTrend.volumeRatio': '量比', // 量比標簽
  'stockTrend.window30': '近30天', // 近 30 天窗口
  'stockTrend.window90': '近90天', // 近 90 天窗口
  // stockUnit.*
  'stockUnit.amountWanYi': '万亿', // 金额單位万亿
  'stockUnit.amountYi': '亿', // 金额單位亿
  'stockUnit.volumeHundredMillionLots': '亿手', // 成交量單位亿手
  'stockUnit.volumeTenThousandLots': '万手', // 成交量單位万手
  // usage.*
  'usage.breakdown': 'Breakdown', // 用量明細標簽
  'usage.callType.agent': '問股 Agent', // 問股調用類型
  'usage.callType.analysis': '個股分析', // 個股分析調用類型
  'usage.callType.marketReview': '大盤復盘', // 大盤復盘調用類型
  'usage.callType.unknown': '{type}', // 未知調用類型
  'usage.callTypeDetail': '{calls} 次 · Prompt {prompt} · Completion {completion}', // 調用類型明細文案
  'usage.callTypeTitle': '調用類型', // 調用類型標題
  'usage.calls': '{count} 次調用', // 調用次數統計
  'usage.completionTokens': 'Completion tokens', // Completion token 數量
  'usage.completionTokensHint': '模型輸出消耗', // Completion token 說明
  'usage.dateRange': '{from} 至 {to}', // 日期範圍
  'usage.description': '查看 LLM 調用次數、Prompt/Completion Token 消耗、模型用量和最近調用明細。', // 用量頁面描述
  'usage.emptyDescription': '完成一次分析、大盤復盘或問股調用後，這裡會顯示模型用量。', // 用量空狀態描述
  'usage.emptyTitle': '暫无 Token 用量記錄', // 用量空狀態標題
  'usage.error.message': 'Token 用量數據載入失敗', // 用量載入失敗提示
  'usage.error.title': 'Token 用量載入失敗', // 用量載入失敗標題
  'usage.eyebrow': 'Usage', // 用量頁面眉標
  'usage.maxSingleCall': '單次峰值', // 單次調用 token 峰值
  'usage.modelUsage': '模型用量', // 模型用量區塊標題
  'usage.modelUsageDescription': '按模型聚合 Token 消耗、調用次數和單次峰值。', // 模型用量說明
  'usage.noRecentCalls': '暫无最近調用記錄', // 最近調用空狀態
  'usage.period.all': '全部', // 全部時間範圍
  'usage.period.month': '本月', // 本月時間範圍
  'usage.period.today': '今日', // 今日時間範圍
  'usage.promptTokens': 'Prompt tokens', // Prompt token 數量
  'usage.promptTokensHint': '輸入上下文消耗', // Prompt token 說明
  'usage.recentCalls': '最近調用', // 最近調用區塊標題
  'usage.recentCallsDescription': '最近 50 条 LLM token 審計記錄。', // 最近調用說明
  'usage.refresh': '重新整理', // 重新整理按鈕
  'usage.table.model': '模型', // 調用表格模型列
  'usage.table.time': '時間', // 調用表格時間列
  'usage.table.type': '類型', // 調用表格類型列
  'usage.title': 'Token 用量監控', // 用量頁面標題
  'usage.totalCalls': '調用次數', // 總調用次數
  'usage.totalCallsHint': '已記錄的 LLM 調用', // 總調用次數說明
  'usage.totalTokens': '總 tokens', // 總 token 數量
  // watchlist.*
  'watchlist.add': '添加自選股', // 添加自選股按鈕
  'watchlist.addPlaceholder': '添加代碼，如 600519', // 添加自選股占位符
  'watchlist.analyzeAll': '分析全部', // 分析全部自選股
  'watchlist.analyzePending': '仅未分析', // 仅分析未分析自選股
  'watchlist.analyzedToday': '今日已分析', // 今日已分析狀態
  'watchlist.batchFailed': '自選股批量分析提交失敗', // 批量分析失敗提示
  'watchlist.batchIncompleteResponse': '批量接口本組請求 {requested} 只，仅確認 {confirmed} 只，返回結果不完整', // 批量回應不完整提示
  'watchlist.batchPartiallySubmitted': '已確認提交 {accepted} 個任務，{duplicates} 個正在运行；另有 {unconfirmed} 只未確認，已停止後續提交並重新整理任務列表。原因：{error}', // 批量部分提交提示
  'watchlist.batchSubmitted': '已提交 {accepted} 個任務，{duplicates} 個正在运行', // 批量提交成功提示
  'watchlist.emptyDescription': '在報告詳情或這裡添加股票後，可一键运行整組自選股。', // 自選股空狀態描述
  'watchlist.emptyTitle': '暫无自選股', // 自選股空狀態標題
  'watchlist.listHint': '按自選顺序展示，今日狀態即時標記', // 自選股列表說明
  'watchlist.loading': '載入自選股中...', // 自選股載入中狀態
  'watchlist.noPendingAnalyze': '今天沒有待分析的自選股。', // 无待分析自選股提示
  'watchlist.noStocksAnalyze': '請先添加自選股。', // 无自選股提示
  'watchlist.notAnalyzedToday': '今日未分析', // 今日未分析狀態
  'watchlist.pendingStatusLoading': '正在確認自選股今日狀態，請稍後再提交仅未分析。', // 待分析狀態載入中提示
  'watchlist.pendingStatusUnavailable': '自選股今日狀態仍有未知項，請重新整理後再提交仅未分析。', // 待分析狀態不可用提示
  'watchlist.pendingToday': '今日待分析', // 今日待分析狀態
  'watchlist.refresh': '重新整理自選股', // 重新整理自選股按鈕
  'watchlist.removeAria': '從自選股移除 {code}', // 移除自選股无障碍標簽
  'watchlist.submitting': '提交中', // 自選股提交中狀態
  'watchlist.tabHistory': '歷史', // 自選股歷史標簽頁
  'watchlist.tabToday': '今日', // 自選股今日標簽頁
  'watchlist.tabWatchlist': '自選', // 自選股自選標簽頁
  'watchlist.taskRunning': '任務{status}', // 自選股任務运行狀態
  'watchlist.title': '自選股', // 自選股標題
  'watchlist.todayCoverage': '今日覆盖', // 今日分析覆盖率
  'watchlist.todayEmptyDescription': '今天完成分析後，這裡會按评分顯示股票排行。', // 今日空狀態描述
  'watchlist.todayEmptyTitle': '今天还沒有分析結果', // 今日空狀態標題
  'watchlist.todayLoadErrorDescription': '完整歷史分頁載入失敗，為避免展示不完整排行，請重新整理後重試。', // 今日排行載入失敗描述
  'watchlist.todayLoadErrorTitle': '今日排行載入失敗', // 今日排行載入失敗標題
  'watchlist.todaySortHint': '按情绪分優先排序', // 今日排序提示
  'watchlist.todayStatusLoading': '確認今日狀態中', // 今日狀態確認中
  'watchlist.todayStatusUnavailable': '今日狀態未知', // 今日狀態未知提示
  'watchlist.todayTitle': '今日分析', // 今日分析標題
  'watchlist.topScore': '最高分', // 最高分標簽
  'watchlist.watchlistCoverage': '自選覆盖' // 自選覆盖率

} as const;

// 注意：UiTextKey 的唯一真源是 uiText-zh.ts，此处不再重复导出。
// 三语 key 集合对齐由 uiText.ts 的 Record<UiLanguage, Record<UiTextKey, string>> 类型强制校验。
export default zhHant;






