/** 路由登录策略：public 静态可访问 / protected 需登录后访问。 */
export type RouteAuthPolicy = 'public' | 'protected';
/** 动态路由类型：page 渲染页面 / redirect loader 重定向 / fallback 预留兜底（当前仅构建前两者）。 */
export type RouteType = 'page' | 'redirect' | 'fallback';

/** 动态路由树节点，由菜单节点转换而来。 */
export type AsyncRouteNode = {
  /** 路由节点业务键，取自菜单 menuCode。 */
  routerKey: string;
  /** 页头标题（i18n 键或文案），写入路由 handle。 */
  routerName?: string;
  /** 浏览器路径；注入时去掉前导 '/' 作为受保护布局的子路由路径。 */
  routerPath: string;
  /** 页面模块相对路径（如 'pages/HomePage'），来自 menuPagePath；redirect 节点为空字符串。 */
  routerPagePath: string;
  /** 节点渲染方式，决定生成 lazy 页面还是 loader 重定向。 */
  routerType: RouteType;
  /** 从菜单透传的登录策略；动态注入不按它分流，鉴权由受保护布局守卫处理。 */
  auth?: RouteAuthPolicy;
  /** 重定向目标路径；仅 routerType 为 redirect 时有效。 */
  redirect?: string;
  /** 页头副标题（i18n 键或文案），写入路由 handle。 */
  routerDescription: string;
  /** 下层路由节点；注册时与父节点一起扁平化为路由对象。 */
  children?: AsyncRouteNode[];
};

/** 挂在 React Router 路由对象 handle 上的静态元数据，供页头 ShellHeader 经 useMatches 读取。 */
export type RouteHandle = {
  /** 页头标题（i18n 键或文案）。 */
  routerName?: string;
  /** 页头副标题（i18n 键或文案）。 */
  routerDescription?: string;
};
