package hermesx.system.base;

/** 统一错误结构：code 便于程序判断，message 便于人阅读，不包含内部 SQL。 */
public record ErrorVO(String code, String message) {}
