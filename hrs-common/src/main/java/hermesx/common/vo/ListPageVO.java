package hermesx.common.vo;

import java.util.List;

/** total按业务定义计数；组织列表以根组织为单位。 */
public record ListPageVO<T>(List<T> list, long total, int pages, int pageNum, int pageSize) {}
