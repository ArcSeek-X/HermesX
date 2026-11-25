package hermesx.system.vo;

import com.fasterxml.jackson.annotation.JsonIgnore;
import hermesx.system.base.TreeNode;
import java.util.List;

/** 查询结果树；children随当前页一次返回，不用于触发懒加载。 */
public record OrganizationVO(Long organizationId, long parentId, String ancestors, String name,
        String shortName, String code, String email, String phone, String leader, String nature,
        String type, String remark, int sort, int status, Long enterpriseId,
        String createBy, String updateBy, String createTime, String updateTime,
        List<OrganizationVO> children) implements TreeNode<OrganizationVO> {
    @Override @JsonIgnore public Long id() { return organizationId; }
}
