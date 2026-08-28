/**
 * @file HomePage.tsx
 * @description 系统首页
 * @module pages
 */
import React, { useState } from 'react';
import { AppPage } from '../components';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import { useTheme } from 'next-themes';
import { useThemeColor } from '../hooks/useThemeColor';
import LightBloom from '../components/vibeBack/LightBloom';
import { StockSearch } from '../components/StockSearch';

/**
 * 复盘页面组件
 *
 * 复盘工作台骨架：后续在此扩展历史复盘记录、大盘回顾等能力。
 * 当前提供统一页面容器、标题区与占位内容，保证路由 /review 可访问且视觉与全站一致。
 */
const ReviewPage: React.FC = () => {
  const { t } = useUiLanguage();
  // 取自系统主题主色（HEX），用户切换主色/主题时实时联动
  const { color } = useThemeColor();
  // 仅在暗色主题下展示 LightBloom 背景光晕
  const { resolvedTheme } = useTheme();
  // 首页股票搜索（受控）
  const [query, setQuery] = useState('');

  return (
    <AppPage>
      {resolvedTheme === 'dark' && (
        <LightBloom
          style={{ position: 'fixed', inset: 0, zIndex: 0 }}
          background="transparent"
          baseColor={color}
        />
      )}
      <div className="relative h-full z-10 flex min-h-screen items-center justify-center  px-4">
        <div className="w-full max-w-[640px]">
          <StockSearch
            className="mb-50"
            value={query}
            size="lg"
            onChange={setQuery}
            onSubmit={(code, name, source, metadata) => {
              // metadata.displayLabel 为"名称（规范代码）"，如"中科曙光（603019.SH）"；
              // 组件内部已用该文案兜底展示，此处仅用于外部需要时的联动。
              // TODO: 接入首页搜索提交逻辑
              console.log('submit stock:', code, name, source, metadata?.displayLabel);
            }}
          />
        </div>
      </div>
    </AppPage>
  );
};

export default ReviewPage;
