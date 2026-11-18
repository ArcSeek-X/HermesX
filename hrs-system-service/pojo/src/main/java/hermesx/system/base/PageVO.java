package hermesx.system.base;

import java.util.List;

/** 分页结果：total 是匹配总数，rows 只是当前页数据。 */
public record PageVO<T>(List<T> rows, long total, int page, int pageSize) {}
