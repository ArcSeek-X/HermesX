package hermesx.system;

import com.fasterxml.jackson.databind.*;
import hermesx.system.service.IOrganizationService;
import hermesx.system.service.IMenuService;
import hermesx.system.dto.OrganizationWriteDTO;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import java.nio.file.*;
import java.util.*;
import static org.assertj.core.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.*;

/** 真实SQLite与完整HTTP链路：重点验证关系和事务，而不是mock Mapper证明调用过。 */
@SpringBootTest(properties={"spring.cloud.nacos.discovery.enabled=false",
    "spring.sql.init.mode=always",
    "spring.sql.init.schema-locations=classpath:db/hrs-system-service.sql"})
@AutoConfigureMockMvc
@WithMockUser(username="tree-manager",roles="SYSTEM_ADMIN")
class TreeManagementApiIntegrationTest {
    static final String ORGS="/api/system/organizations", MENUS="/api/system/menus";
    static final Path DATABASE;
    static {
        try { DATABASE=Files.createTempFile("hermesx-trees-", ".db"); }
        catch (java.io.IOException e) { throw new ExceptionInInitializerError(e); }
    }
    @DynamicPropertySource static void properties(DynamicPropertyRegistry r) {
        r.add("HRS_SYSTEM_DB_URL",()->"jdbc:sqlite:"+DATABASE);
        r.add("HRS_SYSTEM_ADMIN_USERNAME",()->"tree-manager");
        r.add("HRS_SYSTEM_ADMIN_PASSWORD",()->"test-only-tree-password");
    }
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;
    @Autowired JdbcTemplate jdbc;
    @Autowired IOrganizationService organizations;
    @Autowired IMenuService menus;
    @BeforeEach void clear() {
        jdbc.update("DELETE FROM hrs_system_user");
        jdbc.update("DELETE FROM hrs_system_organization");
        jdbc.update("DELETE FROM hrs_system_menu");
    }
    @AfterAll static void cleanup() throws Exception { Files.deleteIfExists(DATABASE); }
    Map<String,Object> organization(String name,long parent) {
        return new LinkedHashMap<>(Map.of("name",name,"parentId",parent));
    }
    Map<String,Object> menu(String name,String type,long parent) {
        String code="test-"+Integer.toUnsignedString(name.hashCode());
        var data=new LinkedHashMap<String,Object>(Map.of("menuCode",code,"menuName",name,"menuType",type,"menuParentId",parent));
        if (type.equals("page")) {
            data.put("menuRoutePath","/"+code);
            data.put("menuPagePath","pages/HomePage");
        }
        return data;
    }
    long create(String url,Map<String,Object> data) throws Exception {
        var result=mvc.perform(post(url).with(csrf()).contentType("application/json").content(json.writeValueAsString(data)))
                .andExpect(status().isCreated()).andExpect(jsonPath("$.resultData.deleteFlag").doesNotExist())
                .andExpect(jsonPath("$.resultData.createBy").value("tree-manager")).andReturn();
        return json.readTree(result.getResponse().getContentAsString()).get("resultData").get("id").asLong();
    }
    JsonNode tree(String url) throws Exception {
        return json.readTree(mvc.perform(get(url)).andExpect(status().isOk()).andReturn().getResponse().getContentAsString()).get("resultData");
    }
    void put(String url,Map<String,Object> data,int status) throws Exception {
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put(url).with(csrf())
                .contentType("application/json").content(json.writeValueAsString(data))).andExpect(status().is(status));
    }

    @Test void departmentCrudAndNonEmptyDeletion() throws Exception {
        long root=create(ORGS,organization("研发",0));
        long child=create(ORGS,organization("分析组",root));
        mvc.perform(delete(ORGS+"/"+root).with(csrf())).andExpect(status().isConflict()).andExpect(jsonPath("$.resultCode").value("HAS_CHILDREN"));
        assertThat(tree(ORGS+"/tree").get(0).get("children").get(0).get("id").asLong()).isEqualTo(child);
        var update=organization("新分析组",root);update.put("status",0);update.put("sort",3);update.put("leader","负责人");
        put(ORGS+"/"+child,update,200);
        mvc.perform(get(ORGS+"/"+child)).andExpect(status().isOk()).andExpect(jsonPath("$.resultData.name").value("新分析组"))
                .andExpect(jsonPath("$.resultData.status").value(0)).andExpect(jsonPath("$.resultData.leader").value("负责人"));
        mvc.perform(delete(ORGS+"/"+child).with(csrf())).andExpect(status().isOk()).andExpect(jsonPath("$.resultCode").value("200")).andExpect(jsonPath("$.resultData").value(true));
        assertThat(jdbc.queryForObject("SELECT delete_flag FROM hrs_system_organization WHERE id=?",Integer.class,child)).isEqualTo(1);
        mvc.perform(get(ORGS+"/"+child)).andExpect(status().isNotFound());
        mvc.perform(delete(ORGS+"/"+child).with(csrf())).andExpect(status().isNotFound());
        put(ORGS+"/"+child,update,404);
        mvc.perform(delete(ORGS+"/"+root).with(csrf())).andExpect(status().isOk()).andExpect(jsonPath("$.resultCode").value("200")).andExpect(jsonPath("$.resultData").value(true));
        assertThat(tree(ORGS+"/tree").size()).isZero();
    }

    @Test void movingDepartmentUpdatesEveryDescendantAndRejectsCyclesAtomically() throws Exception {
        long a=create(ORGS,organization("A",0)), b=create(ORGS,organization("B",a));
        long c=create(ORGS,organization("C",b)), d=create(ORGS,organization("D",0));
        put(ORGS+"/"+b,organization("B moved",d),200);
        assertThat(jdbc.queryForObject("SELECT ancestors FROM hrs_system_organization WHERE id=?",String.class,b)).isEqualTo(""+d);
        assertThat(jdbc.queryForObject("SELECT ancestors FROM hrs_system_organization WHERE id=?",String.class,c)).isEqualTo(d+","+b);
        put(ORGS+"/"+d,organization("must rollback",c),409);
        put(ORGS+"/"+b,organization("self",b),409);
        put(ORGS+"/"+b,organization("missing",999999),409);
        assertThat(jdbc.queryForObject("SELECT dept_name FROM hrs_system_organization WHERE id=?",String.class,d)).isEqualTo("D");
        assertThat(jdbc.queryForObject("SELECT parent_id FROM hrs_system_organization WHERE id=?",Long.class,d)).isZero();
        mvc.perform(delete(ORGS+"/"+a).with(csrf())).andExpect(status().isOk()).andExpect(jsonPath("$.resultCode").value("200")).andExpect(jsonPath("$.resultData").value(true));
        mvc.perform(post(ORGS).with(csrf()).contentType("application/json").content(json.writeValueAsString(organization("bad",a))))
                .andExpect(status().isConflict());
    }

    @Test void treeFiltersKeepAncestorsSortAndExactScope() throws Exception {
        var rootData=organization("目录祖先",0);rootData.put("status",0);rootData.put("enterpriseId",100);rootData.put("organizationId",2001);
        long root=create(ORGS,rootData);
        var child=organization("命中部门",root);child.put("sort",2);child.put("enterpriseId",100);child.put("organizationId",2001);
        long first=create(ORGS,child);child.put("name","命中靠前");child.put("sort",1);long second=create(ORGS,child);
        create(ORGS,organization("其他范围",0));
        JsonNode filtered=tree(ORGS+"/tree?keyword=命中&status=1&enterpriseId=100&organizationId=2001");
        assertThat(filtered.size()).isEqualTo(1);
        assertThat(filtered.get(0).get("id").asLong()).isEqualTo(root);
        assertThat(filtered.get(0).get("status").asInt()).isZero(); // 祖先仅为上下文，不伪装为命中条件。
        assertThat(filtered.get(0).get("children").get(0).get("id").asLong()).isEqualTo(second);
        assertThat(filtered.get(0).get("children").get(1).get("id").asLong()).isEqualTo(first);
        assertThat(tree(ORGS+"/tree?enterpriseId=101").size()).isZero();
        assertThat(tree(ORGS+"/tree?keyword=%27%20OR%201=1--").size()).isZero();
        // 已有子树的归属不能单独改，否则父子树及关联用户将跨范围。
        child.put("enterpriseId",101);put(ORGS+"/"+first,child,409);
        mvc.perform(post(ORGS).with(csrf()).contentType("application/json").content(json.writeValueAsString(child)))
                .andExpect(status().isConflict()).andExpect(jsonPath("$.resultCode").value("SCOPE_MISMATCH"));
    }

    @Test void departmentAssignmentGuardsBothUserWritesAndDepartmentDeletion() throws Exception {
        var department=organization("有用户的部门",0);department.put("enterpriseId",100);department.put("organizationId",2001);
        long id=create(ORGS,department);
        var user=new LinkedHashMap<String,Object>(Map.of("username","department-user","password","test-user-password","nickname","成员",
                "deptId",id,"enterpriseId",100,"organizationId",2001));
        long userId=create("/api/system/users",user);
        mvc.perform(delete(ORGS+"/"+id).with(csrf())).andExpect(status().isConflict()).andExpect(jsonPath("$.resultCode").value("DEPARTMENT_IN_USE"));
        user.put("username","bad-scope");user.put("enterpriseId",101);
        mvc.perform(post("/api/system/users").with(csrf()).contentType("application/json").content(json.writeValueAsString(user)))
                .andExpect(status().isConflict());
        put("/api/system/users/"+userId,new LinkedHashMap<>(Map.of("nickname","bad update","status",1,"deptId",id,"enterpriseId",101,"organizationId",2001)),409);
        mvc.perform(delete("/api/system/users/"+userId).with(csrf())).andExpect(status().isOk()).andExpect(jsonPath("$.resultCode").value("200")).andExpect(jsonPath("$.resultData").value(true));
        mvc.perform(delete(ORGS+"/"+id).with(csrf())).andExpect(status().isOk()).andExpect(jsonPath("$.resultCode").value("200")).andExpect(jsonPath("$.resultData").value(true));
        user.put("enterpriseId",100);
        mvc.perform(post("/api/system/users").with(csrf()).contentType("application/json").content(json.writeValueAsString(user)))
                .andExpect(status().isNotFound());
    }












    @Test void validationAndSecurityApplyToBothModules() throws Exception {
        for (String url:List.of(ORGS,MENUS)) {
            mvc.perform(get(url+"/tree").with(anonymous())).andExpect(status().isUnauthorized());
            mvc.perform(get(url+"/tree").with(user("ordinary").roles("USER"))).andExpect(status().isForbidden());
            mvc.perform(post(url).contentType("application/json").content("{}")).andExpect(status().isForbidden());
            for (String body:List.of("{}","{\"name\":\" \",\"type\":\"menu\"}","{\"name\":\"x\",\"type\":\"menu\",\"enterpriseId\":0}")) {
                mvc.perform(post(url).with(csrf()).contentType("application/json").content(body)).andExpect(status().isBadRequest());
            }
            mvc.perform(get(url+"/tree?status=2")).andExpect(status().isBadRequest());
            mvc.perform(get(url+"/-1")).andExpect(status().isBadRequest());
            mvc.perform(delete(url+"/999999").with(csrf())).andExpect(status().isNotFound());
        }
        // 直接调用业务服务也必须检查权限，不能只依赖Controller。
        org.springframework.security.core.context.SecurityContextHolder.clearContext();
        assertThatThrownBy(()->organizations.get(1)).isInstanceOf(org.springframework.security.access.AccessDeniedException.class);
        assertThatThrownBy(()->menus.get(1)).isInstanceOf(org.springframework.security.access.AccessDeniedException.class);
    }
    @Test void overlongDescendantPathRollsBackTheEntireDepartmentMove() throws Exception {
        // 祖先路径接近500字符：根节点能移动，但孙节点会超限，用真实事务检查全部回滚。
        jdbc.update("INSERT INTO hrs_system_organization(id,parent_id,ancestors,dept_name,create_by,update_by) VALUES (101,0,'','source','fixture','fixture')");
        jdbc.update("INSERT INTO hrs_system_organization(id,parent_id,ancestors,dept_name,create_by,update_by) VALUES (102,101,'101','child','fixture','fixture')");
        jdbc.update("INSERT INTO hrs_system_organization(id,parent_id,ancestors,dept_name,create_by,update_by) VALUES (103,102,'101,102','leaf','fixture','fixture')");
        long parent=0; String ancestors="";
        for (int i=0;i<26;i++) {
            long id=900000000000000000L+i;
            jdbc.update("INSERT INTO hrs_system_organization(id,parent_id,ancestors,dept_name,create_by,update_by) VALUES (?,?,?,?,?,?)",
                    id,parent,ancestors,"deep-"+i,"fixture","fixture");
            ancestors=ancestors.isEmpty()?Long.toString(id):ancestors+","+id; parent=id;
        }
        put(ORGS+"/101",organization("must rollback",parent),409);
        assertThat(jdbc.queryForObject("SELECT dept_name FROM hrs_system_organization WHERE id=101",String.class)).isEqualTo("source");
        assertThat(jdbc.queryForObject("SELECT parent_id FROM hrs_system_organization WHERE id=101",Long.class)).isZero();
        assertThat(jdbc.queryForObject("SELECT ancestors FROM hrs_system_organization WHERE id=102",String.class)).isEqualTo("101");
        assertThat(jdbc.queryForObject("SELECT ancestors FROM hrs_system_organization WHERE id=103",String.class)).isEqualTo("101,102");
    }

    @Test void fieldLimitsAndUnknownInternalFieldsAreRejected() throws Exception {
        var badEmail=organization("email",0);badEmail.put("email","not-an-email");
        var longName=organization("x".repeat(101),0);
        var audit=organization("audit",0);audit.put("createBy","forged");
        var badParent=organization("parent",-1);
        for (var input:List.of(badEmail,longName,audit,badParent)) {
            mvc.perform(post(ORGS).with(csrf()).contentType("application/json").content(json.writeValueAsString(input)))
                    .andExpect(status().isBadRequest());
        }
        var badType=menu("type","unknown",0);
        var badVisible=menu("visible","module",0);badVisible.put("menuVisible","not-boolean");
        var longPath=menu("path","page",0);longPath.put("menuRoutePath","/"+"x".repeat(201));
        var deleteFlag=menu("deleted","module",0);deleteFlag.put("deleteFlag",1);
        for (var input:List.of(badType,badVisible,longPath,deleteFlag)) {
            mvc.perform(post(MENUS).with(csrf()).contentType("application/json").content(json.writeValueAsString(input)))
                    .andExpect(status().isBadRequest());
        }
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM hrs_system_organization",Integer.class)).isZero();
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM hrs_system_menu",Integer.class)).isZero();
    }

}
