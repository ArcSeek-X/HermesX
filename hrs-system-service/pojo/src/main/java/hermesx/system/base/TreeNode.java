package hermesx.system.base;

import java.util.List;

/** 只描述树视图的共同结构，供两个模块复用组树算法，不包含数据库或业务逻辑。 */
public interface TreeNode<T> {
    Long id();
    long parentId();
    List<T> children();
}
