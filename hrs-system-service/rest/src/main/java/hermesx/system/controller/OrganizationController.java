package hermesx.system.controller;

import hermesx.common.dto.PageQueryDTO;
import hermesx.common.rest.RestResult;
import hermesx.common.vo.ListPageVO;
import hermesx.system.dto.*;
import hermesx.system.vo.OrganizationVO;
import hermesx.system.service.IOrganizationService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Positive;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.net.URI;
import java.util.List;

/** HTTP边界：业务校验、分页和关联保护交给Service。 */
@RestController
@RequestMapping("/api/system/organization")
public class OrganizationController {
    private final IOrganizationService organizationService;
    public OrganizationController(IOrganizationService organizationService) { this.organizationService=organizationService; }

    @PostMapping("/list-organization")
    public RestResult<ListPageVO<OrganizationVO>> queryOrganizations(@RequestBody PageQueryDTO organizationQuery) {
        return RestResult.success(organizationService.queryOrganizations(organizationQuery));
    }
    @GetMapping("/get-organization-tree")
    public RestResult<List<OrganizationVO>> getOrganizationCandidates(
            @RequestParam(value="enterpriseId",required=false) @Positive Long enterpriseId) {
        return RestResult.success(organizationService.tree(enterpriseId));
    }
    @GetMapping("/detail-organization/{organizationId}")
    public RestResult<OrganizationVO> getOrganization(@PathVariable("organizationId") @Positive long organizationId) {
        return RestResult.success(organizationService.get(organizationId));
    }
    @PostMapping("/add-organization")
    public ResponseEntity<RestResult<OrganizationVO>> createOrganization(@Valid @RequestBody OrganizationWriteDTO organizationFields) {
        OrganizationVO organization=organizationService.create(organizationFields);
        return ResponseEntity.created(URI.create("/api/system/organization/detail-organization/"+organization.organizationId()))
                .body(RestResult.success(organization));
    }
    @PostMapping("/edit-organization")
    public RestResult<OrganizationVO> editOrganization(@Valid @RequestBody OrganizationEditDTO organizationEdit) {
        return RestResult.success(organizationService.update(organizationEdit.organizationId(),organizationEdit.organizationFields()));
    }
    @PostMapping("/delete-organization")
    public RestResult<Boolean> deleteOrganization(@Valid @RequestBody OrganizationDeleteDTO organizationDelete) {
        organizationService.delete(organizationDelete.organizationId());
        return RestResult.success(true);
    }
}
