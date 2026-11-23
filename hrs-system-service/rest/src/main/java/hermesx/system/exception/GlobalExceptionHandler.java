package hermesx.system.exception;

import hermesx.common.rest.*;
import hermesx.system.enums.SystemResultCodeEnum;
import jakarta.validation.ConstraintViolationException;
import org.slf4j.*;
import org.springframework.dao.*;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.bind.*;
import org.springframework.web.method.annotation.*;
import org.springframework.web.servlet.resource.NoResourceFoundException;
import org.springframework.web.servlet.NoHandlerFoundException;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.web.*;

/** 统一HTTP错误边界。原始异常、请求值、SQL和密码不能直接作为resultMsg返回。 */
@RestControllerAdvice
public class GlobalExceptionHandler {
    private static final Logger LOG=LoggerFactory.getLogger(GlobalExceptionHandler.class);
    private ResponseEntity<RestResult<Void>> failure(int status,ResultCode code) {
        return ResponseEntity.status(status).contentType(MediaType.APPLICATION_JSON).body(RestResult.failure(code));
    }
    @ExceptionHandler(ManagementException.class)
    ResponseEntity<RestResult<Void>> management(ManagementException e) {
        int status=switch(e.kind()) { case INVALID_REQUEST->400; case NOT_FOUND->404; case CONFLICT->409; case INTERNAL->500; };
        return ResponseEntity.status(status).contentType(MediaType.APPLICATION_JSON)
                .body(RestResult.failure(e.resultCode(),e.getMessage()));
    }
    @ExceptionHandler(UserNotFoundException.class)
    ResponseEntity<RestResult<Void>> missingUser() { return failure(404,SystemResultCodeEnum.USER_NOT_FOUND); }
    @ExceptionHandler(DuplicateKeyException.class)
    ResponseEntity<RestResult<Void>> duplicate() { return failure(409,SystemResultCodeEnum.USERNAME_EXISTS); }
    @ExceptionHandler({MethodArgumentNotValidException.class,HttpMessageNotReadableException.class,
        HandlerMethodValidationException.class,MethodArgumentTypeMismatchException.class,
        MissingServletRequestParameterException.class,ConstraintViolationException.class})
    ResponseEntity<RestResult<Void>> invalidRequest(Exception e) { return failure(400,ResultCodeEnum.INVALID_REQUEST); }
    @ExceptionHandler({NoResourceFoundException.class,NoHandlerFoundException.class})
    ResponseEntity<RestResult<Void>> missingRoute(Exception e) { return failure(404,ResultCodeEnum.NOT_FOUND); }
    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    ResponseEntity<RestResult<Void>> method(HttpRequestMethodNotSupportedException e) {
        HttpHeaders headers=new HttpHeaders(); headers.setContentType(MediaType.APPLICATION_JSON);
        if (e.getSupportedHttpMethods()!=null) headers.setAllow(e.getSupportedHttpMethods());
        return new ResponseEntity<>(RestResult.failure(ResultCodeEnum.METHOD_NOT_ALLOWED),headers,HttpStatus.METHOD_NOT_ALLOWED);
    }
    @ExceptionHandler(HttpMediaTypeNotSupportedException.class)
    ResponseEntity<RestResult<Void>> media(HttpMediaTypeNotSupportedException e) { return failure(415,ResultCodeEnum.UNSUPPORTED_MEDIA_TYPE); }
    @ExceptionHandler(HttpMediaTypeNotAcceptableException.class)
    ResponseEntity<RestResult<Void>> accept(HttpMediaTypeNotAcceptableException e) { return failure(406,ResultCodeEnum.NOT_ACCEPTABLE); }
    @ExceptionHandler(AccessDeniedException.class)
    ResponseEntity<RestResult<Void>> denied() { return failure(403,ResultCodeEnum.FORBIDDEN); }
    @ExceptionHandler(DataAccessException.class)
    ResponseEntity<RestResult<Void>> database(DataAccessException e) {
        LOG.error("数据库操作失败，异常类型：{}",e.getClass().getSimpleName());
        return failure(503,ResultCodeEnum.DATABASE_UNAVAILABLE);
    }
    @ExceptionHandler(Exception.class)
    ResponseEntity<RestResult<Void>> unexpected(Exception e) {
        // 包括未预期的IllegalArgumentException，不允许用异常原文向调用方泄露内部信息。
        LOG.error("未预期错误，异常类型：{}",e.getClass().getSimpleName());
        return failure(500,ResultCodeEnum.INTERNAL_ERROR);
    }
}
