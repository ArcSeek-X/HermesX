package hermesx.common.rest;

import java.util.Objects;

/** 不可变响应，每次创建新对象，避免共享可变SUCCESS实例导致请求间数据串用。 */
public record RestResult<T>(String resultCode, String resultMsg, T resultData) {
    public RestResult {
        if (resultCode==null || resultCode.isBlank()) throw new IllegalArgumentException("结果码不能为空");
        Objects.requireNonNull(resultMsg,"结果提示不能为null");
    }
    public static <T> RestResult<T> success(T data) {
        return new RestResult<>(ResultCodeEnum.SUCCESS.getCode(),ResultCodeEnum.SUCCESS.getMessage(),data);
    }
    public static <T> RestResult<T> failure(ResultCode code) { return failure(code,code.getMessage()); }
    public static <T> RestResult<T> failure(ResultCode code,String message) {
        Objects.requireNonNull(code,"结果码不能为空");
        if (ResultCodeEnum.SUCCESS.getCode().equals(code.getCode())) throw new IllegalArgumentException("失败响应不能使用成功码");
        return new RestResult<>(code.getCode(),message,null);
    }
}
