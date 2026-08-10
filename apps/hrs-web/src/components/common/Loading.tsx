/**
 * Loading.tsx
 *
 * 作用简述：
 *   一个通用的「加载中」状态展示组件（Loading Spinner）。
 *   在异步请求、数据初始化或页面切换等需要等待时，向用户呈现一个
 *   居中的旋转加载图标 + 文案提示，缓解等待焦虑并明确告知「正在加载」。
 *   文案默认取自多语言文案 `common.loading`，也允许外部通过 `label` 覆盖。
 *
 * 使用场景：
 *   - 接口请求进行中、首屏数据初始化。
 *   - 列表 / 内容区域等待数据返回的占位提示。
 */

import React from 'react';
import { useUiLanguage } from '../../contexts/UiLanguageContext';

/**
 * 组件属性定义。
 */
interface LoadingProps {
  /** 加载提示文案（可选）；不传时回退到多语言文案 `common.loading`。 */
  label?: string;
  /** 透传到最外层容器的额外 className，用于外部覆盖 / 追加样式。 */
  className?: string;
}

/**
 * 加载中状态组件。
 * 居中渲染一个带旋转动画的环形图标与文案，封装为胶囊状的加载提示。
 */
export const Loading: React.FC<LoadingProps> = ({ label, className = '' }) => {
  const { t } = useUiLanguage();

  return (
    // 最外层容器：水平垂直居中布局，并预留 p-8 内边距；合并外部 className。
    <div className={`flex items-center justify-center p-8 ${className}`}>
      {/* 胶囊状加载提示：内联 flex、圆角、边框、卡片背景、柔和阴影 */}
      <div className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-card px-4 py-2 text-sm text-secondary-text shadow-soft-card">
        {/* 旋转加载图标：标准 Spinner SVG，h-4 w-4 尺寸，animate-spin 持续旋转，使用主题青色 */}
        <svg className="h-4 w-4 animate-spin text-cyan" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          {/* 底层整圆：低透明度，作为轨道背景 */}
          <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          {/* 顶部扇形弧：高透明度，形成旋转的「缺口」视觉效果 */}
          <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        {/* 文案：优先用外部 label，否则回退多语言的「加载中」 */}
        {label ?? t('common.loading')}
      </div>
    </div>
  );
};
