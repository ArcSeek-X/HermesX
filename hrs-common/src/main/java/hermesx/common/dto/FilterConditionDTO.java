package hermesx.common.dto;

import hermesx.common.enums.FilterOperatorEnum;

/** fieldValue为JSON标量或数组，业务服务负责校验其具体类型。 */
public record FilterConditionDTO(String fieldName, FilterOperatorEnum comparison, Object fieldValue) {}
