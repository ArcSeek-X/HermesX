import type { RouteAuthPolicy } from './router';

/** 稳定业务标识（如 productModel、stock），不是数据库数字主键。 */
export type MenuCode = string;
/** 节点类型：module 模块入口 / group 分组 / page 可注册路由的页面。 */
export type MenuType = 'module' | 'group' | 'page';

/**
 * 统一菜单节点：模块、分组、页面共用字段和 children 结构。
 * 数据库字段使用下划线；前端与接口 JSON 使用小驼峰。
 */
export type NavMenuNode = {
  /** 数据库生成的主键；静态清单不编造数字 ID。 */
  id?: number;
  /** 数据库父节点 ID，根节点为 0；静态清单用 children 表达父子关系。 */
  menuParentId?: number;
  /** 节点业务键：模块以它索引 menuData，页面以它作为路由 routerKey。 */
  menuCode: MenuCode;
  /** 菜单显示名；可为 i18n 键或直接文案。 */
  menuName: string;
  /** 菜单描述；可为 i18n 键或直接文案，页面会透传为路由 handle 的副标题。 */
  menuDescription: string;
  /** 节点类型，决定导航层级与是否注册为路由。 */
  menuType: MenuType;
  /** 浏览器路径；仅 page 节点用于注册动态路由，分组可省略。 */
  menuRoutePath?: string;
  /** 页面模块相对路径（如 'pages/HomePage'）；仅 page 节点需要，供懒加载解析。 */
  menuPagePath?: string;
  /** 图标白名单键（如 'Home'）；未命中时侧栏显示空图标。 */
  menuIcon?: string;
  /** 预留徽标文案；当前渲染层未读取该字段。 */
  menuBadge?: string;
  /** 菜单分区：content 主区 / footer 底部；侧栏按此分组渲染。 */
  menuPosition: 'header' | 'content' | 'footer';
  /** 初始展开状态；用户手动切换后以用户值为准。 */
  menuExpanded: boolean;
  /** 是否显示导航入口；隐藏不代表禁止访问路由。 */
  menuVisible: boolean;
  /** 同级按升序排列；层级由 children 表达，不持久化 level。 */
  menuSort: number;
  /** 1=启用，0=禁用；禁用节点及其子树不参与导航和动态路由。 */
  menuStatus: 0 | 1;
  /** 权限标识预留；前端显示控制不能替代后端授权。 */
  menuPermission?: string;
  /** 子节点列表，模块与分组通过它组织层级。 */
  children?: NavMenuNode[];
  /** 路由登录策略，从菜单透传到动态路由；实际鉴权由受保护布局守卫统一处理。 */
  auth?: RouteAuthPolicy;
  /** 高亮匹配是否要求路径完全一致；默认按前缀匹配，仅影响侧栏高亮。 */
  exact?: boolean;
};

/** 按模块 menuCode 索引；值仍是同一套 NavMenuNode，不另设模块数据格式。 */
export type ModuleMenuData = Record<MenuCode, NavMenuNode>;
