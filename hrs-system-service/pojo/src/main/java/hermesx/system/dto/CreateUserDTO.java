package hermesx.system.dto;

import jakarta.validation.constraints.*;

/** 新增输入：只允许调用者填写业务字段，ID、审计人和时间由服务端产生。 */
public record CreateUserDTO(
        @NotBlank @Size(max = 64) String username,
        @NotBlank @Size(min = 8, max = 64) String password,
        @NotBlank @Size(max = 64) String nickname,
        @Size(max = 32) String phone,
        @Email @Size(max = 128) String email,
        @Positive Long deptId,
        // 所属企业、组织仅作归属信息；当前只有管理身份可写，不作为认证凭据。
        @Positive Long enterpriseId,
        @Positive Long organizationId,
        @Min(0) @Max(1) Integer status) {
    // record 自动生成只读字段和访问方法；避免输出包含密码的默认 toString。
    @Override public String toString() { return "CreateUserDTO[password=<redacted>]"; }
}
