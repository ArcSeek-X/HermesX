package hermesx.system.security;

import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.stereotype.Component;

/** 审计人必须来自认证上下文，不能相信请求体中的 createBy/updateBy。 */
@Component
public class CurrentUser {
    public String requireAdmin() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !auth.isAuthenticated() || auth.getAuthorities().stream()
                .noneMatch(a -> a.getAuthority().equals("ROLE_SYSTEM_ADMIN"))) {
            throw new AccessDeniedException("需要system管理权限");
        }
        return auth.getName();
    }
}
