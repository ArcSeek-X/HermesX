package hermesx.system.controller;

import hermesx.system.dto.OrganizationWriteDTO;
import hermesx.system.vo.OrganizationVO;
import hermesx.system.service.IOrganizationService;
import hermesx.common.rest.RestResult;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import java.util.List;

/** HTTP边界只负责路由、格式校验和响应，不直接访问Mapper。 */
@RestController
@RequestMapping("/api/system/organizations")
public class OrganizationController {
    private final IOrganizationService service;
    public OrganizationController(IOrganizationService service) { this.service=service; }
    @PostMapping public ResponseEntity<RestResult<OrganizationVO>> create(@Valid @RequestBody OrganizationWriteDTO data) {
        OrganizationVO result=service.create(data);
        return ResponseEntity.created(java.net.URI.create("/api/system/organizations/"+result.id())).body(RestResult.success(result));
    }
    @GetMapping("/{id}") public RestResult<OrganizationVO> get(@PathVariable("id") @Positive long id) { return RestResult.success(service.get(id)); }
    @GetMapping("/tree") public RestResult<List<OrganizationVO>> tree(
            @RequestParam(value="keyword",required=false) @Size(max=128) String keyword,
            @RequestParam(value="status",required=false) @Min(0) @Max(1) Integer status,
            @RequestParam(value="enterpriseId",required=false) @Positive Long enterpriseId,
            @RequestParam(value="organizationId",required=false) @Positive Long organizationId) {
        return RestResult.success(service.tree(keyword,status,enterpriseId,organizationId));
    }
    @PutMapping("/{id}") public RestResult<OrganizationVO> update(@PathVariable("id") @Positive long id,
            @Valid @RequestBody OrganizationWriteDTO data) { return RestResult.success(service.update(id,data)); }
    @DeleteMapping("/{id}")
    public RestResult<Boolean> delete(@PathVariable("id") @Positive long id) { service.delete(id); return RestResult.success(true); }
}
