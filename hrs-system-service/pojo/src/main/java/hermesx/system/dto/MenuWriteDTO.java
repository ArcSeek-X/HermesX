package hermesx.system.dto;

import jakarta.validation.constraints.*;

/**
 * 菜单新增/修改输入。JSON 使用 camelCase，数据库列由 Mapper 映射为 menu_ 前缀。
 * Boolean/Integer 使用包装类型区分“没传”和显式 false/0，默认值在 Service 统一补齐。
 * id 由数据库分配，审计和 deleteFlag 不接受前端指定。
 */
public record MenuWriteDTO(
        @PositiveOrZero Long menuParentId,
        @NotBlank @Size(max=128) String menuCode,
        @NotBlank @Size(max=100) String menuName,
        @Size(max=500) String menuDescription,
        @NotBlank @Pattern(regexp="module|group|page") String menuType,
        // 只有page必须填写完整站内路径；在Service结合menuType校验，group可保留分组标识。
        @Size(max=200) String menuRoutePath,
        @Size(max=200) @Pattern(regexp="^pages/.+") String menuPagePath,
        @Size(max=64) String menuIcon,
        @Size(max=64) String menuBadge,
        @Pattern(regexp="header|content|footer") String menuPosition,
        Boolean menuExpanded,
        Boolean menuVisible,
        @PositiveOrZero Integer menuSort,
        @Min(0) @Max(1) Integer menuStatus,
        @Size(max=128) String menuPermission,
        @Pattern(regexp="public|protected") String auth,
        Boolean exact,
        @Positive Long enterpriseId,
        @Positive Long organizationId) {}
