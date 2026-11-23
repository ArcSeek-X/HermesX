package hermesx.system.service.impl;

import hermesx.system.base.PageVO;
import hermesx.system.dao.UserMapper;
import hermesx.system.dto.*;
import hermesx.system.entity.UserEntity;
import hermesx.system.vo.UserVO;
import hermesx.system.exception.UserNotFoundException;
import hermesx.system.exception.ManagementException;
import hermesx.common.rest.ResultCodeEnum;
import hermesx.system.security.CurrentUser;
import hermesx.system.service.IUserService;
import java.nio.charset.StandardCharsets;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.validation.annotation.Validated;

/** 业务层负责权限、规则与事务；即使被其他入口调用，也不能绕过这些检查。 */
@Service
@Validated
public class UserServiceImpl implements IUserService {
    private final UserMapper mapper;
    private final PasswordEncoder passwords;
    private final CurrentUser currentUser;
    public UserServiceImpl(UserMapper mapper, PasswordEncoder passwords, CurrentUser currentUser) {
        this.mapper = mapper; this.passwords = passwords; this.currentUser = currentUser;
    }
    @Override @Transactional
    public UserVO create(CreateUserDTO data) {
        String operator = currentUser.requireAdmin();
        // BCrypt 上限按字节算：中文密码不能只判断字符数量。
        if (data.password().getBytes(StandardCharsets.UTF_8).length > 72) {
            throw ManagementException.invalid(ResultCodeEnum.INVALID_REQUEST,"密码不能超过72个UTF-8字节。");
        }
        long id = mapper.insert(data.username().trim(), passwords.encode(data.password()), data.nickname().trim(),
                data.phone(), data.email(), data.deptId(), data.enterpriseId(), data.organizationId(), data.status() == null ? 1 : data.status(), operator);
        return view(find(id));
    }
    @Override public UserVO get(long id) { currentUser.requireAdmin(); return view(find(id)); }
    @Override @Transactional(readOnly = true)
    public PageVO<UserVO> list(String keyword, Integer status,
            Long deptId, Long enterpriseId, Long organizationId, int page, int pageSize) {
        currentUser.requireAdmin();
        String search = keyword == null || keyword.isBlank() ? null : keyword.trim();
        return new PageVO<>(mapper.list(search, status, deptId, enterpriseId, organizationId, pageSize, ((long) page - 1) * pageSize)
                .stream().map(this::view).toList(), mapper.count(search, status, deptId, enterpriseId, organizationId), page, pageSize);
    }
    @Override @Transactional
    public UserVO update(long id, UpdateUserDTO data) {
        String operator = currentUser.requireAdmin();
        UpdateUserDTO normalized = new UpdateUserDTO(data.nickname().trim(), data.phone(), data.email(), data.deptId(), data.enterpriseId(), data.organizationId(), data.status());
        if (mapper.update(id, normalized, operator) == 0) throw new UserNotFoundException();
        return view(find(id));
    }
    @Override @Transactional
    public void delete(long id) {
        if (mapper.softDelete(id, currentUser.requireAdmin()) == 0) throw new UserNotFoundException();
    }
    private UserEntity find(long id) { return mapper.find(id).orElseThrow(UserNotFoundException::new); }
    private UserVO view(UserEntity e) {
        return new UserVO(e.id(), e.username(), e.nickname(), e.phone(), e.email(), e.deptId(), e.enterpriseId(), e.organizationId(), e.status(),
                e.lastLoginTime(), e.createBy(), e.updateBy(), e.createTime(), e.updateTime());
    }
}
