package hermesx.system.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import hermesx.common.rest.*;
import jakarta.servlet.http.*;
import java.io.IOException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.security.web.access.AccessDeniedHandler;
import org.springframework.security.web.csrf.CsrfException;
import org.springframework.stereotype.Component;

/** 安全过滤器发生在Controller之前，必须在这里单独返回统一JSON，而不是HTML或空响应。 */
@Component
public class RestSecurityHandler implements AuthenticationEntryPoint, AccessDeniedHandler {
    public static final String BASIC_CHALLENGE="Basic realm=\"HermesX system\"";
    private final ObjectMapper json;
    public RestSecurityHandler(ObjectMapper json) { this.json=json; }
    @Override public void commence(HttpServletRequest request,HttpServletResponse response,AuthenticationException error) throws IOException {
        response.setHeader("WWW-Authenticate",BASIC_CHALLENGE);
        write(response,401,ResultCodeEnum.UNAUTHENTICATED);
    }
    @Override public void handle(HttpServletRequest request,HttpServletResponse response,AccessDeniedException error) throws IOException {
        write(response,403,error instanceof CsrfException?ResultCodeEnum.CSRF_INVALID:ResultCodeEnum.FORBIDDEN);
    }
    private void write(HttpServletResponse response,int status,ResultCode code) throws IOException {
        response.setStatus(status); response.setCharacterEncoding("UTF-8"); response.setContentType("application/json");
        json.writeValue(response.getOutputStream(),RestResult.failure(code));
    }
}
