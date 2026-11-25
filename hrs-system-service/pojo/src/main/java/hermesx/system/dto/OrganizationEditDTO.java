package hermesx.system.dto;

import jakarta.validation.constraints.*;

/** 编辑提交完整字段；organizationId只定位记录，不可修改主键。 */
public record OrganizationEditDTO(@NotNull @Positive Long organizationId,
        @PositiveOrZero Long parentId,
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
        @Positive Long enterpriseId) {
    public OrganizationWriteDTO organizationFields() {
        return new OrganizationWriteDTO(parentId,name,shortName,code,email,phone,leader,nature,type,remark,sort,status,enterpriseId);
    }
}
