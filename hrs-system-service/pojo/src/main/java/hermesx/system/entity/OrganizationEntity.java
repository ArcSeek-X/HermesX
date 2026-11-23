package hermesx.system.entity;

/** 数据库部门行，id 是本节点主键；organizationId 是归属元数据，不是本节点主键。 */
public record OrganizationEntity(Long id, long parentId, String ancestors, String deptName,
        String leader, String phone, String email, int sort, int status,
        Long enterpriseId, Long organizationId, int deleteFlag, String createBy, String updateBy, String createTime, String updateTime) {}
