// React 类型导入
import type React from 'react';
// 从 lucide-react 引入各分类所需的图标
import { Bell, Bot, Database, Layers3, LineChart, Settings2, SlidersHorizontal } from 'lucide-react';
// lucide 图标组件的属性类型
import type { LucideIcon } from 'lucide-react';
// 通用的列表卡片组件，用于渲染单个分类项
import { ListCard } from '../common/ListCard';
// 多语言上下文，用于获取当前语言与翻译函数
import { useUiLanguage } from '../../contexts/UiLanguageContext';
// 分类标题与描述的 i18n 工具函数
import { getCategoryDescription, getCategoryTitle } from '../../utils/systemConfigI18n';
// 系统配置相关的类型定义
import type { SystemConfigCategory, SystemConfigCategorySchema, SystemConfigItem } from '../../types/systemConfig';

// 组件 Props 定义
interface SettingsCategoryNavProps {
  // 所有配置分类的 schema 列表
  categories: SystemConfigCategorySchema[];
  // 按分类名归类的配置项集合（用于计算每个分类下的条目数量）
  itemsByCategory: Record<string, SystemConfigItem[]>;
  // 当前选中的分类标识
  activeCategory: string;
  // 选中某个分类时的回调
  onSelect: (category: string) => void;
}

// 分类标识与图标组件的映射表，决定每个分类展示哪种图标
const categoryIconMap: Partial<Record<SystemConfigCategory, LucideIcon>> = {
  system: Settings2,          // 系统设置
  base: SlidersHorizontal,    // 基础设置
  data_source: Database,      // 数据源
  ai_model: Layers3,          // AI 模型
  notification: Bell,         // 通知
  agent: Bot,                 // 智能体
  backtest: LineChart,        // 回测
};

// 设置页左侧分类导航组件
export const SettingsCategoryNav: React.FC<SettingsCategoryNavProps> = ({
  categories,
  itemsByCategory,
  activeCategory,
  onSelect,
}) => {
  // 获取当前界面语言与翻译函数
  const { language, t } = useUiLanguage();

  return (
    // 外层导航容器：整高、圆角、边框、卡片背景与阴影
    <nav
      className="h-full rounded-lg border settings-border bg-card/90 p-2 shadow-soft-card backdrop-blur-sm"
      aria-label={t('settings.categoryNavTitle')}
    >
      {/* 顶部标题区：仅在 lg 及以上断点显示 */}
      <div className="hidden px-2 pb-3 pt-2 lg:block">
        <p className="settings-accent-text text-xs font-semibold uppercase tracking-[0.24em]">{t('settings.categoryNavTitle')}</p>
        <p className="mt-1 text-[11px] leading-relaxed text-muted-text">{t('settings.categoryNavDescription')}</p>
      </div>

      {/* 分类列表：小屏横向滚动，大屏纵向堆叠 */}
      <div className="flex gap-2 overflow-x-auto pb-1 lg:block lg:space-y-1.5 lg:overflow-visible lg:pb-0">
        {categories.map((category, index) => {
          // 判断当前分类是否为选中项
          const isActive = category.category === activeCategory;
          // 统计该分类下的配置项数量
          const count = (itemsByCategory[category.category] || []).length;
          // 取多语言标题
          const title = getCategoryTitle(category.category, category.title, language);
          // 取多语言描述
          const description = getCategoryDescription(category.category, category.description, language);
          // 根据分类映射获取图标，未命中时回退到 Layers3
          const Icon = categoryIconMap[category.category] ?? Layers3;

          return (
            // 渲染单个分类卡片
            <ListCard
              key={category.category}
              icon={Icon}
              title={title}
              description={description}
              count={count}
              isActive={isActive}
              ordinal={index}
              onClick={() => onSelect(category.category)}
            />
          );
        })}
      </div>
    </nav>
  );
};
