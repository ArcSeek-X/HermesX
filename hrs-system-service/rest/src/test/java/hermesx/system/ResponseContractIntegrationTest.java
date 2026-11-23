package hermesx.system;

import com.fasterxml.jackson.databind.*;
import hermesx.common.rest.*;
import hermesx.system.enums.SystemResultCodeEnum;
import jakarta.servlet.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.*;
import org.springframework.test.context.*;
import org.springframework.test.web.servlet.*;
import org.springframework.web.bind.annotation.*;
import java.nio.file.*;
import java.util.*;
import static org.assertj.core.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.*;

/** 验证同一协议覆盖MVC、安全过滤器及容器错误边界，而不只检查成功Controller。 */
@SpringBootTest(properties={"spring.cloud.nacos.discovery.enabled=false",
    "spring.sql.init.mode=always",
    "spring.sql.init.schema-locations=classpath:db/hrs-system-service.sql"})
@AutoConfigureMockMvc
@ActiveProfiles("response-contract-test")
@Import(ResponseContractIntegrationTest.ProbeController.class)
class ResponseContractIntegrationTest {
    static final Path DATABASE;
    static {
        try { DATABASE=Files.createTempFile("hermesx-response-", ".db"); }
        catch(java.io.IOException e) { throw new ExceptionInInitializerError(e); }
    }
    @DynamicPropertySource static void properties(DynamicPropertyRegistry r) {
        r.add("HRS_SYSTEM_DB_URL",()->"jdbc:sqlite:"+DATABASE);
        r.add("HRS_SYSTEM_ADMIN_USERNAME",()->"response-manager");
        r.add("HRS_SYSTEM_ADMIN_PASSWORD",()->"test-only-response-password");
    }
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;
    @AfterAll static void cleanup() throws Exception { Files.deleteIfExists(DATABASE); }
    void envelope(MvcResult result,int status,String code) throws Exception {
        assertThat(result.getResponse().getStatus()).isEqualTo(status);
        assertThat(result.getResponse().getContentType()).startsWith("application/json");
        JsonNode body=json.readTree(result.getResponse().getContentAsString());
        List<String> fields=new ArrayList<>();body.fieldNames().forEachRemaining(fields::add);
        assertThat(fields).containsExactlyInAnyOrder("resultCode","resultMsg","resultData");
        assertThat(body.get("resultCode").asText()).isEqualTo(code);
        assertThat(body.get("resultMsg").asText()).isNotBlank();
        if (!code.equals("200")) assertThat(body.get("resultData").isNull()).isTrue();
    }
    @Test void commonAndBusinessCodesAreUnique() {
        Set<String> codes=new HashSet<>();
        for (ResultCode code:ResultCodeEnum.values()) assertThat(codes.add(code.getCode())).isTrue();
        for (ResultCode code:SystemResultCodeEnum.values()) assertThat(codes.add(code.getCode())).isTrue();
    }
    @Test void successPaginationTreeAndCsrfAreWrappedExactlyOnce() throws Exception {
        for (String url:List.of("/api/system/users","/api/system/organizations/tree","/api/system/menus/tree","/api/system/users/csrf")) {
            var result=mvc.perform(get(url).with(user("manager").roles("SYSTEM_ADMIN"))).andReturn();
            envelope(result,200,"200");
            assertThat(json.readTree(result.getResponse().getContentAsString()).get("resultData").has("resultCode")).isFalse();
        }
    }
    @Test void securityErrorsUseJsonAndPreserveAuthenticationChallenge() throws Exception {
        var missing=mvc.perform(get("/api/system/users")).andReturn();
        envelope(missing,401,"UNAUTHENTICATED");
        assertThat(missing.getResponse().getHeader("WWW-Authenticate")).startsWith("Basic ");
        envelope(mvc.perform(get("/api/system/users").with(httpBasic("response-manager","wrong"))).andReturn(),401,"UNAUTHENTICATED");
        envelope(mvc.perform(get("/api/system/users").with(user("ordinary").roles("USER"))).andReturn(),403,"FORBIDDEN");
        envelope(mvc.perform(post("/api/system/users").with(httpBasic("response-manager","test-only-response-password"))
                .contentType("application/json").content("{}")).andReturn(),403,"CSRF_INVALID");
        envelope(mvc.perform(post("/api/system/users").with(user("manager").roles("SYSTEM_ADMIN")).with(csrf().useInvalidToken())
                .contentType("application/json").content("{}")).andReturn(),403,"CSRF_INVALID");
    }
    @Test void protocolAndValidationErrorsUseTheSameEnvelope() throws Exception {
        envelope(mvc.perform(get("/api/system/users?page=0").with(user("manager").roles("SYSTEM_ADMIN"))).andReturn(),400,"INVALID_REQUEST");
        envelope(mvc.perform(post("/api/system/users").with(user("manager").roles("SYSTEM_ADMIN")).with(csrf())
                .contentType("application/json").content("{broken")).andReturn(),400,"INVALID_REQUEST");
        envelope(mvc.perform(get("/api/system/users/999999").with(user("manager").roles("SYSTEM_ADMIN"))).andReturn(),404,"USER_NOT_FOUND");
        envelope(mvc.perform(get("/api/system/unknown").with(user("manager").roles("SYSTEM_ADMIN"))).andReturn(),404,"NOT_FOUND");
        var method=mvc.perform(patch("/api/system/users").with(user("manager").roles("SYSTEM_ADMIN")).with(csrf())).andReturn();
        envelope(method,405,"METHOD_NOT_ALLOWED");assertThat(method.getResponse().getHeader("Allow")).contains("GET");
        envelope(mvc.perform(post("/api/system/users").with(user("manager").roles("SYSTEM_ADMIN")).with(csrf())
                .contentType("text/plain").content("text")).andReturn(),415,"UNSUPPORTED_MEDIA_TYPE");
        envelope(mvc.perform(get("/api/system/users").with(user("manager").roles("SYSTEM_ADMIN")).accept("text/html")).andReturn(),406,"NOT_ACCEPTABLE");
    }
    @Test void internalErrorsAndErrorDispatchCannotLeakExceptionDetails() throws Exception {
        for(String path:List.of("unexpected","database")) {
            var result=mvc.perform(get("/test-response/"+path).with(user("manager").roles("SYSTEM_ADMIN"))).andReturn();
            envelope(result,path.equals("database")?503:500,path.equals("database")?"DATABASE_UNAVAILABLE":"INTERNAL_ERROR");
            assertThat(result.getResponse().getContentAsString()).doesNotContain("private-secret","stackTrace","SELECT");
        }
        var challenge=mvc.perform(get("/error").with(request -> { request.setDispatcherType(DispatcherType.ERROR); return request; })
                .requestAttr(RequestDispatcher.ERROR_STATUS_CODE,401)).andReturn();
        envelope(challenge,401,"UNAUTHENTICATED");
        assertThat(challenge.getResponse().getHeader("WWW-Authenticate")).startsWith("Basic ");
        envelope(mvc.perform(get("/error").with(request -> { request.setDispatcherType(DispatcherType.ERROR); return request; })
                .requestAttr(RequestDispatcher.ERROR_STATUS_CODE,500)).andReturn(),500,"INTERNAL_ERROR");
    }
    // 这些测试探针仅在专用测试profile出现，不会打入生产JAR。
    @RestController @Profile("response-contract-test")
    static class ProbeController {
        @GetMapping("/test-response/unexpected") void unexpected() { throw new IllegalArgumentException("private-secret"); }
        @GetMapping("/test-response/database") void database() {
            throw new org.springframework.dao.DataAccessResourceFailureException("SELECT private-secret");
        }
    }
}
