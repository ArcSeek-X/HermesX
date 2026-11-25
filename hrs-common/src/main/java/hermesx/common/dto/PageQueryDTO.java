package hermesx.common.dto;

import java.util.List;

/** 列表查询共用分页字段；不包含租户身份或SQL字段名。 */
public record PageQueryDTO(Integer pageNum, Integer pageSize, List<FilterConditionDTO> filterList) {
    public PageQueryDTO {
        pageNum = pageNum == null ? 1 : pageNum;
        pageSize = pageSize == null ? 20 : pageSize;
        filterList = filterList == null ? List.of() : filterList;
    }
}
