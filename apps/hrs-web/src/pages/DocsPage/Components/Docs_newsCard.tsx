/**
 * @fileoverview 组件文档页：NewsCard（财经快讯卡片）
 * 路由地址 /docs/component/newsCard，菜单名「快讯卡片」。
 * 用于演示 NewsCard 的时间轴布局、重要条目强调、正文两行截断与展开/收起。
 * @module pages
 */

import React, { useState } from 'react';
import { AppPage, HrsButton, NewsCard } from '../../../components';
import type { LiveNewsItem } from '../../../types/liveNews';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';

/** 当前时间（秒级时间戳），mock 数据以此推算发布时间 */
const NOW = Math.floor(Date.now() / 1000);

/** 演示用 mock 快讯数据（页面内本地构造，不请求接口） */
const MOCK_NEWS: LiveNewsItem[] = [
  {
    id: 1,
    title: '两市成交额连续三日突破万亿',
    content: '沪深两市今日成交额达 1.1 万亿元，连续第三个交易日突破万亿关口，市场交投情绪持续回暖。',
    displayTime: NOW - 60 * 10,
    score: 4,
    important: true,
    channels: ['a-stock-channel'],
    uri: 'https://wallstreetcn.com/livenews/1',
    author: '华尔街见闻',
  },
  {
    id: 2,
    title: '央行开展 5000 亿元 MLF 操作',
    content: '央行今日开展 5000 亿元中期借贷便利（MLF）操作，中标利率维持不变，流动性保持合理充裕。',
    displayTime: NOW - 60 * 25,
    score: 3,
    important: true,
    channels: ['macro-channel'],
    uri: 'https://wallstreetcn.com/livenews/2',
    author: '华尔街见闻',
  },
  {
    id: 3,
    title: '',
    content: '苹果公司宣布将于下周发布新款 MacBook Pro 系列产品，搭载新一代自研芯片。',
    displayTime: NOW - 60 * 40,
    score: 1,
    important: false,
    channels: ['us-stock-channel'],
    uri: 'https://wallstreetcn.com/livenews/3',
    author: '快讯',
  },
  {
    id: 4,
    title: '',
    content: '国际油价小幅走高，布伦特原油期货上涨 0.8%。分析人士指出，供给端扰动仍是近期油价的主要驱动因素，'
      + '而需求端复苏斜率将决定下半年油价中枢。市场关注本周即将公布的 OPEC 月度报告与 EIA 库存数据，'
      + '若库存超预期回落，油价或进一步上行；反之则可能回吐近期涨幅。',
    displayTime: NOW - 60 * 60,
    score: 1,
    important: false,
    channels: ['commodity-channel'],
    uri: 'https://wallstreetcn.com/livenews/4',
    author: '快讯',
  },
];

/**
 * 快讯卡片组件文档演示页。
 *
 * NewsCard 为单条财经快讯卡片：左时间列 | 垂直分割线（Separator secondary 变体 + 渐变）| 右标题 + 正文；
 * 重要条目时间与标题用主题危险色强调并带「重要」标签，正文默认 2 行、超出出现展开/收起按钮。
 */
export const DocsNewsCardPage: React.FC = () => {
  const { t } = useUiLanguage();

  // 「只看重要的」开关：演示 showImportant 对重要标签/强调色的控制
  const [showImportant, setShowImportant] = useState(true);

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsNewsCard.title')}</h1>
          <p className="text-xs text-muted">
            单条财经快讯卡片（NewsCard）。左时间列 + 垂直渐变分割线 + 右标题/正文；
            重要条目用主题危险色强调并带「重要」标签，正文默认 2 行截断、超出出现展开/收起按钮。
          </p>
        </header>

        {/* 1. 快讯列表（普通 + 重要混合） */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例一：快讯列表（普通 + 重要混合）</h2>
          <p className="text-xs text-muted">
            下方为页面内构造的 mock LiveNewsItem 数据；重要条目时间与标题变红并带「重要」标签，普通条目保持默认色。
          </p>
          <div className="flex flex-wrap gap-3">
            <HrsButton variant="secondary" onClick={() => setShowImportant((v) => !v)}>
              只看重要的：{showImportant ? '开' : '关'}
            </HrsButton>
          </div>
          <div className="flex max-w-3xl flex-col">
            {MOCK_NEWS.map((item, i) => (
              <NewsCard key={item.id} item={item} showImportant={showImportant} ordinal={i} />
            ))}
          </div>
        </section>

        {/* 2. 长正文展开/收起 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例二：长正文展开 / 收起</h2>
          <p className="text-xs text-muted">
            正文默认 2 行截断；超出时出现「展开」按钮，点击以网格动画平滑展开全文并切换为「收起」。
          </p>
          <div className="flex max-w-3xl flex-col">
            <NewsCard item={MOCK_NEWS[3]} showImportant={false} />
          </div>
        </section>
      </div>
    </AppPage>
  );
};

export default DocsNewsCardPage;
