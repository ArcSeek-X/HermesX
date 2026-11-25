/**
 * 简体中文（zh）文案：页面表格列头。
 *
 * 只收录从属于页面的列头文案；组件内部列头仍留在 component-zh.ts。
 * 按所属页面分组，分组顺序与 page-zh.ts 中页面出现顺序一致，便于与页面文案对照。
 * orgManagement.field.* 同时作为组织管理编辑表单的字段标签使用。
 *
 * 由 uiText-zh.ts 按类别拆分，经 uiText-zh/index.ts 聚合；key 与三语主字典保持一致。
 */

export const columnZh = {
  // decisionSignals.* AI 建议页：持仓列头
  'decisionSignals.portfolioColumn': 'AI 建议', // 【页面】AI建议-持仓 AI 建议列名

  // stockMetricView.* 股票度量视图页：列头
  'stockMetricView.column.rowNumber': '序号', // 【页面】度量视图-列头：序号
  'stockMetricView.column.market': '市场', // 【页面】度量视图-列头：市场
  'stockMetricView.column.code': '代码', // 【页面】度量视图-列头：代码
  'stockMetricView.column.name': '名称', // 【页面】度量视图-列头：名称
  'stockMetricView.column.price': '最新价', // 【页面】度量视图-列头：最新价
  'stockMetricView.column.changePct': '涨跌幅', // 【页面】度量视图-列头：涨跌幅
  'stockMetricView.column.volume': '成交量', // 【页面】度量视图-列头：成交量
  'stockMetricView.column.relativeVolume': '量比', // 【页面】度量视图-列头：量比
  'stockMetricView.column.totalMarketCap': '总市值', // 【页面】度量视图-列头：总市值
  'stockMetricView.column.peRatioTTM': '市盈率(TTM)', // 【页面】度量视图-列头：市盈率 TTM
  'stockMetricView.column.epsDiluted': '每股收益', // 【页面】度量视图-列头：每股收益（当期）
  'stockMetricView.column.epsGrowthTtmYoyPct': 'EPS增长(TTM同比)', // 【页面】度量视图-列头：EPS 增长 TTM 同比
  'stockMetricView.column.dividendYieldPct': '股息率', // 【页面】度量视图-列头：股息率
  'stockMetricView.column.industry': '所属板块', // 【页面】度量视图-列头：所属板块
  'stockMetricView.column.analystRating': '分析师评级', // 【页面】度量视图-列头：分析师评级
  'stockMetricView.column.source': '数据来源', // 【页面】度量视图-列头：数据来源

  // orgManagement.* 组织管理页：表格列头 / 表单字段标签
  "orgManagement.field.name": "组织名称",
  "orgManagement.field.shortName": "组织简称",
  "orgManagement.field.code": "组织编码",
  "orgManagement.field.nature": "组织性质",
  "orgManagement.field.type": "组织类型",
  "orgManagement.field.leader": "负责人",
  "orgManagement.field.phone": "联系电话",
  "orgManagement.field.email": "邮箱",
  "orgManagement.field.sort": "显示排序",
  "orgManagement.field.status": "启用状态",
  "orgManagement.field.remark": "备注",
  "orgManagement.field.parent": "上级组织",
  "orgManagement.field.enterprise": "所属企业ID",

} as const;
