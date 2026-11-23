package hermesx.system.service;

import hermesx.system.dto.MenuWriteDTO;
import hermesx.system.vo.MenuVO;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.util.List;

/** 业务接口：校验契约在接口声明，所有入口都通过Service执行。 */
public interface IMenuService {
    /** 导航查询不接收管理筛选条件，返回已启用的 module/group/page 树，禁用父节点整棵子树排除。 */
    List<MenuVO> listMenu();
    MenuVO create(@Valid @NotNull MenuWriteDTO data);
    MenuVO get(@Positive long id);
    List<MenuVO> tree(@Size(max=128) String keyword, @Min(0) @Max(1) Integer status,
            @Positive Long enterpriseId, @Positive Long organizationId);
    MenuVO update(@Positive long id, @Valid @NotNull MenuWriteDTO data);
    void delete(@Positive long id);
}
