package hermesx.system;

import com.fasterxml.jackson.databind.*;
import hermesx.system.service.IMenuService;
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
    "spring.sql.init.schema-locations=classpath:db/schema.sql,classpath:db/menu_target_test_schema.sql"})
@AutoConfigureMockMvc
@WithMockUser(username="tree-manager",roles="SYSTEM_ADMIN")
class MenuApiIntegrationTest {
    static final String MENUS="/api/system/menus";
    static final Path DATABASE;
    static {
        try { DATABASE=Files.createTempFile("hermesx-menu-", ".db"); }
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
    @Autowired IMenuService menus;
    @BeforeEach void clear() { jdbc.update("DELETE FROM hrs_system_menu"); }
    @AfterAll static void cleanup() throws Exception { Files.deleteIfExists(DATABASE); }
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

    Set<Long> ids(JsonNode nodes) {
        Set<Long> result=new HashSet<>();
        for (JsonNode node:nodes) {
            result.add(node.get("id").asLong());
            result.addAll(ids(node.get("children")));
        }
        return result;
    }


    @Test void menuCrudAndParentTypesAndSoftDeletion() throws Exception {
        long module=create(MENUS,menu("系统","module",0));
        long group=create(MENUS,menu("管理分组","group",module));
        long page=create(MENUS,menu("用户管理","page",group));
        mvc.perform(delete(MENUS+"/"+group).with(csrf())).andExpect(status().isConflict());
        assertThat(tree(MENUS+"/tree?keyword=用户管理").get(0).get("children").get(0).get("children").get(0).get("id").asLong()).isEqualTo(page);
        var update=menu("修改页面","page",group);
        update.put("menuPermission","system:user:edit");update.put("menuVisible",false);update.put("menuStatus",0);
        put(MENUS+"/"+page,update,200);
        mvc.perform(get(MENUS+"/"+page)).andExpect(status().isOk())
                .andExpect(jsonPath("$.resultData.menuPermission").value("system:user:edit"))
                .andExpect(jsonPath("$.resultData.menuVisible").value(false))
                .andExpect(jsonPath("$.resultData.menuStatus").value(0))
                .andExpect(jsonPath("$.resultData.children").isEmpty())
                .andExpect(jsonPath("$.resultData.parentId").doesNotExist())
                .andExpect(jsonPath("$.resultData.name").doesNotExist());
        put(MENUS+"/"+group,menu("非法改类型","page",module),409);
        for (var invalid:List.of(menu("分组根","group",0),menu("嵌套模块","module",module),menu("页面的孩子","page",page))) {
            mvc.perform(post(MENUS).with(csrf()).contentType("application/json").content(json.writeValueAsString(invalid)))
                    .andExpect(status().isConflict());
        }
        mvc.perform(delete(MENUS+"/"+page).with(csrf())).andExpect(status().isOk()).andExpect(jsonPath("$.resultData").value(true));
        assertThat(jdbc.queryForObject("SELECT delete_flag FROM hrs_system_menu WHERE id=?",Integer.class,page)).isEqualTo(1);
        put(MENUS+"/"+page,update,404);
        mvc.perform(delete(MENUS+"/"+group).with(csrf())).andExpect(status().isOk());
        mvc.perform(delete(MENUS+"/"+module).with(csrf())).andExpect(status().isOk());
        assertThat(tree(MENUS+"/tree").size()).isZero();
    }

    @Test void menuMovesAndScopeChangesCannotBreakHierarchy() throws Exception {
        long a=create(MENUS,menu("A","module",0)),b=create(MENUS,menu("B","group",a));
        long page=create(MENUS,menu("页面","page",b)),d=create(MENUS,menu("D","module",0));
        put(MENUS+"/"+b,menu("B moved","group",d),200);
        var nested=menu("嵌套组","group",b);long child=create(MENUS,nested);
        put(MENUS+"/"+b,menu("循环","group",child),409);
        put(MENUS+"/"+b,menu("自己","group",b),409);
        put(MENUS+"/"+b,menu("无父","group",999999),409);
        put(MENUS+"/"+b,menu("类型非法","page",d),409);
        assertThat(jdbc.queryForObject("SELECT menu_name FROM hrs_system_menu WHERE id=?",String.class,b)).isEqualTo("B moved");
        var scoped=menu("别的企业","module",0);scoped.put("enterpriseId",100);scoped.put("organizationId",2001);
        long other=create(MENUS,scoped);
        put(MENUS+"/"+page,menu("跨范围","page",other),409);
        assertThat(tree(MENUS+"/tree?enterpriseId=100&organizationId=2001").size()).isEqualTo(1);
        assertThat(tree(MENUS+"/tree?enterpriseId=999").size()).isZero();
        var missingPage=menu("缺路径","page",d);missingPage.remove("menuPagePath");
        mvc.perform(post(MENUS).with(csrf()).contentType("application/json").content(json.writeValueAsString(missingPage)))
                .andExpect(status().isBadRequest());
    }

    @Test void navigationPostReturnsManifestContractAndKeepsHiddenEnabledNodes() throws Exception {
        long module=create(MENUS,menu("产品","module",0));
        var data=menu("隐藏禁用页面","page",module);
        data.put("menuVisible",false); data.put("menuExpanded",true); data.put("menuStatus",1);
        data.put("menuSort",2); data.put("auth","protected"); data.put("exact",false);
        data.put("menuBadge","新"); data.put("menuPosition","footer");
        long page=create(MENUS,data);
        mvc.perform(post("/api/system/list-menu").with(csrf()))
                .andExpect(status().isOk()).andExpect(jsonPath("$.resultCode").value("200"))
                .andExpect(jsonPath("$.resultMsg").value("操作成功。"))
                .andExpect(jsonPath("$.resultData[0].menuType").value("module"))
                .andExpect(jsonPath("$.resultData[0].menuParentId").value(0))
                .andExpect(jsonPath("$.resultData[0].menuDescription").value(""))
                .andExpect(jsonPath("$.resultData[0].menuPosition").value("content"))
                .andExpect(jsonPath("$.resultData[0].menuExpanded").value(false))
                .andExpect(jsonPath("$.resultData[0].menuVisible").value(true))
                .andExpect(jsonPath("$.resultData[0].menuIcon").doesNotExist())
                .andExpect(jsonPath("$.resultData[0].children[0].id").value(page))
                .andExpect(jsonPath("$.resultData[0].children[0].menuParentId").value(module))
                .andExpect(jsonPath("$.resultData[0].children[0].menuVisible").value(false))
                .andExpect(jsonPath("$.resultData[0].children[0].menuExpanded").value(true))
                .andExpect(jsonPath("$.resultData[0].children[0].menuStatus").value(1))
                .andExpect(jsonPath("$.resultData[0].children[0].exact").value(false))
                .andExpect(jsonPath("$.resultData[0].children[0].auth").value("protected"))
                .andExpect(jsonPath("$.resultData[0].children[0].menuBadge").value("新"));
        mvc.perform(get("/api/system/list-menu")).andExpect(status().isMethodNotAllowed());
        mvc.perform(post("/api/system/list-menu")) // 新POST接口也不能绕过现有CSRF。
                .andExpect(status().isForbidden()).andExpect(jsonPath("$.resultCode").value("CSRF_INVALID"));
        mvc.perform(post("/api/system/list-menu").with(csrf()).with(anonymous())).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/system/list-menu").with(csrf()).with(user("ordinary").roles("USER")))
                .andExpect(status().isForbidden());
    }

    @Test void menuCodesAndPageRoutesAreUniqueAndCorruptedTreeFailsExplicitly() throws Exception {
        long module=create(MENUS,menu("模块","module",0));
        long page=create(MENUS,menu("页面","page",module));
        mvc.perform(post(MENUS).with(csrf()).contentType("application/json")
                .content(json.writeValueAsString(menu("页面","page",module))))
                .andExpect(status().isConflict()).andExpect(jsonPath("$.resultCode").value("MENU_CODE_EXISTS"));
        var duplicate=menu("其他页面","page",module);duplicate.put("menuRoutePath",menu("页面","page",module).get("menuRoutePath"));
        mvc.perform(post(MENUS).with(csrf()).contentType("application/json").content(json.writeValueAsString(duplicate)))
                .andExpect(status().isConflict()).andExpect(jsonPath("$.resultCode").value("MENU_ROUTE_EXISTS"));
        // 模拟存量坏数据：不能输出缺失父节点的树，也不能返回空数组掩盖异常。
        jdbc.update("UPDATE hrs_system_menu SET menu_parent_id=999999 WHERE id=?",page);
        mvc.perform(post("/api/system/list-menu").with(csrf())).andExpect(status().isInternalServerError())
                .andExpect(jsonPath("$.resultCode").value("INVALID_TREE"));
    }

    @Test void navigationSortsSiblingsAndPreservesBusinessCodeAcrossRename() throws Exception {
        var later=menu("靠后模块","module",0);later.put("menuSort",5);
        long laterId=create(MENUS,later);
        var first=menu("靠前模块","module",0);first.put("menuSort",1);
        long firstId=create(MENUS,first);
        var page=menu("原始页面","page",firstId);
        page.put("menuCode","  stable-code  ");
        long pageId=create(MENUS,page);
        page.put("menuCode","stable-code");page.put("menuName","重命名页面");
        put(MENUS+"/"+pageId,page,200);
        mvc.perform(post("/api/system/list-menu").with(csrf()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.resultData[0].id").value(firstId))
                .andExpect(jsonPath("$.resultData[1].id").value(laterId))
                .andExpect(jsonPath("$.resultData[0].children[0].menuCode").value("stable-code"))
                .andExpect(jsonPath("$.resultData[0].children[0].menuName").value("重命名页面"));
    }

    @Test void navigationExcludesDisabledSubtreesButManagementKeepsThem() throws Exception {
        long module=create(MENUS,menu("启用模块","module",0));
        var groupData=menu("禁用分组","group",module);groupData.put("menuStatus",0);
        long group=create(MENUS,groupData);
        long enabledChild=create(MENUS,menu("禁用分组下的启用页面","page",group));
        var pageData=menu("禁用页面","page",module);pageData.put("menuStatus",0);
        long disabledPage=create(MENUS,pageData);
        long enabledPage=create(MENUS,menu("正常页面","page",module));
        var disabledModuleData=menu("禁用模块","module",0);disabledModuleData.put("menuStatus",0);
        long disabledModule=create(MENUS,disabledModuleData);
        long enabledModuleChild=create(MENUS,menu("禁用模块下的启用页面","page",disabledModule));
        var response=mvc.perform(post("/api/system/list-menu").with(csrf())).andExpect(status().isOk())
                .andExpect(jsonPath("$.resultData[0].children.length()").value(1)).andReturn();
        var navigation=json.readTree(response.getResponse().getContentAsString()).get("resultData");
        assertThat(ids(navigation)).containsExactlyInAnyOrder(module,enabledPage);
        assertThat(ids(tree(MENUS+"/tree"))).contains(group,enabledChild,disabledPage,disabledModule,enabledModuleChild);
        // 管理筛选会保留祖先，不能拿它代替导航过滤。
        assertThat(ids(tree(MENUS+"/tree?status=1"))).contains(group,disabledModule);
        mvc.perform(get(MENUS+"/"+disabledPage)).andExpect(status().isOk())
                .andExpect(jsonPath("$.resultData.menuStatus").value(0));
        groupData.put("menuStatus",1);put(MENUS+"/"+group,groupData,200);
        response=mvc.perform(post("/api/system/list-menu").with(csrf())).andExpect(status().isOk()).andReturn();
        assertThat(ids(json.readTree(response.getResponse().getContentAsString()).get("resultData")))
                .containsExactlyInAnyOrder(module,group,enabledChild,enabledPage);
        // 导航读取没有删除/改写任何记录。
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM hrs_system_menu",Integer.class)).isEqualTo(7);
    }

    @Test void hiddenAncestorsRemainInNavigationAndPagePathDoesNotDependOnCodesOrParent() throws Exception {
        var firstModule=menu("隐藏模块","module",0);firstModule.put("menuVisible",false);
        long module=create(MENUS,firstModule);
        var groupData=menu("路径分组","group",module);
        groupData.put("menuCode","stock");groupData.put("menuRoutePath","ignored-prefix");groupData.put("menuVisible",false);
        long group=create(MENUS,groupData);
        var pageData=menu("K线页面","page",group);
        pageData.put("menuCode","kline");pageData.put("menuRoutePath","/stock/kline");
        long page=create(MENUS,pageData);
        mvc.perform(post("/api/system/list-menu").with(csrf())).andExpect(status().isOk())
                .andExpect(jsonPath("$.resultData[0].menuVisible").value(false))
                .andExpect(jsonPath("$.resultData[0].children[0].menuVisible").value(false))
                .andExpect(jsonPath("$.resultData[0].children[0].children[0].menuVisible").value(true))
                .andExpect(jsonPath("$.resultData[0].children[0].children[0].menuRoutePath").value("/stock/kline"));
        long other=create(MENUS,menu("其他模块","module",0));
        groupData.put("menuParentId",other);groupData.put("menuCode","renamed-group");
        put(MENUS+"/"+group,groupData,200);
        pageData.put("menuCode","renamed-page");put(MENUS+"/"+page,pageData,200);
        mvc.perform(get(MENUS+"/"+page)).andExpect(status().isOk())
                .andExpect(jsonPath("$.resultData.menuCode").value("renamed-page"))
                .andExpect(jsonPath("$.resultData.menuRoutePath").value("/stock/kline"));
    }

    @Test void pagesRequireFullInternalPathsEvenThoughGroupPathsAreOptionalMetadata() throws Exception {
        long module=create(MENUS,menu("路径校验模块","module",0));
        var group=menu("路径校验分组","group",module);group.put("menuRoutePath","stock");
        long parent=create(MENUS,group);
        for (String path:List.of("kline","//outside.example/kline","https://outside.example/kline","")) {
            var data=menu("非法路径页面","page",parent);data.put("menuRoutePath",path);
            mvc.perform(post(MENUS).with(csrf()).contentType("application/json").content(json.writeValueAsString(data)))
                    .andExpect(status().isBadRequest()).andExpect(jsonPath("$.resultCode").value("INVALID_REQUEST"));
        }
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM hrs_system_menu",Integer.class)).isEqualTo(2);
    }

    @Test void disabledModuleProducesEmptyNavigationWithoutErasingManagementData() throws Exception {
        var data=menu("暂停模块","module",0);data.put("menuStatus",0);
        long module=create(MENUS,data);
        create(MENUS,menu("启用子页面","page",module));
        mvc.perform(post("/api/system/list-menu").with(csrf())).andExpect(status().isOk())
                .andExpect(jsonPath("$.resultData").isEmpty());
        assertThat(ids(tree(MENUS+"/tree"))).hasSize(2);
    }

    @Test void emptyNavigationIsAnEmptyArray() throws Exception {
        mvc.perform(post("/api/system/list-menu").with(csrf())).andExpect(status().isOk())
                .andExpect(jsonPath("$.resultData").isArray()).andExpect(jsonPath("$.resultData").isEmpty());
    }

    @Test void menuValidationAndServiceAuthorizationRemainEnforced() throws Exception {
        mvc.perform(get(MENUS+"/tree").with(anonymous())).andExpect(status().isUnauthorized());
        mvc.perform(get(MENUS+"/tree").with(user("ordinary").roles("USER"))).andExpect(status().isForbidden());
        mvc.perform(post(MENUS).contentType("application/json").content("{}")).andExpect(status().isForbidden());
        mvc.perform(get(MENUS+"/tree?status=2")).andExpect(status().isBadRequest());
        mvc.perform(get(MENUS+"/-1")).andExpect(status().isBadRequest());
        mvc.perform(delete(MENUS+"/999999").with(csrf())).andExpect(status().isNotFound());
        var badType=menu("type","unknown",0);
        var badVisible=menu("visible","module",0);badVisible.put("menuVisible","not-boolean");
        var longPath=menu("path","page",0);longPath.put("menuRoutePath","/"+"x".repeat(201));
        var audit=menu("audit","module",0);audit.put("createBy","forged");
        var deleted=menu("deleted","module",0);deleted.put("deleteFlag",1);
        for (var data:List.of(badType,badVisible,longPath,audit,deleted)) {
            mvc.perform(post(MENUS).with(csrf()).contentType("application/json").content(json.writeValueAsString(data)))
                    .andExpect(status().isBadRequest());
        }
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM hrs_system_menu",Integer.class)).isZero();
        org.springframework.security.core.context.SecurityContextHolder.clearContext();
        assertThatThrownBy(()->menus.get(1)).isInstanceOf(org.springframework.security.access.AccessDeniedException.class);
    }
}
