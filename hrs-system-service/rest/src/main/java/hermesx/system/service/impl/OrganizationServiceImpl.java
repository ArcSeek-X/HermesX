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
import java.util.function.Predicate;
import hermesx.common.dto.*;
import hermesx.common.vo.ListPageVO;
import hermesx.common.enums.FilterOperatorEnum;
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
        String ancestors=ancestorsFor(0, data.parentId(), data.enterpriseId());
        return view(find(mapper.insert(data,ancestors,operator)));
    }
    @Override public OrganizationVO get(long id) { currentUser.requireAdmin(); return view(find(id)); }
    @Override @Transactional(readOnly=true)
    public List<OrganizationVO> tree(Long enterpriseId) {
        currentUser.requireAdmin();
        return TreeUtils.build(mapper.all(enterpriseId).stream().map(this::view).toList(), organization -> true);
    }
    @Override @Transactional(readOnly=true)
    public ListPageVO<OrganizationVO> queryOrganizations(PageQueryDTO organizationQuery) {
        currentUser.requireAdmin();
        if (organizationQuery.pageNum()<1 || organizationQuery.pageSize()<1 || organizationQuery.pageSize()>100)
            throw invalidQuery();
        Predicate<OrganizationVO> organizationMatches=organizationPredicate(organizationQuery.filterList());
        List<OrganizationVO> organizationRoots=TreeUtils.build(mapper.all(null).stream().map(this::view).toList(),organizationMatches);
        int rootCount=organizationRoots.size();
        int pageCount=(rootCount+organizationQuery.pageSize()-1)/organizationQuery.pageSize();
        long rootOffset=(long)(organizationQuery.pageNum()-1)*organizationQuery.pageSize();
        List<OrganizationVO> pageRoots=rootOffset>=rootCount ? List.of()
                : organizationRoots.subList((int)rootOffset,(int)Math.min(rootOffset+organizationQuery.pageSize(),rootCount));
        return new ListPageVO<>(pageRoots,rootCount,pageCount,organizationQuery.pageNum(),organizationQuery.pageSize());
    }
    private Predicate<OrganizationVO> organizationPredicate(List<FilterConditionDTO> organizationFilters) {
        if (organizationFilters.size()>4) throw invalidQuery();
        Set<String> filterFields=new HashSet<>();
        Predicate<OrganizationVO> organizationMatches=organization -> true;
        for (FilterConditionDTO organizationFilter:organizationFilters) {
            if (organizationFilter==null || organizationFilter.fieldName()==null || !filterFields.add(organizationFilter.fieldName())) throw invalidQuery();
            Object filterValue=organizationFilter.fieldValue();
            Predicate<OrganizationVO> condition;
            switch (organizationFilter.fieldName()) {
                case "name" -> {
                    if (organizationFilter.comparison()!=FilterOperatorEnum.LIKE || !(filterValue instanceof String organizationName)
                            || organizationName.isBlank() || organizationName.length()>100) throw invalidQuery();
                    condition=organization -> organization.name().contains(organizationName.trim());
                }
                case "nature" -> {
                    if (organizationFilter.comparison()!=FilterOperatorEnum.EQUAL || !(filterValue instanceof String organizationNature)
                            || organizationNature.isBlank() || organizationNature.length()>32) throw invalidQuery();
                    condition=organization -> organizationNature.equals(organization.nature());
                }
                case "type" -> {
                    if (organizationFilter.comparison()!=FilterOperatorEnum.IN || !(filterValue instanceof List<?> organizationTypes)
                            || organizationTypes.isEmpty() || organizationTypes.size()>100 || organizationTypes.stream().anyMatch(
                                    organizationType -> !(organizationType instanceof String typeCode) || typeCode.isBlank() || typeCode.length()>32)) throw invalidQuery();
                    condition=organization -> organizationTypes.contains(organization.type());
                }
                case "status" -> {
                    if (organizationFilter.comparison()!=FilterOperatorEnum.EQUAL || !(filterValue instanceof Integer organizationStatus)
                            || (organizationStatus!=0 && organizationStatus!=1)) throw invalidQuery();
                    condition=organization -> organization.status()==organizationStatus;
                }
                default -> throw invalidQuery();
            }
            organizationMatches=organizationMatches.and(condition);
        }
        return organizationMatches;
    }
    private ManagementException invalidQuery() {
        return ManagementException.invalid(ResultCodeEnum.INVALID_REQUEST,"组织筛选字段、比较方式、值或分页参数不合法");
    }
    @Override @Transactional
    public OrganizationVO update(long id, OrganizationWriteDTO input) {
        String operator=currentUser.requireAdmin();
        OrganizationEntity old=find(id);
        OrganizationWriteDTO data=normalize(input);
        sameEnterprise(old.enterpriseId(),data.enterpriseId());
        String ancestors=ancestorsFor(id,data.parentId(),data.enterpriseId());
        mapper.update(id,data,ancestors,operator);
        if (old.parentId()!=data.parentId()) {
            // 原子更新整个子树路径；任何节点超过长度限制时，根节点更新也一起回滚。
            List<OrganizationEntity> rows=mapper.all(null);
            Map<Long,List<OrganizationEntity>> children=new HashMap<>();
            for (OrganizationEntity row:rows) children.computeIfAbsent(row.parentId(),k->new ArrayList<>()).add(row);
            Deque<Long> queue=new ArrayDeque<>(); queue.add(id);
            Set<Long> visited=new HashSet<>();
            while (!queue.isEmpty()) {
                long parent=queue.remove();
                if (!visited.add(parent)) throw ManagementException.internal(SystemResultCodeEnum.INVALID_TREE);
                for (OrganizationEntity child:children.getOrDefault(parent,List.of())) {
                    String path=ancestorsFor(child.organizationId(),child.parentId(),child.enterpriseId());
                    mapper.updateAncestors(child.organizationId(),path,operator); queue.add(child.organizationId());
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
    @Override public void validateUserDepartment(Long deptId, Long enterpriseId) {
        currentUser.requireAdmin();
        if (deptId==null) return;
        OrganizationEntity department=find(deptId);
        sameEnterprise(department.enterpriseId(),enterpriseId);
    }
    private String ancestorsFor(long id,long parentId,Long enterpriseId) {
        List<String> path=new ArrayList<>(); Set<Long> visited=new HashSet<>();
        if (id!=0) visited.add(id);
        while (parentId!=0) {
            if (!visited.add(parentId)) throw conflict(SystemResultCodeEnum.INVALID_PARENT,"不能把自己或子孙设为上级部门");
            OrganizationEntity parent=mapper.find(parentId).orElseThrow(()->conflict(SystemResultCodeEnum.INVALID_PARENT,"上级部门不存在或已删除"));
            sameEnterprise(parent.enterpriseId(),enterpriseId);
            path.add(Long.toString(parentId)); parentId=parent.parentId();
            if (path.size()>=64) throw conflict(SystemResultCodeEnum.TREE_TOO_DEEP,"部门层级最多64层");
        }
        Collections.reverse(path);
        String ancestors=String.join(",",path);
        if (ancestors.length()>500) throw conflict(SystemResultCodeEnum.ANCESTORS_TOO_LONG,"部门祖级路径超过500字符");
        return ancestors;
    }
    private void sameEnterprise(Long parentEnterpriseId,Long organizationEnterpriseId) {
        if (!Objects.equals(parentEnterpriseId,organizationEnterpriseId))
            throw conflict(SystemResultCodeEnum.SCOPE_MISMATCH,"节点、父节点及关联用户必须同企业；现有节点不支持修改企业归属");
    }
    private OrganizationWriteDTO normalize(OrganizationWriteDTO d) {
        return new OrganizationWriteDTO(d.parentId()==null?0:d.parentId(),d.name().trim(),optionalText(d.shortName()),
                optionalText(d.code()),optionalText(d.email()),optionalText(d.phone()),optionalText(d.leader()),optionalText(d.nature()),
                optionalText(d.type()),optionalText(d.remark()),d.sort()==null?0:d.sort(),d.status()==null?1:d.status(),d.enterpriseId());
    }
    private String optionalText(String organizationText) { return organizationText==null || organizationText.isBlank() ? null : organizationText.trim(); }
    private OrganizationEntity find(long id) {
        return mapper.find(id).orElseThrow(()->ManagementException.missing(SystemResultCodeEnum.ORGANIZATION_NOT_FOUND,"部门不存在或已删除"));
    }
    private ManagementException conflict(SystemResultCodeEnum code,String message) { return ManagementException.conflict(code,message); }
    private OrganizationVO view(OrganizationEntity e) {
        return new OrganizationVO(e.organizationId(),e.parentId(),e.ancestors(),e.name(),e.shortName(),e.code(),e.email(),e.phone(),e.leader(),
                e.nature(),e.type(),e.remark(),e.sort(),e.status(),e.enterpriseId(),e.createBy(),e.updateBy(),e.createTime(),e.updateTime(),new ArrayList<>());
    }
}
