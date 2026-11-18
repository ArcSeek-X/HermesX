package hermesx.system.vo;

/** 返回给调用方的用户视图：刻意没有 password 字段，也不暴露删除标记。 */
public record UserVO(Long id, String username, String nickname, String phone, String email,
        Long deptId, Long enterpriseId, Long organizationId, int status, String lastLoginTime, String createBy, String updateBy,
        String createTime, String updateTime) {}
