package hermesx.common.rest;

/** 公共协议：结果码给程序判断，默认提示给用户阅读，不绑定HTTP或业务服务。 */
public interface ResultCode {
    String getCode();
    String getMessage();
}
