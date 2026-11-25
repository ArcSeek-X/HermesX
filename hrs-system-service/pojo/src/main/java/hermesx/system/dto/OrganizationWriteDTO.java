package hermesx.system.dto;

import jakarta.validation.constraints.*;

/** 新增组织的可写字段；主键、祖先路径和审计由服务端生成。 */
public record OrganizationWriteDTO(@PositiveOrZero Long parentId,
        @NotBlank @Size(max=100) String name,
        @Size(max=64) String shortName,
        @Size(max=64) String code,
        @Email @Size(max=128) String email,
        @Size(max=32) String phone,
        @Size(max=64) String leader,
        @Size(max=32) String nature,
        @Size(max=32) String type,
        @Size(max=500) String remark,
        @PositiveOrZero Integer sort,
        @Min(0) @Max(1) Integer status,
        @Positive Long enterpriseId) {}
