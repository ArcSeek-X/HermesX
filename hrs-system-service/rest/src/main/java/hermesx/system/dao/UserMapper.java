package hermesx.system.dao;

import hermesx.system.dto.UpdateUserDTO;
import hermesx.system.entity.UserEntity;
import java.util.List;
import java.util.Optional;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * 数据访问接口：这里声明“要查询/写入什么”，具体 SQL 在 resources/mapper/UserMapper.xml。
 * MyBatis 根据 @Mapper 创建代理实现，因此不需要再手写 UserMapperImpl 或转发 DAO。
 * @Param 名称与 XML 中的 #{名称} 对应，所有输入通过参数绑定传递。
 */
@Mapper
public interface UserMapper {
    /** 正常查询排除已删除用户，找不到时返回 Optional.empty()。 */
    Optional<UserEntity> find(@Param("id") long id);

    long count(@Param("keyword") String keyword, @Param("status") Integer status,
            @Param("deptId") Long deptId, @Param("enterpriseId") Long enterpriseId,
            @Param("organizationId") Long organizationId);

    List<UserEntity> list(@Param("keyword") String keyword, @Param("status") Integer status,
            @Param("deptId") Long deptId, @Param("enterpriseId") Long enterpriseId,
            @Param("organizationId") Long organizationId, @Param("limit") int limit, @Param("offset") long offset);

    /** INSERT RETURNING 返回本次新增的主键；输入密码已经由业务层转成哈希。 */
    long insert(@Param("username") String username, @Param("passwordHash") String passwordHash,
            @Param("nickname") String nickname, @Param("phone") String phone,
            @Param("email") String email, @Param("deptId") Long deptId,
            @Param("enterpriseId") Long enterpriseId, @Param("organizationId") Long organizationId,
            @Param("status") int status, @Param("operator") String operator);

    /** 返回实际影响行数，由业务层据此判断用户是否存在。 */
    int update(@Param("id") long id, @Param("data") UpdateUserDTO data, @Param("operator") String operator);

    int softDelete(@Param("id") long id, @Param("operator") String operator);
}
