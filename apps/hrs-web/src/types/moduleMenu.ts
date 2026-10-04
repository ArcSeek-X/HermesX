/**
 * @file moduleMenu.ts
 * @description 菜单相关类型定义：模块标识（ModuleId）、导航菜单节点（NavMenuNode）、
 *   模块菜单（NavModuleNode，即模块级元数据 + 菜单树）及按模块划分的菜单数据（ModuleMenuData）。
 *   作为 MenuStore 与布局组件（SidebarNav / ApplicationMenu）之间的类型契约，
 *   数据由 router/manifest.ts（MENU_MANIFEST 真源）经 MenuStore 构建而来。
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-10-04
 */

/**
 * 模块唯一标识，取值为数据真源 MENU_MANIFEST 中的模块 id；
 * 运行期合法性由 MenuStore.getValidModuleId 校验。
 */
export type ModuleId = string;

/**
 * 导航菜单节点（菜单树中的节点）。
 * 同一套字段同时承载一级（分组）与二级（子项），供左侧导航 SidebarNav 渲染、HeroUI Tree 消费；
 * 由 router/manifest 的路由节点经 MenuStore 转换生成。
 */
export type NavMenuNode = {
  /** 节点唯一标识，同时作为 HeroUI Tree 的节点 id */
  menuId: string;
  /** 菜单名称：i18n key 或直写文案 */
  menuName?: string;
  /** 路由路径；为空表示不可跳转 */
  routePath?: string;
  /** 图标名（lucide-react 组件名），运行时按名称解析回组件 */
  menuIcon?: string;
  /** 菜单徽章文本 */
  menuBadge?: string;
  /** 菜单所在区域：header / content / footer，使用方据此拆分渲染 */
  menuPosition: 'header' | 'content' | 'footer';
  /** 菜单层级（从 0 起），用于缩进等展示 */
  level: number;
  /** 菜单类型：page=可跳转页 / group=分组（仅分区标题，不可点击）/ redirect / fallback */
  menuType?: 'page' | 'group' | 'redirect' | 'fallback';
  /** 是否默认展开 */
  menuExpanded: boolean;
  /** 页面描述文案，用于 tooltip 等 */
  description: string;
  /** 是否精确匹配路由高亮 */
  exact?: boolean;
  /** 子菜单节点；存在时渲染为嵌套项 */
  children?: NavMenuNode[];
};

/**
 * 模块菜单：单个模块的「模块级元数据 + 菜单树」聚合。
 * 作为 ModuleMenuData 的值，由 MenuStore.buildRuntimeMenuData 依据 MENU_MANIFEST 构建；
 * ApplicationMenu 读取其元数据渲染「我的应用」入口，SidebarNav 读取 children 渲染侧栏。
 */
export type NavModuleNode = {
  /** 模块唯一标识，也是 currentModuleId 取值与持久化键 */
  moduleId: ModuleId;
  /** 模块名称：i18n key 或直写文案 */
  moduleName: string;
  /** 模块描述文案 */
  moduleDescription?: string;
  /** 模块根路由路径 */
  routePath?: string;
  /** 所属分组 id，便于按分组聚合展示 */
  moduleGroupId?: string;
  /** 所属分组名称 */
  moduleGroupName?: string;
  /** 模块图标名（lucide-react 组件名），运行时解析回组件 */
  moduleIcon?: string;
  /** 该模块下的菜单树，节点结构见 NavMenuNode */
  children: NavMenuNode[];
};

/**
 * 按模块划分的菜单数据。
 * 键为 moduleId，值为 NavModuleNode；由 MenuStore 持久化到 localStorage，
 * 作为全量菜单数据源，供 ApplicationMenu 与 SidebarNav 读取。
 */
export type ModuleMenuData = Record<ModuleId, NavModuleNode>;
