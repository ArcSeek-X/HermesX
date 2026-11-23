package hermesx.system.vo;

import com.fasterxml.jackson.annotation.JsonInclude;
import hermesx.system.base.TreeNode;
import java.util.List;

/**
 * 对外菜单节点与前端 manifest 同构：模块、分组和页面共用一个类型。
 * 可选字段无值时省略，不能输出 null，否则不满足前端的节点契约。
 * menuStatus是管理字段；导航仅保留启用子树，所以导航响应中的该值均为1。
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record MenuVO(Long id, long menuParentId, String menuCode, String menuName,
        String menuDescription, String menuType, String menuRoutePath, String menuPagePath,
        String menuIcon, String menuBadge, String menuPosition, boolean menuExpanded,
        boolean menuVisible, int menuSort, int menuStatus, String menuPermission,
        String auth, Boolean exact, Long enterpriseId, Long organizationId,
        String createBy, String updateBy, String createTime, String updateTime,
        List<MenuVO> children) implements TreeNode<MenuVO> {
    /** 仅适配共享组树工具；JSON record 属性仍为 menuParentId，不增加旧 parentId 字段。 */
    @Override public long parentId() { return menuParentId; }
}
