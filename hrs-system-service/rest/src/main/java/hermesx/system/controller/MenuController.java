package hermesx.system.controller;

import hermesx.system.dto.MenuWriteDTO;
import hermesx.system.vo.MenuVO;
import hermesx.system.service.IMenuService;
import hermesx.common.rest.RestResult;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import java.util.List;

/** HTTP边界只负责路由、格式校验和响应，不直接访问Mapper。 */
@RestController
@RequestMapping("/api/system")
public class MenuController {
    private final IMenuService service;
    public MenuController(IMenuService service) { this.service=service; }
    /** 登录后的导航加载接口：无请求体；认证和 CSRF 仍交给现有 SecurityFilterChain。 */
    @PostMapping("/list-menu")
    public RestResult<List<MenuVO>> listMenu() { return RestResult.success(service.listMenu()); }

    /** 以下为管理接口；筛选查询与导航完整树查询分工不同。 */
    @PostMapping("/menus") public ResponseEntity<RestResult<MenuVO>> create(@Valid @RequestBody MenuWriteDTO data) {
        MenuVO result=service.create(data);
        return ResponseEntity.created(java.net.URI.create("/api/system/menus/"+result.id())).body(RestResult.success(result));
    }
    @GetMapping("/menus/{id}") public RestResult<MenuVO> get(@PathVariable("id") @Positive long id) { return RestResult.success(service.get(id)); }
    @GetMapping("/menus/tree") public RestResult<List<MenuVO>> tree(
            @RequestParam(value="keyword",required=false) @Size(max=128) String keyword,
            @RequestParam(value="status",required=false) @Min(0) @Max(1) Integer status,
            @RequestParam(value="enterpriseId",required=false) @Positive Long enterpriseId,
            @RequestParam(value="organizationId",required=false) @Positive Long organizationId) {
        return RestResult.success(service.tree(keyword,status,enterpriseId,organizationId));
    }
    @PutMapping("/menus/{id}") public RestResult<MenuVO> update(@PathVariable("id") @Positive long id,
            @Valid @RequestBody MenuWriteDTO data) { return RestResult.success(service.update(id,data)); }
    @DeleteMapping("/menus/{id}")
    public RestResult<Boolean> delete(@PathVariable("id") @Positive long id) { service.delete(id); return RestResult.success(true); }
}
