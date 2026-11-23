/** Java 服务统一响应；成功业务码固定为字符串 "200"，不等同于 HTTP 状态码。 */
export interface RestResult<T> {
  resultCode: string;
  resultMsg: string;
  /** 成功时为业务数据；失败时允许为 null。 */
  resultData: T | null;
}
