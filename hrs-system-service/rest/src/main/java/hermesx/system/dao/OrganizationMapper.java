package hermesx.system.dao;

import hermesx.system.dto.OrganizationWriteDTO;
import hermesx.system.entity.OrganizationEntity;
import java.util.List;
import java.util.Optional;
import org.apache.ibatis.annotations.*;

/** Organization数据访问契约；实现由MyBatis创建，SQL位于同名XML。 */
@Mapper
public interface OrganizationMapper {
    Optional<OrganizationEntity> find(@Param("id") long id);
    List<OrganizationEntity> all(@Param("enterpriseId") Long enterpriseId);
    long insert(@Param("data") OrganizationWriteDTO data, @Param("ancestors") String ancestors, @Param("operator") String operator);
    int update(@Param("id") long id, @Param("data") OrganizationWriteDTO data, @Param("ancestors") String ancestors, @Param("operator") String operator);
    long countChildren(@Param("id") long id);
    int softDelete(@Param("id") long id, @Param("operator") String operator);
    long countUsers(@Param("id") long id);
    int updateAncestors(@Param("id") long id, @Param("ancestors") String ancestors, @Param("operator") String operator);
}
