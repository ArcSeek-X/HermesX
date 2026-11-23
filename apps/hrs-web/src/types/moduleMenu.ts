import type { RouteAuthPolicy } from './router';

/** 稳定业务标识，例如 productModel、stock、watchlist，不是数据库数字主键。 */
export type MenuCode = string;
export type MenuType = 'module' | 'group' | 'page';

/**
 * 统一菜单节点：模块、分组、页面共用字段和 children 结构。
 * 数据库字段使用下划线；前端、接口 JSON 使用这里的小驼峰命名。
 */
export type NavMenuNode = {
  /** 数据库生成的主键；当前静态清单不编造数字 ID。 */
  id?: number;
  /** 数据库父节点 ID，根节点为 0；静态清单通过 children 表达父子关系。 */
  menuParentId?: number;
  menuCode: MenuCode;
  /** 名称、描述均支持国际化键或直写文案。 */
  menuName: string;
  menuDescription: string;
  menuType: MenuType;
  menuRoutePath?: string;
  /** 对应已构建的页面模块；模块和分组无需配置页面文件。 */
  menuPagePath?: string;
  menuIcon?: string;
  menuBadge?: string;
  menuPosition: 'header' | 'content' | 'footer';
  menuExpanded: boolean;
  /** 隐藏导航入口不代表禁止访问路由。 */
  menuVisible: boolean;
  /** 同级按升序排列；层级由 children 计算，不持久化 level。 */
  menuSort: number;
  /** 1=启用，0=禁用；禁用节点及其子树不参与导航和动态路由。 */
  menuStatus: 0 | 1;
  /** 权限标识预留；前端显示控制不能替代后端授权。 */
  menuPermission?: string;
  children?: NavMenuNode[];
  /** 前端路由扩展，保留当前登录策略，不属于本次数据库字段调整。 */
  auth?: RouteAuthPolicy;
  /** 仅用于前端高亮匹配，不是数据库字段。 */
  exact?: boolean;
};

/** 按模块 menuCode 索引；值仍然是同一套 NavMenuNode，不另设模块数据格式。 */
export type ModuleMenuData = Record<MenuCode, NavMenuNode>;
