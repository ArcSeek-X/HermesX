package hermesx.system;

import com.fasterxml.jackson.databind.*;
import hermesx.system.service.IOrganizationService;
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

/** 使用正式SQL与临时SQLite覆盖真实HTTP、父链及事务。 */
@SpringBootTest(properties={"spring.cloud.nacos.discovery.enabled=false", "spring.sql.init.mode=always",
    "spring.sql.init.schema-locations=classpath:db/hrs-system-service.sql"})
@AutoConfigureMockMvc
@WithMockUser(username="tree-manager",roles="SYSTEM_ADMIN")
class TreeManagementApiIntegrationTest {
    static final String ORGANIZATIONS="/api/system/organization/";
    static final Path DATABASE;
    static { try { DATABASE=Files.createTempFile("hermesx-trees-", ".db"); } catch (java.io.IOException exception) { throw new ExceptionInInitializerError(exception); } }
    @DynamicPropertySource static void properties(DynamicPropertyRegistry registry) {
        registry.add("HRS_SYSTEM_DB_URL",()->"jdbc:sqlite:"+DATABASE);
        registry.add("HRS_SYSTEM_ADMIN_USERNAME",()->"tree-manager");
        registry.add("HRS_SYSTEM_ADMIN_PASSWORD",()->"test-only-tree-password");
    }
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;
    @Autowired JdbcTemplate jdbc;
    @Autowired IOrganizationService organizations;
    @BeforeEach void clearFixtures() { jdbc.update("DELETE FROM hrs_system_user"); jdbc.update("DELETE FROM hrs_system_organization"); }
    @AfterAll static void cleanupDatabase() throws Exception { Files.deleteIfExists(DATABASE); }
    Map<String,Object> organizationFields(String organizationName,long parentId) {
        return new LinkedHashMap<>(Map.of("name",organizationName,"parentId",parentId));
    }
    long createOrganization(Map<String,Object> organizationFields) throws Exception {
        var result=mvc.perform(post(ORGANIZATIONS+"add-organization").with(csrf()).contentType("application/json").content(json.writeValueAsString(organizationFields)))
            .andExpect(status().isCreated()).andExpect(jsonPath("$.resultCode").value("200"))
            .andExpect(jsonPath("$.resultData.id").doesNotExist()).andExpect(jsonPath("$.resultData.deleteFlag").doesNotExist())
            .andExpect(jsonPath("$.resultData.createBy").value("tree-manager")).andReturn();
        return json.readTree(result.getResponse().getContentAsString()).get("resultData").get("organizationId").asLong();
    }
    JsonNode queryOrganizations(int pageNum,int pageSize,List<Map<String,Object>> organizationFilters) throws Exception {
        var result=mvc.perform(post(ORGANIZATIONS+"list-organization").with(csrf()).contentType("application/json")
            .content(json.writeValueAsString(Map.of("pageNum",pageNum,"pageSize",pageSize,"filterList",organizationFilters))))
            .andExpect(status().isOk()).andExpect(jsonPath("$.resultCode").value("200")).andReturn();
        return json.readTree(result.getResponse().getContentAsString()).get("resultData");
    }
    void editOrganization(long organizationId,Map<String,Object> organizationFields,int expectedStatus) throws Exception {
        organizationFields.put("organizationId",organizationId);
        mvc.perform(post(ORGANIZATIONS+"edit-organization").with(csrf()).contentType("application/json")
            .content(json.writeValueAsString(organizationFields))).andExpect(status().is(expectedStatus));
    }
    void deleteOrganization(long organizationId,int expectedStatus) throws Exception {
        mvc.perform(post(ORGANIZATIONS+"delete-organization").with(csrf()).contentType("application/json")
            .content(json.writeValueAsString(Map.of("organizationId",organizationId)))).andExpect(status().is(expectedStatus));
    }
    @Test void organizationFieldsAndJsonPrimaryKeyRoundTrip() throws Exception {
        var fields=organizationFields("研发",0);
        fields.putAll(Map.of("shortName","研发简称","code","RND","email","rnd@example.com","phone","+86 010 001","leader","负责人","nature","A","type","1","remark","研发备注"));
        long organizationId=createOrganization(fields);
        mvc.perform(get(ORGANIZATIONS+"detail-organization/"+organizationId))
            .andExpect(status().isOk()).andExpect(jsonPath("$.resultData.organizationId").value(organizationId))
            .andExpect(jsonPath("$.resultData.shortName").value("研发简称")).andExpect(jsonPath("$.resultData.remark").value("研发备注"));
        assertThat(jdbc.queryForList("PRAGMA table_info(hrs_system_organization)").stream().map(column->column.get("name")))
            .contains("organization_id","organization_name","organization_type").doesNotContain("id","dept_name");
        editOrganization(organizationId,organizationFields("停用研发",0),200);
        deleteOrganization(organizationId,200);
        assertThat(jdbc.queryForObject("SELECT delete_flag FROM hrs_system_organization WHERE organization_id=?",Integer.class,organizationId)).isEqualTo(1);
        deleteOrganization(organizationId,404);
    }
    @Test void rootPaginationReturnsWholeSubtreesAndStableMetadata() throws Exception {
        long firstRoot=createOrganization(organizationFields("第一根",0));
        long child=createOrganization(organizationFields("子组织",firstRoot));
        createOrganization(organizationFields("第二根",0));
        JsonNode firstPage=queryOrganizations(1,1,List.of());
        assertThat(firstPage.get("total").asInt()).isEqualTo(2);
        assertThat(firstPage.get("pages").asInt()).isEqualTo(2);
        assertThat(firstPage.get("list").get(0).get("children").get(0).get("organizationId").asLong()).isEqualTo(child);
        assertThat(queryOrganizations(2,1,List.of()).get("list").get(0).get("name").asText()).isEqualTo("第二根");
        assertThat(queryOrganizations(Integer.MAX_VALUE,100,List.of()).get("list").size()).isZero();
    }
    @Test void filtersKeepAncestorsSupportMultiselectAndRejectMalformedConditions() throws Exception {
        long root=createOrganization(organizationFields("目录",0));
        var child=organizationFields("命中研发",root);child.put("type","2");child.put("status",0);createOrganization(child);
        createOrganization(organizationFields("其他",0));
        var filters=List.of(Map.<String,Object>of("fieldName","name","comparison","LIKE","fieldValue","研发"),
            Map.<String,Object>of("fieldName","type","comparison","IN","fieldValue",List.of("1","2")),
            Map.<String,Object>of("fieldName","status","comparison","EQUAL","fieldValue",0));
        JsonNode filtered=queryOrganizations(1,10,filters);
        assertThat(filtered.get("total").asInt()).isEqualTo(1);
        assertThat(filtered.get("list").get(0).get("organizationId").asLong()).isEqualTo(root);
        assertThat(filtered.get("list").get(0).get("children").size()).isEqualTo(1);
        for (Object malformed:List.of(
            Map.of("fieldName","type","comparison","IN","fieldValue","1,2"),
            Map.of("fieldName","type","comparison","IN","fieldValue",List.of()),
            Map.of("fieldName","status","comparison","EQUAL","fieldValue","0"),
            Map.of("fieldName","organization_type","comparison","EQUAL","fieldValue","2"))) {
            mvc.perform(post(ORGANIZATIONS+"list-organization").with(csrf()).contentType("application/json")
                .content(json.writeValueAsString(Map.of("filterList",List.of(malformed)))))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.resultCode").value("INVALID_REQUEST"));
        }
        JsonNode empty=queryOrganizations(1,10,List.of(Map.of("fieldName","name","comparison","LIKE","fieldValue","%研发%")));
        assertThat(empty.get("list").size()).isZero();assertThat(empty.get("pages").asInt()).isZero();
    }
    @Test void movingUpdatesDescendantsAndRejectsCyclesOrCrossEnterprise() throws Exception {
        long root=createOrganization(organizationFields("A",0));
        long child=createOrganization(organizationFields("B",root));
        long leaf=createOrganization(organizationFields("C",child));
        long destination=createOrganization(organizationFields("D",0));
        editOrganization(child,organizationFields("B moved",destination),200);
        assertThat(jdbc.queryForObject("SELECT ancestors FROM hrs_system_organization WHERE organization_id=?",String.class,leaf)).isEqualTo(destination+","+child);
        editOrganization(destination,organizationFields("cycle",leaf),409);
        assertThat(jdbc.queryForObject("SELECT parent_id FROM hrs_system_organization WHERE organization_id=?",Long.class,destination)).isZero();
        var differentEnterprise=organizationFields("wrong enterprise",destination);differentEnterprise.put("enterpriseId",100);
        editOrganization(child,differentEnterprise,409);
        deleteOrganization(destination,409);deleteOrganization(root,200);
    }
    @Test void assignedUsersProtectDeletionAndCompareEnterpriseNotNodePrimaryKey() throws Exception {
        var department=organizationFields("部门",0);department.put("enterpriseId",100);
        long departmentId=createOrganization(department);
        var user=new LinkedHashMap<String,Object>(Map.of("username","department-user","password","test-user-password","nickname","成员", "deptId",departmentId,"enterpriseId",100,"organizationId",2001));
        var created=mvc.perform(post("/api/system/users").with(csrf()).contentType("application/json").content(json.writeValueAsString(user)))
            .andExpect(status().isCreated()).andReturn();
        long userId=json.readTree(created.getResponse().getContentAsString()).get("resultData").get("id").asLong();
        deleteOrganization(departmentId,409);
        user.put("username","wrong-enterprise");user.put("enterpriseId",101);
        mvc.perform(post("/api/system/users").with(csrf()).contentType("application/json").content(json.writeValueAsString(user))).andExpect(status().isConflict());
        mvc.perform(delete("/api/system/users/"+userId).with(csrf())).andExpect(status().isOk());
        deleteOrganization(departmentId,200);
    }
    @Test void securityValidationAndRemovedRoutesRemainExplicit() throws Exception {
        mvc.perform(get(ORGANIZATIONS+"get-organization-tree").with(anonymous())).andExpect(status().isUnauthorized());
        mvc.perform(get(ORGANIZATIONS+"get-organization-tree").with(user("ordinary").roles("USER"))).andExpect(status().isForbidden());
        mvc.perform(post(ORGANIZATIONS+"list-organization").contentType("application/json").content("{}"))
            .andExpect(status().isForbidden()).andExpect(jsonPath("$.resultCode").value("CSRF_INVALID"));
        for (String body:List.of("{}","{\"name\":\" \"}","{\"name\":\"x\",\"organizationId\":1}","{\"name\":\"x\",\"email\":\"invalid\"}")) {
            mvc.perform(post(ORGANIZATIONS+"add-organization").with(csrf()).contentType("application/json").content(body)).andExpect(status().isBadRequest());
        }
        mvc.perform(post(ORGANIZATIONS+"delete-organization").with(csrf()).contentType("application/json").content("{}"))
            .andExpect(status().isBadRequest()).andExpect(jsonPath("$.resultData").isEmpty());
        mvc.perform(get("/api/system/organizations/tree")).andExpect(status().isNotFound());
        org.springframework.security.core.context.SecurityContextHolder.clearContext();
        assertThatThrownBy(()->organizations.get(1)).isInstanceOf(org.springframework.security.access.AccessDeniedException.class);
    }
    @Test void overlongDescendantPathRollsBackWholeMove() throws Exception {
        jdbc.update("INSERT INTO hrs_system_organization(organization_id,parent_id,ancestors,organization_name,create_by,update_by) VALUES (101,0,'','source','fixture','fixture')");
        jdbc.update("INSERT INTO hrs_system_organization(organization_id,parent_id,ancestors,organization_name,create_by,update_by) VALUES (102,101,'101','child','fixture','fixture')");
        jdbc.update("INSERT INTO hrs_system_organization(organization_id,parent_id,ancestors,organization_name,create_by,update_by) VALUES (103,102,'101,102','leaf','fixture','fixture')");
        long parentId=0;String ancestors="";
        for (int depth=0;depth<26;depth++) {
            long organizationId=900000000000000000L+depth;
            jdbc.update("INSERT INTO hrs_system_organization(organization_id,parent_id,ancestors,organization_name,create_by,update_by) VALUES (?,?,?,?,?,?)",organizationId,parentId,ancestors,"deep-"+depth,"fixture","fixture");
            ancestors=ancestors.isEmpty()?Long.toString(organizationId):ancestors+","+organizationId;parentId=organizationId;
        }
        editOrganization(101,organizationFields("must rollback",parentId),409);
        assertThat(jdbc.queryForObject("SELECT organization_name FROM hrs_system_organization WHERE organization_id=101",String.class)).isEqualTo("source");
        assertThat(jdbc.queryForObject("SELECT ancestors FROM hrs_system_organization WHERE organization_id=103",String.class)).isEqualTo("101,102");
    }

