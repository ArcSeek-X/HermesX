package hermesx.system.exception;

import hermesx.system.base.ErrorVO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.*;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.method.annotation.HandlerMethodValidationException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

/** 在 HTTP 边界把异常转成状态码，Service/DAO 不需要依赖 HTTP 对象。 */
@RestControllerAdvice
public class GlobalExceptionHandler {
    private static final Logger LOG = LoggerFactory.getLogger(GlobalExceptionHandler.class);
    @ExceptionHandler(UserNotFoundException.class)
    ResponseEntity<ErrorVO> missing(UserNotFoundException e) {
        return ResponseEntity.status(404).body(new ErrorVO("USER_NOT_FOUND", e.getMessage()));
    }
    @ExceptionHandler(DuplicateKeyException.class)
    ResponseEntity<ErrorVO> duplicate() {
        return ResponseEntity.status(409).body(new ErrorVO("USERNAME_EXISTS", "登录账号已存在（含已删除账号）"));
    }
    @ExceptionHandler({MethodArgumentNotValidException.class, HttpMessageNotReadableException.class,
            HandlerMethodValidationException.class, MethodArgumentTypeMismatchException.class, jakarta.validation.ConstraintViolationException.class})
    ResponseEntity<ErrorVO> invalidRequest(Exception e) {
        // 不返回 rejectedValue：其中可能有密码。
        return ResponseEntity.badRequest().body(new ErrorVO("INVALID_REQUEST", "参数格式、长度或取值不正确"));
    }
    @ExceptionHandler(IllegalArgumentException.class)
    ResponseEntity<ErrorVO> invalidBusiness(IllegalArgumentException e) {
        return ResponseEntity.badRequest().body(new ErrorVO("INVALID_REQUEST", e.getMessage()));
    }
    @ExceptionHandler(DataAccessException.class)
    ResponseEntity<ErrorVO> database(DataAccessException e) {
        LOG.error("用户数据访问失败，异常类型：{}", e.getClass().getSimpleName());
        return ResponseEntity.status(503).body(new ErrorVO("DATABASE_UNAVAILABLE", "用户数据暂不可用"));
    }
}
