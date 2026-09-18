import type { ComponentType } from 'react';
import {
  Activity,
  BarChart3,
  Bell,
  BriefcaseBusiness,
  CalendarDays,
  CandlestickChart,
  Component,
  Database,
  FlaskConical,
  FormInput,
  Gauge,
  History,
  Home,
  Layers,
  LayoutDashboard,
  LayoutGrid,
  LayoutTemplate,
  MessageSquareQuote,
  Navigation,
  Newspaper,
  Search,
  Settings2,
  Star,
} from 'lucide-react';

/**
 * 菜单图标注册表：图标名（字符串）→ lucide 组件。
 * 菜单数据（manifest / menudata）只保存图标名字符串（可序列化、可持久化），
 * 渲染层据此表把名字解析回组件；MenuStore 持久化时无需再针对图标做特殊处理。
 */
export const menuIconRegistry: Record<string, ComponentType<{ className?: string }>> = {
  Activity,
  BarChart3,
  Bell,
  BriefcaseBusiness,
  CalendarDays,
  CandlestickChart,
  Component,
  Database,
  FlaskConical,
  FormInput,
  Gauge,
  History,
  Home,
  Layers,
  LayoutDashboard,
  LayoutGrid,
  LayoutTemplate,
  MessageSquareQuote,
  Navigation,
  Newspaper,
  Search,
  Settings2,
  Star,
};
