package hermesx.system.dto;

import jakarta.validation.constraints.*;

/** 部门写入参数；parentId=0 表示根节点，ancestors、删除标志与审计字段由服务端维护。 */
public record OrganizationWriteDTO(
        @PositiveOrZero Long parentId,
        @NotBlank @Size(max=100) String name,
        @Size(max=64) String leader,
        @Size(max=32) String phone,
        @Email @Size(max=128) String email,
        @PositiveOrZero Integer sort,
        @Min(0) @Max(1) Integer status,
        @Positive Long enterpriseId,
        @Positive Long organizationId) {}
