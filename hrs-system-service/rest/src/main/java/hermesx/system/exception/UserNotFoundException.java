package hermesx.system.exception;

/** 查询或修改已删除/不存在的用户时，返回明确的 404。 */
public class UserNotFoundException extends RuntimeException {
    public UserNotFoundException() { super("用户不存在或已删除"); }
}
