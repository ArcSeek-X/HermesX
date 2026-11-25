package hermesx.system.dto;

import jakarta.validation.constraints.*;

/** 删除只接收组织节点主键。 */
public record OrganizationDeleteDTO(@NotNull @Positive Long organizationId) {}
