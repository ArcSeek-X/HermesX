package hermesx.system.controller;

import hermesx.common.rest.*;
import hermesx.system.security.RestSecurityHandler;
import jakarta.servlet.RequestDispatcher;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.boot.web.servlet.error.ErrorController;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;

/** 容器错误分发兜底；不返回Spring默认的timestamp/path/error等第二套响应结构。 */
@RestController
public class ApiErrorController implements ErrorController {
    @RequestMapping("${server.error.path:${error.path:/error}}")
    public ResponseEntity<RestResult<Void>> error(HttpServletRequest request) {
        Object value=request.getAttribute(RequestDispatcher.ERROR_STATUS_CODE);
        int status=value instanceof Integer number && number>=400 && number<=599?number:500;
        ResultCode code=switch(status) {
            case 400->ResultCodeEnum.INVALID_REQUEST; case 401->ResultCodeEnum.UNAUTHENTICATED;
            case 403->ResultCodeEnum.FORBIDDEN; case 404->ResultCodeEnum.NOT_FOUND;
            case 405->ResultCodeEnum.METHOD_NOT_ALLOWED; case 406->ResultCodeEnum.NOT_ACCEPTABLE;
            case 415->ResultCodeEnum.UNSUPPORTED_MEDIA_TYPE; default->ResultCodeEnum.INTERNAL_ERROR;
        };
        HttpHeaders headers=new HttpHeaders(); headers.setContentType(MediaType.APPLICATION_JSON);
        if (status==401) headers.set(HttpHeaders.WWW_AUTHENTICATE,RestSecurityHandler.BASIC_CHALLENGE);
        return new ResponseEntity<>(RestResult.failure(code),headers,HttpStatusCode.valueOf(status));
    }
}
