package hermesx.system.dto;

import jakarta.validation.constraints.*;

/** 完整更新可编辑资料；账号不可改，密码不通过这个接口更新。可选字段传 null 表示清空。 */
public record UpdateUserDTO(
        @NotBlank @Size(max = 64) String nickname,
        @Size(max = 32) String phone,
        @Email @Size(max = 128) String email,
        @Positive Long deptId,
        // 所属企业、组织仅作归属信息；当前只有管理身份可写，不作为认证凭据。
        @Positive Long enterpriseId,
        @Positive Long organizationId,
        @NotNull @Min(0) @Max(1) Integer status) {}
