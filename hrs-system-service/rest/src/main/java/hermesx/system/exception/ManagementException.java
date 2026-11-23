package hermesx.system.exception;

import hermesx.common.rest.ResultCode;

/** 业务错误只携带语义与类别；HTTP状态由边界处理器映射。 */
public class ManagementException extends RuntimeException {
    public enum Kind { INVALID_REQUEST, NOT_FOUND, CONFLICT, INTERNAL }
    private final Kind kind;
    private final ResultCode resultCode;
    private ManagementException(Kind kind, ResultCode code, String message) {
        super(message); this.kind=kind; this.resultCode=code;
    }
    public static ManagementException missing(ResultCode code,String message) { return new ManagementException(Kind.NOT_FOUND,code,message); }
    public static ManagementException conflict(ResultCode code,String message) { return new ManagementException(Kind.CONFLICT,code,message); }
    public static ManagementException invalid(ResultCode code,String message) { return new ManagementException(Kind.INVALID_REQUEST,code,message); }
    public static ManagementException internal(ResultCode code) { return new ManagementException(Kind.INTERNAL,code,code.getMessage()); }
    public Kind kind() { return kind; }
    public ResultCode resultCode() { return resultCode; }
}
