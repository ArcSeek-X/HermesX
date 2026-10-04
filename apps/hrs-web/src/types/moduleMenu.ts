/**
 * 模块唯一标识。
 * 与 NavMenuNode.menuId 同理：取值来自数据真源（MENU_MANIFEST 的模块 id），
 * 不写死为固定字面量联合，保持为动态字符串；运行期合法性由 MenuStore.getValidModuleId 校验。
 */
export type ModuleId = string;

/** 菜单节点：一级（分组）与二级（子项）共用同一套字段。 */
export type NavMenuNode = {
  /** 唯一标识（即 HeroUI Tree 节点的 id） */
  menuId: string;
  /** 菜单名称：i18n key 或直写文案 */
  menuName?: string;
  /** 路由路径：不传或空串表示不可跳转 */
  routePath?: string;
  /** 菜单图标：图标名字符串（lucide-react 组件名，按名称解析回组件） */
  menuIcon?: string;
  /** 菜单徽章标志 */
  menuBadge?: string;
  /** 菜单所在区域 */
  menuPosition: 'header' | 'content' | 'footer';
  /** 菜单层级 */
  level: number;
  /** 菜单类型：page=可跳转页 / group=分组（仅作分区标题、不可点击跳转） / redirect / fallback */
  menuType?: 'page' | 'group' | 'redirect' | 'fallback';
  /** 菜单是否默认展开 */
  menuExpanded: boolean;
  /** 页面描述文案 */
  description: string;
  /** 是否精确匹配高亮 */
  exact?: boolean;
  /** 二级菜单 */
  children?: NavMenuNode[];
};

/** 模块菜单：模块级元数据 + 该模块下的菜单树。 */
export type NavModuleNode = {
  /** 模块唯一标识（也是 currentModuleId 取值与持久化键） */
  moduleId: ModuleId;
  /** 模块名称：i18n key 或直写文案 */
  moduleName: string;
  /** 模块描述文案 */
  moduleDescription?: string;
  /** 模块根路由路径（可选） */
  routePath?: string;
  /** 模块所属分组 id（可选，便于按分组聚合） */
  moduleGroupId?: string;
  /** 模块分组名称（可选） */
  moduleGroupName?: string;
  /** 模块图标名（lucide-react 组件名，按名称解析，可选） */
  moduleIcon?: string;
  /** 该模块下的菜单树（已由路由节点转换） */
  children: NavMenuNode[];
};

/** 按模块划分的菜单数据：键为 moduleId，值为模块（含元数据与菜单树）。 */
export type ModuleMenuData = Record<ModuleId, NavModuleNode>;
