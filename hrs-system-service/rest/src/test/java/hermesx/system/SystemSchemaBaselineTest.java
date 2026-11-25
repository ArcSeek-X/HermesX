package hermesx.system;

import java.nio.file.Path;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import static org.assertj.core.api.Assertions.*;

/** 验证正式SQL的基线与组织结构升级，使用临时SQLite。重复部署由手动工具的历史记录控制。 */
class SystemSchemaBaselineTest {
    @TempDir Path directory;

    @Test void organizationMigrationPreservesPrimaryKeysParentPathsAndUserLinks() throws Exception {
        var source = new DriverManagerDataSource("jdbc:sqlite:" + directory.resolve("system.db"));
        String sql = new ClassPathResource("db/hrs-system-service.sql").getContentAsString(StandardCharsets.UTF_8);
        int migrationStart = sql.indexOf("-- BEGIN ORGANIZATION_20261124");
        var baseline = new ResourceDatabasePopulator(new ByteArrayResource(sql.substring(0,migrationStart).getBytes(StandardCharsets.UTF_8)));
        baseline.execute(source);
        var jdbc = new JdbcTemplate(source);
        jdbc.update("INSERT INTO hrs_system_organization(id,dept_name,enterprise_id,organization_id,create_by,update_by) "
                + "VALUES (7,'总部',100,2001,'fixture','fixture')");
        jdbc.update("INSERT INTO hrs_system_organization(id,parent_id,ancestors,dept_name,email,phone,leader,enterprise_id,organization_id,delete_flag,create_by,update_by) "
                + "VALUES (8,7,'7','研发部','rnd@example.com','010123','负责人',100,2001,1,'fixture','fixture')");
        jdbc.update("INSERT INTO hrs_system_user(username,password,nickname,dept_id,enterprise_id,organization_id,create_by,update_by) "
                + "VALUES ('learner','test-hash','学习用户',8,100,2001,'fixture','fixture')");
        var users = jdbc.queryForList("SELECT * FROM hrs_system_user ORDER BY id");
        baseline.execute(source);
        new ResourceDatabasePopulator(new ByteArrayResource(sql.substring(migrationStart).getBytes(StandardCharsets.UTF_8))).execute(source);
        assertThat(jdbc.queryForList("SELECT * FROM hrs_system_user ORDER BY id")).isEqualTo(users);
        var department = jdbc.queryForMap("SELECT * FROM hrs_system_organization WHERE organization_id=8");
        assertThat(department).containsEntry("organization_name","研发部").containsEntry("ancestors","7")
                .containsEntry("organization_email","rnd@example.com").containsEntry("organization_phone","010123")
                .containsEntry("organization_leader","负责人").containsEntry("delete_flag",1)
                .containsEntry("organization_short_name",null).doesNotContainKey("id");
        assertThat(((Number)department.get("parent_id")).longValue()).isEqualTo(7);
        assertThat(jdbc.queryForObject("PRAGMA integrity_check", String.class)).isEqualTo("ok");
        jdbc.update("INSERT INTO hrs_system_organization(organization_name,create_by,update_by) VALUES ('新组织','fixture','fixture')");
        assertThat(jdbc.queryForObject("SELECT organization_id FROM hrs_system_organization WHERE organization_name='新组织'",Long.class)).isGreaterThan(8);
        // 组织迁移不改变用户唯一性与主键。
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
