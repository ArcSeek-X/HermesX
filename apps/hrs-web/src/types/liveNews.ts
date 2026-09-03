/**
 * 实时财经快讯（Live News）类型定义。
 *
 * 数据来源为华尔街见闻 7x24 快讯，接口契约见 docs/live-news.md。
 * 字段与后端 Pydantic 模型一一对应（后端 snake_case，此处保持同名以简化对接）。
 */

/** 快讯频道（前端 Tab 的数据源） */
export interface LiveNewsChannel {
  /** 频道 ID，同时作为接口查询入参，如 `a-stock-channel` */
  value: string;
  /** 频道展示文案，如 `A股` */
  label: string;
}

/** 单条快讯 */
export interface LiveNewsItem {
  /** 快讯 ID（上游 id），全局唯一 */
  id: number;
  /** 标题；快讯常为空字符串，展示时应回退到 content */
  title: string;
  /** 正文纯文本 */
  content: string;
  /** 发布时间（秒级 Unix 时间戳） */
  displayTime: number | null;
  /** 重要级，统一业务量纲：0=无 / 1=普通 / 2=较重要 / 3=重要 / 4=非常重要（见 constants/importance.ts） */
  score: number;
  /** 是否重要，等价于 `score >= 阈值`（阈值由后端配置决定，默认 3=重要） */
  important: boolean;
  /** 所属频道（上游原始值），一条快讯可属于多个频道 */
  channels: string[];
  /** 原文链接，形如 `https://wallstreetcn.com/livenews/<id>` */
  uri: string;
  /** 作者显示名，可能为空 */
  author: string | null;
}

/** 频道列表响应 */
export interface LiveNewsChannelsResponse {
  /** 可用频道列表；降级模式下只返回「要闻」一项 */
  channels: LiveNewsChannel[];
  /**
   * 是否处于降级模式。
   * true 表示官方源不可用，数据来自 NewsNow 兜底源：
   * 无频道分类、无重要级，前端需隐藏「只看重要的」开关与重要标签。
   */
  degraded: boolean;
  /** 当前实际生效的数据源：`wallstreetcn` 或 `newsnow` */
  source: string;
}

/** 快讯列表响应 */
export interface LiveNewsResponse {
  /** 快讯列表，按发布时间倒序 */
  items: LiveNewsItem[];
  /** 下一页游标；为 null 表示已无更多数据 */
  nextCursor: string | null;
  /** 是否降级数据 */
  degraded: boolean;
  /** 服务端当前时间戳（秒），供前端校准本地时间 */
  serverTime: number;
  /** 当前过滤条件下的总条数，用于空态判断 */
  total: number;
}

/** 手动刷新响应 */
export interface LiveNewsRefreshResponse {
  /** 本次新入库的条数（重复条目不计入） */
  fetchedCount: number;
  /** 是否走了降级 */
  degraded: boolean;
  /** 各频道失败详情；为空表示全部成功 */
  errors: Array<{ channel: string; error: string }>;
}

/** 快讯列表查询参数 */
export interface LiveNewsQueryParams {
  /** 频道 ID，必填 */
  channel: string;
  /** 只看重要的 */
  importantOnly?: boolean;
  /** 关键词 */
  keyword?: string;
  /** 精确查询某日，格式 YYYY-MM-DD；与 dateFrom/dateTo 同时传时以本参数为准 */
  date?: string;
  /** 起始日期 YYYY-MM-DD（含当天） */
  dateFrom?: string;
  /** 结束日期 YYYY-MM-DD（含当天） */
  dateTo?: string;
  /** 分页游标，取上次响应的 nextCursor */
  cursor?: string;
  /** 每页条数，1~100 */
  limit?: number;
}

/** 按天分组后的快讯（由 Hook 计算，非接口返回） */
export interface LiveNewsDateGroup {
  /** 分组键，YYYY-MM-DD */
  date: string;
  /** 分组标题，形如 `08月28日 周五` */
  label: string;
  /** 该日的快讯列表 */
  items: LiveNewsItem[];
}
