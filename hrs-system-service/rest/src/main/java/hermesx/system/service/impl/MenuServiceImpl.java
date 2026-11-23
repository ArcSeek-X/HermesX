package hermesx.system.service.impl;

import hermesx.system.dao.MenuMapper;
import hermesx.system.dto.MenuWriteDTO;
import hermesx.system.entity.MenuEntity;
import hermesx.system.vo.MenuVO;
import hermesx.system.service.IMenuService;
import hermesx.system.security.CurrentUser;
import hermesx.system.utils.TreeUtils;
import hermesx.system.exception.ManagementException;
import hermesx.system.enums.SystemResultCodeEnum;
import hermesx.common.rest.ResultCodeEnum;
import java.util.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.validation.annotation.Validated;

/**
 * 菜单业务层：处理默认值、树约束和实体转视图，不依赖前端静态清单。
 * menuPermission 目前仅保存权限标识；本阶段仍要求 SYSTEM_ADMIN，不宣称已经实现角色授权。
 */
@Service
@Validated
public class MenuServiceImpl implements IMenuService {
    private final MenuMapper mapper;
    private final CurrentUser currentUser;
    public MenuServiceImpl(MenuMapper mapper, CurrentUser currentUser) {
        this.mapper=mapper; this.currentUser=currentUser;
    }

    /**
     * 导航只返回生效节点：父节点禁用时整棵子树排除，不能把启用孩子提升到别处。
     * 不能复用 tree(..., status=1, ...) 的管理筛选：管理树会补齐命中节点的祖先，
     * 因而仍可能带回禁用父节点。这里先取得校验后的完整树，再按子树过滤。
     * menuVisible 只传给前端控制显示，不在这里过滤；用户级授权暂未实现。
     */
    @Override @Transactional(readOnly=true)
    public List<MenuVO> listMenu() { return retainEnabledSubtrees(tree(null,null,null,null)); }

    /** 只修改本次查询新建的VO树，不修改数据库，也不把父级状态写入子级。 */
    private List<MenuVO> retainEnabledSubtrees(List<MenuVO> nodes) {
        nodes.removeIf(node -> node.menuStatus()!=1);
        for (MenuVO node:nodes) retainEnabledSubtrees(node.children());
        return nodes;
    }

    @Override @Transactional
    public MenuVO create(MenuWriteDTO input) {
        String operator=currentUser.requireAdmin();
        MenuWriteDTO data=normalize(input);
        validateHierarchy(0,data);
        validateUnique(0,data);
        return view(find(mapper.insert(data,operator)));
    }
    @Override public MenuVO get(long id) { currentUser.requireAdmin(); return view(find(id)); }

    /** 管理查询可按关键字等筛选，并保留祖先；导航接口使用无筛选的完整树。 */
    @Override @Transactional(readOnly=true)
    public List<MenuVO> tree(String keyword,Integer status,Long enterpriseId,Long organizationId) {
        currentUser.requireAdmin();
        String search=keyword==null?"":keyword.trim();
        List<MenuEntity> rows=mapper.all(enterpriseId,organizationId);
        // 防止坏数据组装成“成功但前端无法使用”的树；异常统一转为稳定业务码。
        Map<Long,MenuEntity> indexed=new HashMap<>();
        Set<String> codes=new HashSet<>(), routes=new HashSet<>();
        for (MenuEntity row:rows) indexed.put(row.id(),row);
        for (MenuEntity row:rows) {
            MenuEntity parent=indexed.get(row.menuParentId());
            if (!validType(row.menuType()) || row.menuCode()==null || row.menuCode().isBlank()
                    || !codes.add(row.menuCode())
                    || (row.menuParentId()==0 ? !row.menuType().equals("module")
                        : parent==null || !validChildren(parent.menuType(),row.menuType())
                          || !Objects.equals(parent.enterpriseId(),row.enterpriseId())
                          || !Objects.equals(parent.organizationId(),row.organizationId()))
                    || (row.menuType().equals("page") && (!validPage(row.menuRoutePath(),row.menuPagePath())
                        || !routes.add(row.menuRoutePath())))) {
                throw ManagementException.internal(SystemResultCodeEnum.INVALID_TREE);
            }
        }
        try {
            return TreeUtils.build(rows.stream().map(this::view).toList(),
                    node->node.menuName().contains(search) && (status==null || node.menuStatus()==status));
        } catch (IllegalStateException e) {
            throw ManagementException.internal(SystemResultCodeEnum.INVALID_TREE);
        }
    }

    @Override @Transactional
    public MenuVO update(long id, MenuWriteDTO input) {
        String operator=currentUser.requireAdmin();
        MenuEntity old=find(id); MenuWriteDTO data=normalize(input);
        sameScope(old.enterpriseId(),old.organizationId(),data.enterpriseId(),data.organizationId());
        validateHierarchy(id,data);
        validateUnique(id,data);
        // 不允许把有孩子的分组改成 page；页面必须是叶子节点。
        for (MenuEntity child:mapper.all(null,null)) {
            if (child.menuParentId()==id) checkTypes(data.menuType(),child.menuType());
        }
        mapper.update(id,data,operator);
        return view(find(id));
    }
    @Override @Transactional
    public void delete(long id) {
        String operator=currentUser.requireAdmin(); find(id);
        if (mapper.countChildren(id)>0) throw conflict(SystemResultCodeEnum.HAS_CHILDREN,"存在子菜单，不能删除");
        mapper.softDelete(id,operator);
    }

