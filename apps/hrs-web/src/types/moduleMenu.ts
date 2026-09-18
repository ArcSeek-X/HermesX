export type ModuleId = 'productModel' | 'developmentMode';

/** 菜单节点：一级（分组）与二级（子项）共用同一套字段。 */
export type NavMenuNode = {
  /** 唯一标识（即 HeroUI Tree 节点的 id） */
  menuId: string;
  /** 菜单名称：i18n key 或直写文案 */
  menuName?: string;
  /** 路由路径：不传或空串表示不可跳转 */
  routePath?: string;
  /** 菜单图标：图标名字符串（在 menuIconRegistry 中映射回组件） */
  menuIcon?: string;
  /** 菜单徽章标志 */
  menuBadge?: string;
  /** 菜单所在区域 */
  menuPosition: 'header' | 'content' | 'footer';
  /** 菜单层级 */
  level: number;
  /** 菜单是否默认展开 */
  menuExpanded: boolean;
  /** 页面描述文案 */
  description: string;
  /** 是否精确匹配高亮 */
  exact?: boolean;
  /** 二级菜单 */
  children?: NavMenuNode[];
};

/** 按模块划分的菜单数据。 */
export type ModuleMenuData = Record<ModuleId, NavMenuNode[]>;
