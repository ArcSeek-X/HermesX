/**
 * @file HomePage.tsx
 * @description 系统首页
 * @module pages
 */
import React, { useState } from 'react';
import { AppPage } from '@components/layout/AppPage';
import { StockSearch } from '@components/StockSearch/StockSearch';
// import UniverseBackground from '@components/universe/UniverseBackground';

/**
 * 复盘页面组件
 *
 * 复盘工作台骨架：后续在此扩展历史复盘记录、大盘回顾等能力。
 * 当前提供统一页面容器、标题区与占位内容，保证路由 /review 可访问且视觉与全站一致。
 */
const ReviewPage: React.FC = () => {
  // 首页股票搜索（受控）
  const [query, setQuery] = useState('');
  return (

    <AppPage className="flex flex-col">
      {/* 星空背景（银河系尺度梯子）：fixed + Main 的 [contain:layout_paint] → 相对主滚动容器
          固定、不随内容滚动，也不会越界盖到侧栏/页头；zIndex -1 沉在内容之下。
          默认为银心外 halo 视角 + 星系慢转，HUD（VOYAGE/ORBITS/标尺/DESTINATIONS）可直接交互。 */}
      {/* <UniverseBackground style={{ position: 'fixed', inset: 0, zIndex: 99 }} /> */}
      <div className="relative z-10 flex flex-1 items-center justify-center px-4">
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