    private void validateUnique(long id,MenuWriteDTO data) {
        // menuCode 与 page 路由都必须在返回的完整树中唯一；不能只在同级检查。
        for (MenuEntity row:mapper.all(null,null)) {
            if (row.id()==id) continue;
            if (row.menuCode().equals(data.menuCode()))
                throw conflict(SystemResultCodeEnum.MENU_CODE_EXISTS,"菜单业务标识已存在。");
            if (data.menuType().equals("page") && row.menuType().equals("page")
                    && Objects.equals(row.menuRoutePath(),data.menuRoutePath()))
                throw conflict(SystemResultCodeEnum.MENU_ROUTE_EXISTS,"页面路由已存在。");
        }
    }
    private void validateHierarchy(long id,MenuWriteDTO data) {
        long parentId=data.menuParentId();
        if ((parentId==0)!=data.menuType().equals("module"))
            throw conflict(SystemResultCodeEnum.INVALID_MENU_TYPE,"根节点必须为module；group/page必须属于模块或分组。");
        Set<Long> visited=new HashSet<>(); if (id!=0) visited.add(id);
        boolean direct=true;
        while (parentId!=0) {
            if (!visited.add(parentId)) throw conflict(SystemResultCodeEnum.INVALID_PARENT,"不能把自己或子孙设为父菜单");
            MenuEntity parent=mapper.find(parentId).orElseThrow(()->conflict(SystemResultCodeEnum.INVALID_PARENT,"父菜单不存在或已删除"));
            sameScope(parent.enterpriseId(),parent.organizationId(),data.enterpriseId(),data.organizationId());
            if (direct) { checkTypes(parent.menuType(),data.menuType()); direct=false; }
            parentId=parent.menuParentId();
            if (visited.size()+(id==0?1:0)>64) throw conflict(SystemResultCodeEnum.TREE_TOO_DEEP,"菜单层级最多64层");
        }
        // 移动已有子树时也计算子孙深度，避免局部合法、整棵树超限。
        if (id!=0) {
            Map<Long,Long> parents=new HashMap<>();
            for (MenuEntity row:mapper.all(null,null)) parents.put(row.id(),row.id()==id?data.menuParentId():row.menuParentId());
            for (long rowId:parents.keySet()) {
                Set<Long> chain=new HashSet<>(); long current=rowId;
                while (current!=0) {
                    if (!chain.add(current)) throw conflict(SystemResultCodeEnum.INVALID_PARENT,"菜单树存在循环");
                    if (chain.size()>64) throw conflict(SystemResultCodeEnum.TREE_TOO_DEEP,"菜单层级最多64层");
                    Long next=parents.get(current);
                    if (next==null) throw conflict(SystemResultCodeEnum.INVALID_PARENT,"菜单树存在缺失父节点");
                    current=next;
                }
            }
        }
    }
    private boolean validType(String type) { return "module".equals(type) || "group".equals(type) || "page".equals(type); }
    private boolean validChildren(String parent,String child) {
        return ("module".equals(parent) || "group".equals(parent)) && ("group".equals(child) || "page".equals(child));
    }
    private void checkTypes(String parent,String child) {
        if (!validChildren(parent,child))
            throw conflict(SystemResultCodeEnum.INVALID_MENU_TYPE,"模块或分组下可建group/page；page不能有子节点。");
    }
    private void sameScope(Long a,Long b,Long c,Long d) {
        if (!Objects.equals(a,c)||!Objects.equals(b,d))
            throw conflict(SystemResultCodeEnum.SCOPE_MISMATCH,"父子菜单必须同企业同组织；现有菜单不支持修改归属");
    }
    /** page直接保存完整站内路径，不按menuCode、父节点或模块名称拼接。 */
    private boolean validPage(String route,String page) {
        return route!=null && route.startsWith("/") && !route.startsWith("//")
                && page!=null && page.startsWith("pages/") && page.length()>6;
    }
    private MenuWriteDTO normalize(MenuWriteDTO d) {
        if (d.menuType().equals("page") && !validPage(d.menuRoutePath(),d.menuPagePath()))
            throw ManagementException.invalid(ResultCodeEnum.INVALID_REQUEST,"page必须提供站内路由及pages/开头的页面路径。");
        return new MenuWriteDTO(d.menuParentId()==null?0:d.menuParentId(),d.menuCode().trim(),d.menuName().trim(),
                d.menuDescription()==null?"":d.menuDescription(),d.menuType(),d.menuRoutePath(),d.menuPagePath(),
                d.menuIcon(),d.menuBadge(),d.menuPosition()==null?"content":d.menuPosition(),
                d.menuExpanded()==null?false:d.menuExpanded(),d.menuVisible()==null?true:d.menuVisible(),
                d.menuSort()==null?0:d.menuSort(),d.menuStatus()==null?1:d.menuStatus(),d.menuPermission(),
                d.auth(),d.exact(),d.enterpriseId(),d.organizationId());
    }
    private MenuEntity find(long id) {
        return mapper.find(id).orElseThrow(()->ManagementException.missing(SystemResultCodeEnum.MENU_NOT_FOUND,"菜单不存在或已删除"));
    }
    private ManagementException conflict(SystemResultCodeEnum code,String message) { return ManagementException.conflict(code,message); }
    private MenuVO view(MenuEntity e) {
        return new MenuVO(e.id(),e.menuParentId(),e.menuCode(),e.menuName(),e.menuDescription(),e.menuType(),
                e.menuRoutePath(),e.menuPagePath(),e.menuIcon(),e.menuBadge(),e.menuPosition(),e.menuExpanded(),
                e.menuVisible(),e.menuSort(),e.menuStatus(),e.menuPermission(),e.auth(),e.exact(),
                e.enterpriseId(),e.organizationId(),e.createBy(),e.updateBy(),e.createTime(),e.updateTime(),new ArrayList<>());
    }
}
