package hermesx.system.entity;

/** 数据库行模型：字段与 hrs_system_user 对应，不能直接作为 HTTP 响应。 */
public record UserEntity(Long id, String username, String password, String nickname,
        String phone, String email, Long deptId, Long enterpriseId, Long organizationId, int status, String lastLoginTime,
        int deleteFlag, String createBy, String updateBy, String createTime, String updateTime) {
    @Override public String toString() { return "UserEntity[id=" + id + ", password=<redacted>]"; }
}
