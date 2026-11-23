package hermesx.system.service;

import hermesx.system.dto.OrganizationWriteDTO;
import hermesx.system.vo.OrganizationVO;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.util.List;

/** 业务接口：校验契约在接口声明，所有入口都通过Service执行。 */
public interface IOrganizationService {
    OrganizationVO create(@Valid @NotNull OrganizationWriteDTO data);
    OrganizationVO get(@Positive long id);
    List<OrganizationVO> tree(@Size(max=128) String keyword, @Min(0) @Max(1) Integer status,
            @Positive Long enterpriseId, @Positive Long organizationId);
    OrganizationVO update(@Positive long id, @Valid @NotNull OrganizationWriteDTO data);
    void delete(@Positive long id);
    /** 用户管理同服务公开调用此方法，不能绕过部门归属校验直接写UserMapper。 */
    void validateUserDepartment(@Positive Long deptId, @Positive Long enterpriseId, @Positive Long organizationId);
}
