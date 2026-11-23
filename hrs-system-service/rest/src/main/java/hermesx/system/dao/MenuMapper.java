package hermesx.system.dao;

import hermesx.system.dto.MenuWriteDTO;
import hermesx.system.entity.MenuEntity;
import java.util.List;
import java.util.Optional;
import org.apache.ibatis.annotations.*;

/** Menu数据访问契约；实现由MyBatis创建，SQL位于同名XML。 */
@Mapper
public interface MenuMapper {
    Optional<MenuEntity> find(@Param("id") long id);
    List<MenuEntity> all(@Param("enterpriseId") Long enterpriseId, @Param("organizationId") Long organizationId);
    long insert(@Param("data") MenuWriteDTO data, @Param("operator") String operator);
    int update(@Param("id") long id, @Param("data") MenuWriteDTO data, @Param("operator") String operator);
    long countChildren(@Param("id") long id);
    int softDelete(@Param("id") long id, @Param("operator") String operator);
}
