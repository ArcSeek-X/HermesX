package hermesx.system;

import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import static org.assertj.core.api.Assertions.*;

/** 使用生产配置的 never：即使能找到正式脚本，完整应用启动也不得建表或改写已有数据。 */
@SpringBootTest(properties="spring.sql.init.schema-locations=classpath:db/hrs-system-service.sql")
class DatabaseInitializationIntegrationTest {
    static final Path DATABASE;
    static {
        try {
            DATABASE = Files.createTempFile("hermesx-no-auto-init-", ".db");
            var jdbc = new JdbcTemplate(new DriverManagerDataSource("jdbc:sqlite:" + DATABASE));
            jdbc.execute("CREATE TABLE startup_probe (id INTEGER PRIMARY KEY, value TEXT NOT NULL)");
            jdbc.update("INSERT INTO startup_probe VALUES (1,'keep-existing-data')");
        } catch (java.io.IOException e) {
            throw new ExceptionInInitializerError(e);
        }
    }

    @DynamicPropertySource static void properties(DynamicPropertyRegistry registry) {
        registry.add("HRS_SYSTEM_DB_URL", () -> "jdbc:sqlite:" + DATABASE);
        registry.add("HRS_SYSTEM_ADMIN_USERNAME", () -> "startup-test-manager");
        registry.add("HRS_SYSTEM_ADMIN_PASSWORD", () -> "test-only-startup-password");
        registry.add("spring.cloud.nacos.discovery.enabled", () -> "false");
    }

    @Autowired JdbcTemplate jdbc;
    @Autowired Environment environment;

    @Test void applicationStartsWithoutRunningDatabaseScripts() {
        assertThat(environment.getProperty("spring.sql.init.mode")).isEqualTo("never");
        assertThat(jdbc.queryForList("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", String.class))
                .containsExactly("startup_probe");
        assertThat(jdbc.queryForObject("SELECT value FROM startup_probe WHERE id=1", String.class))
                .isEqualTo("keep-existing-data");
    }

    @AfterAll static void cleanup() throws java.io.IOException { Files.deleteIfExists(DATABASE); }
}
