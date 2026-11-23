package hermesx.system.service;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import hermesx.common.vo.PageVO;
import hermesx.system.dto.*;
import hermesx.system.vo.UserVO;

/** 业务契约：不暴露 SQL、HTTP 请求、数据库连接或密码密文。 */
public interface IUserService {
    UserVO create(@Valid CreateUserDTO data);
    UserVO get(@Positive long id);
    PageVO<UserVO> list(@Size(max = 128) String keyword, @Min(0) @Max(1) Integer status, @Positive Long deptId, @Positive Long enterpriseId, @Positive Long organizationId, @Min(1) int page, @Min(1) @Max(100) int pageSize);
    UserVO update(@Positive long id, @Valid UpdateUserDTO data);
    void delete(@Positive long id);
}
