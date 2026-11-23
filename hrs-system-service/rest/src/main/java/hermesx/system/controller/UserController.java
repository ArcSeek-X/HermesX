package hermesx.system.controller;

import hermesx.common.vo.PageVO;
import hermesx.system.dto.*;
import hermesx.system.vo.UserVO;
import hermesx.system.service.IUserService;
import hermesx.common.rest.RestResult;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.web.csrf.CsrfToken;

/** HTTP 层：只处理输入输出，所有业务都交给 Service。 */
@RestController
@RequestMapping("/api/system/users")
public class UserController {
    private final IUserService service;
    public UserController(IUserService service) { this.service = service; }
    @GetMapping("/csrf") public RestResult<CsrfToken> csrf(CsrfToken token) { return RestResult.success(token); }
    @PostMapping
    public ResponseEntity<RestResult<UserVO>> create(@Valid @RequestBody CreateUserDTO data) {
        UserVO user = service.create(data);
        return ResponseEntity.created(java.net.URI.create("/api/system/users/" + user.id())).body(RestResult.success(user));
    }
    @GetMapping("/{id}") public RestResult<UserVO> get(@PathVariable("id") @Positive long id) { return RestResult.success(service.get(id)); }
    @GetMapping public RestResult<PageVO<UserVO>> list(
            @RequestParam(value="keyword", required=false) @Size(max=128) String keyword,
            @RequestParam(value="status", required=false) @Min(0) @Max(1) Integer status,
            @RequestParam(value="deptId", required=false) @Positive Long deptId,
            @RequestParam(value="enterpriseId", required=false) @Positive Long enterpriseId,
            @RequestParam(value="organizationId", required=false) @Positive Long organizationId,
            @RequestParam(value="page", defaultValue="1") @Min(1) int page,
            @RequestParam(value="pageSize", defaultValue="20") @Min(1) @Max(100) int pageSize) {
        return RestResult.success(service.list(keyword, status, deptId, enterpriseId, organizationId, page, pageSize));
    }
    @PutMapping("/{id}") public RestResult<UserVO> update(@PathVariable("id") @Positive long id,
            @Valid @RequestBody UpdateUserDTO data) { return RestResult.success(service.update(id, data)); }
    @DeleteMapping("/{id}")
    public RestResult<Boolean> delete(@PathVariable("id") @Positive long id) { service.delete(id); return RestResult.success(true); }
}
