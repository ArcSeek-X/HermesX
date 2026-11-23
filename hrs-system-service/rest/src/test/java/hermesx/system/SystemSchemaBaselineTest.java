package hermesx.system;

import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.core.io.ClassPathResource;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import static org.assertj.core.api.Assertions.*;

/** 使用同一份正式 SQL 和真实 SQLite，验证新库基线；不再模拟已移除的旧版本升级。 */
class SystemSchemaBaselineTest {
    @TempDir Path directory;

    @Test void repeatedBaselinePreservesSchemaDataAndAllocatedIds() {
        var source = new DriverManagerDataSource("jdbc:sqlite:" + directory.resolve("system.db"));
        var baseline = new ResourceDatabasePopulator(new ClassPathResource("db/hrs-system-service.sql"));
        baseline.execute(source);
        var jdbc = new JdbcTemplate(source);
        jdbc.update("INSERT INTO hrs_system_user(username,password,nickname,delete_flag,create_by,update_by) "
                + "VALUES ('learner','test-hash','学习用户',1,'fixture','fixture')");
        jdbc.update("INSERT INTO hrs_system_organization(dept_name,create_by,update_by) "
                + "VALUES ('研发部','fixture','fixture')");
        jdbc.update("INSERT INTO hrs_system_menu(menu_code,menu_name,menu_type,create_by,update_by) "
                + "VALUES ('product','产品','module','fixture','fixture')");
        var schema = jdbc.queryForList("SELECT type,name,sql FROM sqlite_master ORDER BY type,name");
        var users = jdbc.queryForList("SELECT * FROM hrs_system_user ORDER BY id");
        var organizations = jdbc.queryForList("SELECT * FROM hrs_system_organization ORDER BY id");
        var menus = jdbc.queryForList("SELECT * FROM hrs_system_menu ORDER BY id");

        baseline.execute(source);

        assertThat(jdbc.queryForList("SELECT type,name,sql FROM sqlite_master ORDER BY type,name")).isEqualTo(schema);
        assertThat(jdbc.queryForList("SELECT * FROM hrs_system_user ORDER BY id")).isEqualTo(users);
        assertThat(jdbc.queryForList("SELECT * FROM hrs_system_organization ORDER BY id")).isEqualTo(organizations);
        assertThat(jdbc.queryForList("SELECT * FROM hrs_system_menu ORDER BY id")).isEqualTo(menus);
        assertThat(jdbc.queryForObject("PRAGMA integrity_check", String.class)).isEqualTo("ok");
        // 已删除账号仍占用名称；再次执行基线不能让账号唯一性失效。
        assertThatThrownBy(() -> jdbc.update("INSERT INTO hrs_system_user(username,password,nickname,create_by,update_by) "
                + "VALUES ('learner','other-hash','重复账号','fixture','fixture')"))
                .isInstanceOf(DataAccessException.class);
        jdbc.update("INSERT INTO hrs_system_user(username,password,nickname,create_by,update_by) "
                + "VALUES ('second','test-hash','新用户','fixture','fixture')");
        assertThat(jdbc.queryForObject("SELECT id FROM hrs_system_user WHERE username='second'", Long.class))
                .isGreaterThan(((Number) users.get(0).get("id")).longValue());
    }

    @Test void activeMenuKeysStayUniqueAcrossRepeatedSoftDeleteAndRecreate() {
        var source = new DriverManagerDataSource("jdbc:sqlite:" + directory.resolve("menu.db"));
        new ResourceDatabasePopulator(new ClassPathResource("db/hrs-system-service.sql")).execute(source);
        var jdbc = new JdbcTemplate(source);
        jdbc.update("INSERT INTO hrs_system_menu(menu_code,menu_name,menu_type,create_by,update_by) "
                + "VALUES ('product','产品','module','fixture','fixture')");
        long parent = jdbc.queryForObject("SELECT id FROM hrs_system_menu WHERE menu_code='product'", Long.class);
        String insert = "INSERT INTO hrs_system_menu(menu_parent_id,menu_code,menu_name,menu_type,menu_route_path,"
                + "menu_page_path,create_by,update_by) VALUES (?,'kline','K线','page','/stock/kline','pages/Kline','fixture','fixture')";
        jdbc.update(insert, parent);
        assertThatThrownBy(() -> jdbc.update(insert, parent)).isInstanceOf(DataAccessException.class);
        assertThatThrownBy(() -> jdbc.update("INSERT INTO hrs_system_menu(menu_parent_id,menu_code,menu_name,menu_type,"
                + "menu_route_path,menu_page_path,create_by,update_by) "
                + "VALUES (?,'another','重复路径','page','/stock/kline','pages/Other','fixture','fixture')", parent))
                .isInstanceOf(DataAccessException.class);
        for (int i = 0; i < 2; i++) {
            jdbc.update("UPDATE hrs_system_menu SET delete_flag=1 WHERE menu_code='kline' AND delete_flag=0");
            jdbc.update(insert, parent);
        }
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM hrs_system_menu WHERE menu_code='kline' AND delete_flag=1", Integer.class))
                .isEqualTo(2);
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM hrs_system_menu WHERE menu_code='kline' AND delete_flag=0", Integer.class))
                .isEqualTo(1);
    }
}
