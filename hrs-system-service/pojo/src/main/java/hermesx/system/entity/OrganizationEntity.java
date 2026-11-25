package hermesx.system.entity;

/** 组织表完整一行，organizationId对应唯一主键organization_id。 */
public record OrganizationEntity(Long organizationId, long parentId, String ancestors, String name,
        String shortName, String code, String email, String phone, String leader, String nature,
        String type, String remark, int sort, int status, Long enterpriseId, int deleteFlag,
        String createBy, String updateBy, String createTime, String updateTime) {}
