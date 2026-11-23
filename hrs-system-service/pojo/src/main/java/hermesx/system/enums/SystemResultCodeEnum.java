package hermesx.system.enums;

import hermesx.common.rest.ResultCode;

/** 集中维护稳定结果码与默认文案；不允许各接口重复手写一套编号。 */
public enum SystemResultCodeEnum implements ResultCode {
    USER_NOT_FOUND("USER_NOT_FOUND", "用户不存在或已删除。"),
    USERNAME_EXISTS("USERNAME_EXISTS", "登录账号已存在。"),
    ORGANIZATION_NOT_FOUND("ORGANIZATION_NOT_FOUND", "部门不存在或已删除。"),
    MENU_NOT_FOUND("MENU_NOT_FOUND", "菜单不存在或已删除。"),
    MENU_CODE_EXISTS("MENU_CODE_EXISTS", "菜单业务标识已存在。"),
    MENU_ROUTE_EXISTS("MENU_ROUTE_EXISTS", "页面路由已存在。"),
    HAS_CHILDREN("HAS_CHILDREN", "存在下级数据，不能删除。"),
    DEPARTMENT_IN_USE("DEPARTMENT_IN_USE", "部门仍关联用户，不能删除。"),
    INVALID_PARENT("INVALID_PARENT", "父节点无效或会造成循环引用。"),
    SCOPE_MISMATCH("SCOPE_MISMATCH", "企业或组织归属不一致。"),
    INVALID_MENU_TYPE("INVALID_MENU_TYPE", "菜单父子类型不符合规则。"),
    TREE_TOO_DEEP("TREE_TOO_DEEP", "树形结构超过允许的层级。"),
    ANCESTORS_TOO_LONG("ANCESTORS_TOO_LONG", "部门祖级路径超过允许长度。"),
    INVALID_TREE("INVALID_TREE", "树形数据异常，请联系管理员。");

    private final String code;
    private final String message;
    SystemResultCodeEnum(String code, String message) { this.code=code; this.message=message; }
    @Override public String getCode() { return code; }
    @Override public String getMessage() { return message; }
}
