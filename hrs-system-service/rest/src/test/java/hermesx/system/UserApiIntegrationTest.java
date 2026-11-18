package hermesx.system;

import com.fasterxml.jackson.databind.ObjectMapper;
import hermesx.system.service.IUserService;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import java.nio.file.*;
import static org.assertj.core.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.*;

/** 使用真实 SQLite 临时文件，贯穿 HTTP→Service→DAO，不 mock 数据访问或业务规则。 */
@SpringBootTest
@AutoConfigureMockMvc
class UserApiIntegrationTest {
    static final Path DATABASE;
    static {
        try { DATABASE = Files.createTempFile("hermesx-users-", ".db"); }
        catch (java.io.IOException e) { throw new ExceptionInInitializerError(e); }
    }
    @DynamicPropertySource static void properties(DynamicPropertyRegistry r) {
        r.add("HRS_SYSTEM_DB_URL", () -> "jdbc:sqlite:" + DATABASE);
        r.add("HRS_SYSTEM_ADMIN_USERNAME", () -> "test-manager");
        r.add("HRS_SYSTEM_ADMIN_PASSWORD", () -> "test-only-manager-password");
    }
    @Autowired MockMvc mvc;
    @Autowired JdbcTemplate jdbc;
    @Autowired ObjectMapper json;
    @Autowired PasswordEncoder encoder;
    @Autowired IUserService service;
    @BeforeEach void clear() { jdbc.update("DELETE FROM hrs_system_user"); }
    @AfterAll static void cleanup() throws Exception { Files.deleteIfExists(DATABASE); }
    String createBody(String username) {
        return "{\"username\":\"" + username + "\",\"password\":\"learning-secret\",\"nickname\":\"学习用户\",\"deptId\":7}";
    }
    long create(String username) throws Exception {
        String body = mvc.perform(post("/api/system/users").with(httpBasic("test-manager", "test-only-manager-password"))
                .with(csrf()).contentType("application/json").content(createBody(username)))
                .andExpect(status().isCreated()).andExpect(jsonPath("$.password").doesNotExist())
                .andExpect(jsonPath("$.status").value(1)).andReturn().getResponse().getContentAsString();
        return json.readTree(body).get("id").asLong();
    }
    @Test void fullLifecycleAndDatabaseState() throws Exception {
        long id = create("learner");
        String hash = jdbc.queryForObject("SELECT password FROM hrs_system_user WHERE id=?", String.class, id);
        assertThat(hash).isNotEqualTo("learning-secret");
        assertThat(encoder.matches("learning-secret", hash)).isTrue();
        assertThat(jdbc.queryForObject("SELECT create_by FROM hrs_system_user WHERE id=?",String.class,id)).isEqualTo("test-manager");
        mvc.perform(get("/api/system/users/{id}",id).with(user("manager").roles("SYSTEM_ADMIN")))
                .andExpect(status().isOk()).andExpect(jsonPath("$.deptId").value(7)).andExpect(jsonPath("$.password").doesNotExist());
        mvc.perform(put("/api/system/users/{id}",id).with(user("editor").roles("SYSTEM_ADMIN")).with(csrf())
                .contentType("application/json").content("{\"nickname\":\"新昵称\",\"status\":0}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.nickname").value("新昵称"))
                .andExpect(jsonPath("$.deptId").isEmpty()).andExpect(jsonPath("$.updateBy").value("editor"));
        assertThat(jdbc.queryForObject("SELECT password FROM hrs_system_user WHERE id=?",String.class,id)).isEqualTo(hash);
        mvc.perform(delete("/api/system/users/{id}",id).with(user("manager").roles("SYSTEM_ADMIN")).with(csrf()))
                .andExpect(status().isNoContent());
        assertThat(jdbc.queryForObject("SELECT delete_flag FROM hrs_system_user WHERE id=?",Integer.class,id)).isEqualTo(1);
        mvc.perform(get("/api/system/users/{id}",id).with(user("manager").roles("SYSTEM_ADMIN"))).andExpect(status().isNotFound());
        mvc.perform(get("/api/system/users").with(user("manager").roles("SYSTEM_ADMIN")))
                .andExpect(status().isOk()).andExpect(jsonPath("$.total").value(0));
        mvc.perform(delete("/api/system/users/{id}",id).with(user("manager").roles("SYSTEM_ADMIN")).with(csrf()))
                .andExpect(status().isNotFound());
        mvc.perform(post("/api/system/users").with(user("manager").roles("SYSTEM_ADMIN")).with(csrf())
                .contentType("application/json").content(createBody("learner"))).andExpect(status().isConflict());
    }
    @Test void duplicateAndPaginationAndLiteralSearch() throws Exception {
        long first = create("first"); create("second");
        mvc.perform(post("/api/system/users").with(user("manager").roles("SYSTEM_ADMIN")).with(csrf())
                .contentType("application/json").content(createBody("first"))).andExpect(status().isConflict());
        mvc.perform(get("/api/system/users?pageSize=1&page=2&status=1&deptId=7").with(user("manager").roles("SYSTEM_ADMIN")))
                .andExpect(status().isOk()).andExpect(jsonPath("$.total").value(2))
                .andExpect(jsonPath("$.rows[0].id").value(first));
        mvc.perform(get("/api/system/users").param("keyword", "' OR 1=1 --").with(user("manager").roles("SYSTEM_ADMIN")))
                .andExpect(status().isOk()).andExpect(jsonPath("$.total").value(0));
    }
    @Test void authenticationAuthorizationAndCsrf() throws Exception {
        mvc.perform(get("/api/system/users")).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/system/users").with(httpBasic("test-manager","wrong"))).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/system/users").with(user("ordinary").roles("USER"))).andExpect(status().isForbidden());
        mvc.perform(post("/api/system/users").with(user("manager").roles("SYSTEM_ADMIN"))
                .contentType("application/json").content(createBody("blocked"))).andExpect(status().isForbidden());
        assertThatThrownBy(() -> service.get(1)).isInstanceOf(org.springframework.security.access.AccessDeniedException.class);
        mvc.perform(get("/api/system/users/csrf").with(httpBasic("test-manager","test-only-manager-password")))
                .andExpect(status().isOk()).andExpect(jsonPath("$.token").isNotEmpty());
    }
    @Test void invalidInputCannotWriteOrLeakPassword() throws Exception {
        for (String body : new String[]{"{}", createBody("x").replace("learning-secret","short"),
                createBody("x").replace("学习用户"," "), createBody("x").replace("7}","0}"),
                createBody("x").replace("7}","7,\"status\":2}"),
                createBody("x").replace("7}","7,\"roleIds\":[1]}"),
                createBody("x").replace("learning-secret","中".repeat(25))}) {
            mvc.perform(post("/api/system/users").with(user("manager").roles("SYSTEM_ADMIN")).with(csrf())
                    .contentType("application/json").content(body)).andExpect(status().isBadRequest())
                    .andExpect(content().string(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("learning-secret"))));
        }
        for (String query : new String[]{"page=0","pageSize=101","status=2","deptId=-1"}) {
            mvc.perform(get("/api/system/users?"+query).with(user("manager").roles("SYSTEM_ADMIN"))).andExpect(status().isBadRequest());
        }
        mvc.perform(get("/api/system/users/-1").with(user("manager").roles("SYSTEM_ADMIN"))).andExpect(status().isBadRequest());
        mvc.perform(put("/api/system/users/999").with(user("manager").roles("SYSTEM_ADMIN")).with(csrf())
                .contentType("application/json").content("{\"nickname\":\"未知\",\"status\":1}"))
                .andExpect(status().isNotFound());
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM hrs_system_user",Integer.class)).isZero();
    }
    @Test void realBasicAndCsrfTokensSupportSuccessiveWrites() throws Exception {
        // 不使用 with(csrf())：真实获取 token 和 Cookie，覆盖认证后的 token 轮换。
        var first = mvc.perform(get("/api/system/users/csrf")
                .with(httpBasic("test-manager", "test-only-manager-password")))
                .andExpect(status().isOk()).andReturn();
        var session = (org.springframework.mock.web.MockHttpSession) first.getRequest().getSession(false);
        String token = json.readTree(first.getResponse().getContentAsString()).get("token").asText();
        var created = mvc.perform(post("/api/system/users").session(session)
                .with(httpBasic("test-manager", "test-only-manager-password"))
                .header("X-CSRF-TOKEN", token).contentType("application/json").content(createBody("csrf-user")))
                .andExpect(status().isCreated()).andReturn();
        long id = json.readTree(created.getResponse().getContentAsString()).get("id").asLong();
        var next = mvc.perform(get("/api/system/users/csrf").session(session)
                .with(httpBasic("test-manager", "test-only-manager-password")))
                .andExpect(status().isOk()).andReturn();
        token = json.readTree(next.getResponse().getContentAsString()).get("token").asText();
        mvc.perform(delete("/api/system/users/{id}", id).session(session)
                .with(httpBasic("test-manager", "test-only-manager-password"))
                .header("X-CSRF-TOKEN", token)).andExpect(status().isNoContent());
    }

    @Autowired hermesx.system.dao.UserMapper mapper;
    @Autowired org.springframework.transaction.PlatformTransactionManager transactionManager;

    @Test void mapperInsertReturningParticipatesInSpringRollback() {
        // INSERT RETURNING 在 XML 中用 select 标签，但必须遵守写事务及回滚。
        var transaction = new org.springframework.transaction.support.TransactionTemplate(transactionManager);
        assertThatThrownBy(() -> transaction.execute(status -> {
            long id = mapper.insert("rollback-user", encoder.encode("temporary-secret"), "回滚用户",
                    null, null, null, null, null, 1, "test-operator");
            assertThat(mapper.find(id)).isPresent();
            throw new IllegalStateException("触发回滚");
        })).isInstanceOf(IllegalStateException.class);
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM hrs_system_user WHERE username=?",
                Integer.class, "rollback-user")).isZero();
    }

    @Test void enterpriseAndOrganizationArePersistedReturnedFilteredAndCleared() throws Exception {
        String body = createBody("scoped").replace("7}", "7,\"enterpriseId\":100,\"organizationId\":2001}");
        var created = mvc.perform(post("/api/system/users").with(user("manager").roles("SYSTEM_ADMIN")).with(csrf())
                .contentType("application/json").content(body)).andExpect(status().isCreated())
                .andExpect(jsonPath("$.enterpriseId").value(100))
                .andExpect(jsonPath("$.organizationId").value(2001)).andReturn();
        long id = json.readTree(created.getResponse().getContentAsString()).get("id").asLong();
        create("unassigned");
        assertThat(jdbc.queryForObject("SELECT enterprise_id FROM hrs_system_user WHERE id=?",Long.class,id)).isEqualTo(100L);
        assertThat(jdbc.queryForObject("SELECT organization_id FROM hrs_system_user WHERE id=?",Long.class,id)).isEqualTo(2001L);
        mvc.perform(get("/api/system/users/{id}", id).with(user("manager").roles("SYSTEM_ADMIN")))
                .andExpect(status().isOk()).andExpect(jsonPath("$.enterpriseId").value(100))
                .andExpect(jsonPath("$.organizationId").value(2001));
        for (String query : new String[]{"enterpriseId=100", "organizationId=2001", "enterpriseId=100&organizationId=2001"}) {
            mvc.perform(get("/api/system/users?"+query).with(user("manager").roles("SYSTEM_ADMIN")))
                    .andExpect(status().isOk()).andExpect(jsonPath("$.total").value(1))
                    .andExpect(jsonPath("$.rows[0].id").value(id));
        }
        mvc.perform(get("/api/system/users?enterpriseId=999&organizationId=2001").with(user("manager").roles("SYSTEM_ADMIN")))
                .andExpect(status().isOk()).andExpect(jsonPath("$.total").value(0));
        mvc.perform(put("/api/system/users/{id}",id).with(user("manager").roles("SYSTEM_ADMIN")).with(csrf())
                .contentType("application/json").content("{\"nickname\":\"改归属\",\"status\":1,\"enterpriseId\":101,\"organizationId\":2002}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.enterpriseId").value(101))
                .andExpect(jsonPath("$.organizationId").value(2002));
        mvc.perform(put("/api/system/users/{id}",id).with(user("manager").roles("SYSTEM_ADMIN")).with(csrf())
                .contentType("application/json").content("{\"nickname\":\"清空归属\",\"status\":1}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.enterpriseId").isEmpty())
                .andExpect(jsonPath("$.organizationId").isEmpty());
        assertThat(mapper.find(id).orElseThrow().enterpriseId()).isNull();
        assertThat(mapper.find(id).orElseThrow().organizationId()).isNull();
    }

    @Test void invalidEnterpriseAndOrganizationAreRejectedOnAllInputs() throws Exception {
        long id = create("validation");
        for (String field : new String[]{"enterpriseId", "organizationId"}) {
            for (long value : new long[]{0, -1}) {
                mvc.perform(post("/api/system/users").with(user("manager").roles("SYSTEM_ADMIN")).with(csrf())
                        .contentType("application/json").content(createBody("bad").replace("7}", "7,\""+field+"\":"+value+"}")))
                        .andExpect(status().isBadRequest());
                mvc.perform(put("/api/system/users/{id}",id).with(user("manager").roles("SYSTEM_ADMIN")).with(csrf())
                        .contentType("application/json").content("{\"nickname\":\"无效\",\"status\":1,\""+field+"\":"+value+"}"))
                        .andExpect(status().isBadRequest());
                mvc.perform(get("/api/system/users?"+field+"="+value).with(user("manager").roles("SYSTEM_ADMIN")))
                        .andExpect(status().isBadRequest());
            }
        }
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM hrs_system_user",Integer.class)).isEqualTo(1);
    }

}
