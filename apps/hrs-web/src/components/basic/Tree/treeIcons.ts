/**
 * @file treeIcons.ts
 * @description 树的具名图标注册表；显式导入避免把整个图标库打进基础组件。
 * @author Lensgcx (GaoCangxiong)
 */
import { Archive, Building2, Database, File, FileCode, FileText, Folder, FolderOpen, Globe, Home, Layers, Package, Settings, Shield, Tag, Users } from 'lucide-react';
import type { TreeIconComponents } from './types';

/** 内置名称区分大小写；业务可通过iconComponentsData扩展任意图标。 */
export const treeIconComponentsData: TreeIconComponents = {
  Archive, Building2, Database, File, FileCode, FileText, Folder, FolderOpen,
  Globe, Home, Layers, Package, Settings, Shield, Tag, Users,
};
