package hermesx.system.entity;

/** 数据库菜单行：只在持久化和业务层流转，包含内部删除及审计字段。 */
public record MenuEntity(Long id, long menuParentId, String menuCode, String menuName,
        String menuDescription, String menuType, String menuRoutePath, String menuPagePath,
        String menuIcon, String menuBadge, String menuPosition, boolean menuExpanded,
        boolean menuVisible, int menuSort, int menuStatus, String menuPermission,
        String auth, Boolean exact, Long enterpriseId, Long organizationId, int deleteFlag,
        String createBy, String updateBy, String createTime, String updateTime) {}
