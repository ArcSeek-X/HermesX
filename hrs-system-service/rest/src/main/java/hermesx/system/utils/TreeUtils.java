package hermesx.system.utils;

import hermesx.system.base.TreeNode;
import java.util.*;
import java.util.function.Predicate;

/** 纯内存组树：不读取会话、数据库，也不决定谁有权限。 */
public final class TreeUtils {
    private TreeUtils() {}
    public static <T extends TreeNode<T>> List<T> build(List<T> ordered, Predicate<T> matches) {
        Map<Long,T> nodes=new LinkedHashMap<>();
        for (T node:ordered) {
            if (nodes.put(node.id(),node)!=null) throw new IllegalStateException("树存在重复节点");
        }
        Set<Long> included=new HashSet<>();
        for (T node:ordered) {
            // 即使筛选没有命中，也检查坏数据，不能用空结果掩盖循环或孤立节点。
            Set<Long> visited=new HashSet<>();
            T current=node;
            while (current!=null) {
                if (!visited.add(current.id())) throw new IllegalStateException("树存在循环引用");
                if (current.parentId()==0) break;
                current=nodes.get(current.parentId());
                if (current==null) throw new IllegalStateException("树存在缺失的父节点");
            }
            if (matches.test(node)) included.addAll(visited);
        }
        List<T> roots=new ArrayList<>();
        // 两次遍历，父节点不必先出现；保留Mapper给定的sort、id顺序。
        for (T node:ordered) {
            if (!included.contains(node.id())) continue;
            if (node.parentId()==0) roots.add(node);
            else nodes.get(node.parentId()).children().add(node);
        }
        return roots;
    }
}