    @Test void organizationFieldLimitsAndInternalFieldsCannotBeWritten() throws Exception {
        for (var invalidField:List.of(Map.<String,Object>of("name","x".repeat(101)), Map.<String,Object>of("shortName","x".repeat(65)),
            Map.<String,Object>of("remark","x".repeat(501)),Map.<String,Object>of("parentId",-1),
            Map.<String,Object>of("enterpriseId",0),Map.<String,Object>of("createBy","forged"),Map.<String,Object>of("ancestors","1,2"))) {
            var organizationFields=organizationFields("无效组织",0);organizationFields.putAll(invalidField);
            mvc.perform(post(ORGANIZATIONS+"add-organization").with(csrf()).contentType("application/json")
                .content(json.writeValueAsString(organizationFields))).andExpect(status().isBadRequest());
        }
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM hrs_system_organization",Integer.class)).isZero();
    }

    @Test void invalidPaginationDuplicateFiltersAndOldSearchParametersAreRejected() throws Exception {
        String statusFilter="{\"fieldName\":\"status\",\"comparison\":\"EQUAL\",\"fieldValue\":1}";
        for (String invalidQuery:List.of("{\"pageNum\":0}","{\"pageSize\":101}","{\"pageSize\":0}",
            "{\"keyword\":\"研发\"}","{\"mainSearch\":\"研发\"}","{\"filterList\":[null]}",
            "{\"filterList\":["+statusFilter+","+statusFilter+"]}")) {
            mvc.perform(post(ORGANIZATIONS+"list-organization").with(csrf()).contentType("application/json").content(invalidQuery))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.resultCode").value("INVALID_REQUEST"));
        }
    }
}
