package hermesx.system.service.impl;

import hermesx.system.dao.OrganizationMapper;
import hermesx.system.dto.OrganizationWriteDTO;
import hermesx.system.entity.OrganizationEntity;
import hermesx.system.vo.OrganizationVO;
import hermesx.system.service.IOrganizationService;
import hermesx.system.security.CurrentUser;
import hermesx.system.utils.TreeUtils;
import hermesx.system.exception.ManagementException;
import hermesx.system.enums.SystemResultCodeEnum;
import hermesx.common.rest.ResultCodeEnum;
import java.util.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.validation.annotation.Validated;

/** 部门用例：parentId是结构，ancestors是结构的派生路径，不能由前端任意写入。 */
@Service
@Validated
public class OrganizationServiceImpl implements IOrganizationService {
    private final OrganizationMapper mapper;
    private final CurrentUser currentUser;
    public OrganizationServiceImpl(OrganizationMapper mapper, CurrentUser currentUser) {
        this.mapper=mapper; this.currentUser=currentUser;
    }
    @Override @Transactional
    public OrganizationVO create(OrganizationWriteDTO input) {
        String operator=currentUser.requireAdmin();
        OrganizationWriteDTO data=normalize(input);
        String ancestors=ancestorsFor(0, data.parentId(), data.enterpriseId(), data.organizationId());
        return view(find(mapper.insert(data,ancestors,operator)));
    }
    @Override public OrganizationVO get(long id) { currentUser.requireAdmin(); return view(find(id)); }
    @Override @Transactional(readOnly=true)
    public List<OrganizationVO> tree(String keyword, Integer status, Long enterpriseId, Long organizationId) {
        currentUser.requireAdmin();
        String search=keyword==null ? "" : keyword.trim();
        return TreeUtils.build(mapper.all(enterpriseId,organizationId).stream().map(this::view).toList(),
                node -> node.name().contains(search) && (status==null || node.status()==status));
    }
    @Override @Transactional
    public OrganizationVO update(long id, OrganizationWriteDTO input) {
        String operator=currentUser.requireAdmin();
        OrganizationEntity old=find(id);
        OrganizationWriteDTO data=normalize(input);
        sameScope(old.enterpriseId(),old.organizationId(),data.enterpriseId(),data.organizationId());
        String ancestors=ancestorsFor(id,data.parentId(),data.enterpriseId(),data.organizationId());
        mapper.update(id,data,ancestors,operator);
        if (old.parentId()!=data.parentId()) {
            // 原子更新整个子树路径；任何节点超过长度限制时，根节点更新也一起回滚。
            List<OrganizationEntity> rows=mapper.all(null,null);
            Map<Long,List<OrganizationEntity>> children=new HashMap<>();
            for (OrganizationEntity row:rows) children.computeIfAbsent(row.parentId(),k->new ArrayList<>()).add(row);
            Deque<Long> queue=new ArrayDeque<>(); queue.add(id);
            Set<Long> visited=new HashSet<>();
            while (!queue.isEmpty()) {
                long parent=queue.remove();
                if (!visited.add(parent)) throw ManagementException.internal(SystemResultCodeEnum.INVALID_TREE);
                for (OrganizationEntity child:children.getOrDefault(parent,List.of())) {
                    String path=ancestorsFor(child.id(),child.parentId(),child.enterpriseId(),child.organizationId());
                    mapper.updateAncestors(child.id(),path,operator); queue.add(child.id());
                }
            }
        }
        return view(find(id));
    }
    @Override @Transactional
    public void delete(long id) {
        String operator=currentUser.requireAdmin(); find(id);
        if (mapper.countChildren(id)>0) throw conflict(SystemResultCodeEnum.HAS_CHILDREN,"存在下级部门，不能删除");
        if (mapper.countUsers(id)>0) throw conflict(SystemResultCodeEnum.DEPARTMENT_IN_USE,"部门仍关联用户，不能删除");
        mapper.softDelete(id,operator);
    }
    @Override public void validateUserDepartment(Long deptId, Long enterpriseId, Long organizationId) {
        currentUser.requireAdmin();
        if (deptId==null) return;
        OrganizationEntity department=find(deptId);
        sameScope(department.enterpriseId(),department.organizationId(),enterpriseId,organizationId);
    }
    private String ancestorsFor(long id,long parentId,Long enterpriseId,Long organizationId) {
        List<String> path=new ArrayList<>(); Set<Long> visited=new HashSet<>();
        if (id!=0) visited.add(id);
        while (parentId!=0) {
            if (!visited.add(parentId)) throw conflict(SystemResultCodeEnum.INVALID_PARENT,"不能把自己或子孙设为上级部门");
            OrganizationEntity parent=mapper.find(parentId).orElseThrow(()->conflict(SystemResultCodeEnum.INVALID_PARENT,"上级部门不存在或已删除"));
            sameScope(parent.enterpriseId(),parent.organizationId(),enterpriseId,organizationId);
            path.add(Long.toString(parentId)); parentId=parent.parentId();
            if (path.size()>=64) throw conflict(SystemResultCodeEnum.TREE_TOO_DEEP,"部门层级最多64层");
        }
        Collections.reverse(path);
        String ancestors=String.join(",",path);
        if (ancestors.length()>500) throw conflict(SystemResultCodeEnum.ANCESTORS_TOO_LONG,"部门祖级路径超过500字符");
        return ancestors;
    }
    private void sameScope(Long a,Long b,Long c,Long d) {
        if (!Objects.equals(a,c) || !Objects.equals(b,d))
            throw conflict(SystemResultCodeEnum.SCOPE_MISMATCH,"节点与父节点、关联用户必须同企业同组织；现有节点不支持修改归属");
    }
    private OrganizationWriteDTO normalize(OrganizationWriteDTO d) {
        return new OrganizationWriteDTO(d.parentId()==null?0:d.parentId(),d.name().trim(),d.leader(),d.phone(),d.email(),
                d.sort()==null?0:d.sort(),d.status()==null?1:d.status(),d.enterpriseId(),d.organizationId());
    }
    private OrganizationEntity find(long id) {
        return mapper.find(id).orElseThrow(()->ManagementException.missing(SystemResultCodeEnum.ORGANIZATION_NOT_FOUND,"部门不存在或已删除"));
    }
    private ManagementException conflict(SystemResultCodeEnum code,String message) { return ManagementException.conflict(code,message); }
    private OrganizationVO view(OrganizationEntity e) {
        return new OrganizationVO(e.id(),e.parentId(),e.ancestors(),e.deptName(),e.leader(),e.phone(),e.email(),e.sort(),e.status(),
                e.enterpriseId(),e.organizationId(),e.createBy(),e.updateBy(),e.createTime(),e.updateTime(),new ArrayList<>());
    }
}
