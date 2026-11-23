package hermesx.system;

import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import static org.assertj.core.api.Assertions.*;

/** 用真实旧版本表验证升级，不能只证明新建数据库可用。 */
class UserSchemaMigrationTest {
    @TempDir Path directory;

    @Test void upgradeKeepsExistingUsersAndAddsNullableConstrainedColumns() {
        var source = new DriverManagerDataSource("jdbc:sqlite:" + directory.resolve("old-users.db"));
        new ResourceDatabasePopulator(new ClassPathResource("db/user_schema_before_scope.sql")).execute(source);
        var jdbc = new JdbcTemplate(source);
        jdbc.update("INSERT INTO hrs_system_user(username,password,nickname) VALUES (?,?,?)",
                "existing", "existing-hash", "原用户");
        jdbc.update("INSERT INTO hrs_system_user(username,password,nickname,deleted) VALUES (?,?,?,1)",
                "deleted-user", "deleted-hash", "已删除用户");
        new ResourceDatabasePopulator(new ClassPathResource(
                "db/migration/V2__add_user_enterprise_organization.sql")).execute(source);
        new ResourceDatabasePopulator(new ClassPathResource(
                "db/migration/V3__rename_user_delete_flag.sql")).execute(source);
        assertThat(jdbc.queryForObject("SELECT delete_flag FROM hrs_system_user WHERE username=?",
                Integer.class, "existing")).isZero();
        assertThat(jdbc.queryForObject("SELECT delete_flag FROM hrs_system_user WHERE username=?",
                Integer.class, "deleted-user")).isEqualTo(1);
        assertThat(jdbc.queryForList("PRAGMA table_info(hrs_system_user)").stream()
                .map(column -> column.get("name"))).doesNotContain("deleted");
        // 模拟升级后再次启动：初始化脚本不会删表或覆盖旧数据。
        new ResourceDatabasePopulator(new ClassPathResource("db/schema.sql")).execute(source);
        var row = jdbc.queryForMap("SELECT * FROM hrs_system_user WHERE username=?", "existing");
        assertThat(row.get("nickname")).isEqualTo("原用户");
        assertThat(row.get("password")).isEqualTo("existing-hash");
        assertThat(row.get("enterprise_id")).isNull();
        assertThat(row.get("organization_id")).isNull();
        jdbc.update("UPDATE hrs_system_user SET enterprise_id=?,organization_id=?", 100L, 2001L);
        assertThat(jdbc.queryForObject("SELECT organization_id FROM hrs_system_user WHERE username='existing'",Long.class)).isEqualTo(2001L);
        assertThatThrownBy(() -> jdbc.update("UPDATE hrs_system_user SET enterprise_id=0"))
                .isInstanceOf(org.springframework.dao.DataAccessException.class);
        assertThatThrownBy(() -> jdbc.update("UPDATE hrs_system_user SET organization_id=-1"))
                .isInstanceOf(org.springframework.dao.DataAccessException.class);
    }
    @Test void additiveTreeSchemaPreservesUsersAndIsSafeOnRestart() {
        var source=new DriverManagerDataSource("jdbc:sqlite:"+directory.resolve("existing-system.db"));
        new ResourceDatabasePopulator(new ClassPathResource("db/schema.sql")).execute(source);
        var jdbc=new JdbcTemplate(source);
        jdbc.update("INSERT INTO hrs_system_user(username,password,nickname,delete_flag) VALUES ('old-user','old-hash','旧用户',1)");
        var schema=new ResourceDatabasePopulator(new ClassPathResource("db/migration/V4__create_organization_and_menu.sql"));
        schema.execute(source);
        jdbc.update("INSERT INTO hrs_system_organization(dept_name,create_by,update_by) VALUES ('部门','fixture','fixture')");
        jdbc.update("INSERT INTO hrs_system_menu(menu_name,menu_type,create_by,update_by) VALUES ('菜单','dir','fixture','fixture')");
        // 再次初始化既不能删用户，也不能覆盖新节点。
        new ResourceDatabasePopulator(new ClassPathResource("db/schema.sql")).execute(source);
        schema.execute(source);
        assertThat(jdbc.queryForObject("SELECT password FROM hrs_system_user",String.class)).isEqualTo("old-hash");
        assertThat(jdbc.queryForObject("SELECT delete_flag FROM hrs_system_user",Integer.class)).isEqualTo(1);
        for (String table:java.util.List.of("hrs_system_organization","hrs_system_menu")) {
            assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM "+table,Integer.class)).isEqualTo(1);
            var columns=jdbc.queryForList("PRAGMA table_info("+table+")").stream().map(r->r.get("name")).toList();
            assertThat(columns).contains("enterprise_id","organization_id","delete_flag","create_by","update_time");
            assertThatThrownBy(()->jdbc.update("UPDATE "+table+" SET delete_flag=2"))
                    .isInstanceOf(org.springframework.dao.DataAccessException.class);
            assertThatThrownBy(()->jdbc.update("UPDATE "+table+" SET enterprise_id=-1"))
                    .isInstanceOf(org.springframework.dao.DataAccessException.class);
        }
    }

}
