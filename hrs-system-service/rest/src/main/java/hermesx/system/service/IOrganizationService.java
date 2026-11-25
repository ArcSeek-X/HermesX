package hermesx.system.service;

import hermesx.system.dto.OrganizationWriteDTO;
import hermesx.common.dto.PageQueryDTO;
import hermesx.common.vo.ListPageVO;
import hermesx.system.vo.OrganizationVO;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.util.List;

/** 业务接口：校验契约在接口声明，所有入口都通过Service执行。 */
public interface IOrganizationService {
    OrganizationVO create(@Valid @NotNull OrganizationWriteDTO data);
    OrganizationVO get(@Positive long id);
    List<OrganizationVO> tree(@Positive Long enterpriseId);
    ListPageVO<OrganizationVO> queryOrganizations(@NotNull PageQueryDTO organizationQuery);
    OrganizationVO update(@Positive long id, @Valid @NotNull OrganizationWriteDTO data);
    void delete(@Positive long id);
    /** 用户管理同服务公开调用此方法，不能绕过部门归属校验直接写UserMapper。 */
    void validateUserDepartment(@Positive Long deptId, @Positive Long enterpriseId);
}
