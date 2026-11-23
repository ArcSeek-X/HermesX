package hermesx.system.vo;

import hermesx.system.base.TreeNode;
import java.util.List;

/** 只返回允许展示的字段；children 由服务端组装，叶节点为空列表。 */
public record OrganizationVO(Long id, long parentId, String ancestors, String name,
        String leader, String phone, String email, int sort, int status,
        Long enterpriseId, Long organizationId, String createBy, String updateBy, String createTime, String updateTime, List<OrganizationVO> children) implements TreeNode<OrganizationVO> {}
