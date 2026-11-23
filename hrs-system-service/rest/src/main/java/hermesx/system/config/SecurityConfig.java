package hermesx.system.config;

import org.springframework.context.annotation.*;
import org.springframework.beans.factory.annotation.Value;
import jakarta.servlet.DispatcherType;
import hermesx.system.security.RestSecurityHandler;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.*;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;

/** 本案例使用配置提供的管理身份，独立于被管理的用户表；不是完整登录系统。 */
@Configuration
public class SecurityConfig {
    @Bean PasswordEncoder passwordEncoder() { return new BCryptPasswordEncoder(); }

    @Bean UserDetailsService administrators(@Value("${hermesx.system.admin-username}") String username,
            @Value("${hermesx.system.admin-password}") String password, PasswordEncoder encoder) {
        if (username.isBlank() || username.length() > 64 || password.isBlank()
                || password.getBytes(java.nio.charset.StandardCharsets.UTF_8).length < 12
                || password.getBytes(java.nio.charset.StandardCharsets.UTF_8).length > 72) {
            throw new IllegalArgumentException("请配置管理账号（最多64字符）和12至72字节管理密码");
        }
        return new InMemoryUserDetailsManager(User.withUsername(username)
                .password(encoder.encode(password)).roles("SYSTEM_ADMIN").build());
    }

    @Bean SecurityFilterChain apiSecurity(HttpSecurity http, RestSecurityHandler errors) throws Exception {
        // 每次请求用 Basic 认证；Session 仅保存 CSRF token，不保存登录状态。
        return http.authorizeHttpRequests(a -> a.dispatcherTypeMatchers(DispatcherType.ERROR).permitAll().anyRequest().hasRole("SYSTEM_ADMIN"))
                .httpBasic(b -> b.authenticationEntryPoint(errors))
                .exceptionHandling(e -> e.authenticationEntryPoint(errors).accessDeniedHandler(errors))
                .logout(AbstractHttpConfigurer::disable)
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .csrf(c -> c.csrfTokenRepository(new org.springframework.security.web.csrf.HttpSessionCsrfTokenRepository()))
                .build();
    }
}
