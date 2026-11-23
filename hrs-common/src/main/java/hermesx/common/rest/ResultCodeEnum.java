package hermesx.common.rest;

import hermesx.common.rest.ResultCode;

/** 集中维护稳定结果码与默认文案；不允许各接口重复手写一套编号。 */
public enum ResultCodeEnum implements ResultCode {
    SUCCESS("200", "操作成功。"),
    INVALID_REQUEST("INVALID_REQUEST", "请求参数格式、长度或取值不正确。"),
    UNAUTHENTICATED("UNAUTHENTICATED", "身份认证失败，请提供有效凭据。"),
    FORBIDDEN("FORBIDDEN", "无权执行此操作。"),
    CSRF_INVALID("CSRF_INVALID", "请求校验失败，请刷新校验信息后重试。"),
    NOT_FOUND("NOT_FOUND", "请求的资源不存在。"),
    METHOD_NOT_ALLOWED("METHOD_NOT_ALLOWED", "当前接口不支持此请求方法。"),
    UNSUPPORTED_MEDIA_TYPE("UNSUPPORTED_MEDIA_TYPE", "不支持此请求内容类型。"),
    NOT_ACCEPTABLE("NOT_ACCEPTABLE", "无法提供请求指定的响应格式。"),
    INTERNAL_ERROR("INTERNAL_ERROR", "系统暂时无法处理请求，请稍后重试。"),
    DATABASE_UNAVAILABLE("DATABASE_UNAVAILABLE", "数据服务暂不可用，请稍后重试。");

    private final String code;
    private final String message;
    ResultCodeEnum(String code, String message) { this.code=code; this.message=message; }
    @Override public String getCode() { return code; }
    @Override public String getMessage() { return message; }
}
