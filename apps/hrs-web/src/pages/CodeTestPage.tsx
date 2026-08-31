/**
 * @fileoverview 测试页面（CodeTest）
 * 用于开发期功能验证与组件联调，路由地址 /codeTest。
 * @module pages
 */

import React from "react";
import { Fragment, useState } from 'react';
import { AppPage, InlineTipCard, Input, HrsButton, Modal, Chip, TextArea, HrsSelect, type HrsSelectOptionDef, type HrsSelectSectionDef } from '../components';
import { type ParsedApiError } from '../api/error';
import { type Key } from '@heroui/react';
import { Star, ArrowRight } from '@gravity-ui/icons';
import { showToast, type ToastPlacement, type ToastVariant } from '../components/basic/Toast';
/**
 * 测试页面组件
 * 当前为占位内容，可在开发过程中按需挂载待验证的组件与逻辑。
 */

/** 把 Toast 主题配色映射到 HrsButton 支持的 variant */
const toastVariantToButton: Record<
    ToastVariant,
    'primary' | 'secondary' | 'danger' | 'ghost'
> = {
    default: 'ghost',
    accent: 'primary',
    success: 'primary',
    warning: 'secondary',
    danger: 'danger',
};

/** HrsSelect 基础单选演示：扁平选项（含禁用子项） */
const selectMarketOptions: HrsSelectOptionDef[] = [
    { key: 'a', label: 'A 股' },
    { key: 'hk', label: '港股' },
    { key: 'us', label: '美股' },
    { key: 'tw', label: '台股', disabled: true },
];

/** HrsSelect 分组演示：数据结构与扁平选项统一走 options 入口（每个分组有 title，分组间自动插入分割线） */
const selectMarketSections: HrsSelectSectionDef[] = [
    {
        key: 'asia',
        title: '亚洲',
        options: [
            { key: 'cn', label: '上证指数' },
            { key: 'hk', label: '恒生指数' },
            { key: 'jp', label: '日经 225', disabled: true },
        ],
    },
    {
        key: 'europe',
        title: '欧洲',
        options: [
            { key: 'uk', label: '富时 100' },
            { key: 'de', label: 'DAX 30' },
        ],
    },
    {
        key: 'america',
        title: '美洲',
        options: [
            { key: 'usa', label: '标普 500' },
            { key: 'usa-tech', label: '纳斯达克 100' },
        ],
    },
];

/** HrsSelect 多选演示：扁平选项 */
const selectMultiOptions: HrsSelectOptionDef[] = [
    { key: 'macd', label: 'MACD' },
    { key: 'kdj', label: 'KDJ' },
    { key: 'rsi', label: 'RSI' },
    { key: 'boll', label: 'BOLL' },
    { key: 'ma', label: 'MA 均线' },
];

/** InlineTipCard 的 variant 枚举（组件内部类型未导出，此处按同名字面量集合声明） */
type InlineTipCardVariant = 'default' | 'accent' | 'success' | 'warning' | 'danger';

/** InlineTipCard 演示：variant 语义色 × ParsedApiError 示例内容 */
const inlineTipSamples: {
    key: string;
    variant: InlineTipCardVariant;
    label: string;
    content: ParsedApiError;
}[] = [
    {
        key: 'default',
        variant: 'default',
        label: '中性灰，不抢视觉',
        content: {
            title: '行情数据来自第三方行情源',
            message: '行情可能存在 15 分钟延迟，页面数据仅供参考，不构成投资建议。',
            rawMessage: 'quote_source=third_party, delay=15min, provider=akshare',
            category: 'unknown',
        },
    },
    {
        key: 'accent',
        variant: 'accent',
        label: '强调 / 信息',
        content: {
            title: 'Agent 模式已开启',
            message: '本次分析将启用工具调用与多轮推理，耗时通常比标准模式更长。',
            rawMessage: 'agent_mode=enabled, max_tool_rounds=8, backend=codex_app_server',
            category: 'unknown',
        },
    },
    {
        key: 'success',
        variant: 'success',
        label: '成功',
        content: {
            title: '配置已保存',
            message: '系统配置已写入并生效，无需重启服务。',
            rawMessage: 'POST /api/v1/system-config 200 OK, updated_items=12',
            status: 200,
            category: 'unknown',
        },
    },
    {
        key: 'warning',
        variant: 'warning',
        label: '警告',
        content: {
            title: '上游模型响应较慢',
            message: '当前模型连续两次响应超过 60 秒，建议切换通道或降低并发后再试。',
            rawMessage: 'upstream latency=63.4s, threshold=60s, channel=deepseek-chat',
            category: 'upstream_timeout',
        },
    },
    {
        key: 'danger',
        variant: 'danger',
        label: '危险（原 ApiErrorAlert 的红色样式）；此处 message 故意写长，用于验证 line-clamp-3 截断',
        content: {
            title: '无法连接到本地服务',
            message:
                '请确认 HermesX 后端已启动（默认监听 http://127.0.0.1:8000），且浏览器所在机器可以访问该地址；若服务部署在容器或远程主机，请检查端口映射与防火墙规则，确认无误后点击右侧「重试」再次发起请求。',
            rawMessage:
                'AxiosError: Network Error at http://127.0.0.1:8000/api/v1/watchlist (ERR_CONNECTION_REFUSED)\n  at XMLHttpRequest.handleError (xhr.js:117)\n  at dispatchEvent (event-target.js:59)',
            status: 0,
            category: 'local_connection_failed',
        },
    },
];

const CodeTestPage: React.FC = () => {
    // 三个尺寸的输入框共享同一受控值，便于对比 size 参数的视觉效果。
    const [newName] = useState('');
    const [text, setText] = useState('这是一段初始的多行文本内容，用于演示 TextArea 的受控用法。');
    const [isOpen, setIsOpen] = useState(false);
    // HrsSelect 演示：基础受控单选（共享同一状态，用于对比各尺寸）
    const [selectMarket, setSelectMarket] = useState<Key | null>('a');
    // HrsSelect 演示：分组受控单选
    const [selectIndex, setSelectIndex] = useState<Key | null>('usa');
    // HrsSelect 演示：多选（受控，Key[]）
    const [selectIndicators, setSelectIndicators] = useState<Key[]>(['macd']);
    // HrsSelect 演示：校验态（未选择时展示错误提示）
    const [selectStrategy, setSelectStrategy] = useState<Key | null>(null);
    // InlineTipCard 关闭演示：记录被 onDismiss 关掉的卡片 key
    const [dismissedTips, setDismissedTips] = useState<string[]>([]);
    // Chip 关闭演示：受控标签列表
    const [chips, setChips] = useState<string[]>([
        '科创50',
        '人工智能',
        '新能源',
        '港股通',
    ]);

    const clsickFn = () => {
        console.log('点击了')
    }



    const openModel = () => {
        setIsOpen(true)
        console.log('打开模态框')
    }



    return (
        <AppPage>
            {/* ============ InlineTipCard（内联提示卡片）组件演示 ============ */}
            <div className="flex flex-col gap-4 rounded-lg border border-border/70 bg-card/75 p-6">
                <h3 className="text-sm font-medium text-primary-text">InlineTipCard（内联提示卡片）组件演示</h3>
                <p className="text-xs text-muted">
                    内联插入页面 DOM 流的提示卡片，与 Toast（浮层、命令式）视觉同源、场景互补。
                    入参 content 为请求层解析好的 ParsedApiError；当 rawMessage 与 message 不一致时自动出现「详情」展开面板；
                    danger / warning 语义使用 role=&quot;alert&quot;，其余使用 role=&quot;status&quot;。
                </p>

                {/* 1. variant 语义色 + 关闭按钮 + 操作按钮 */}
                <div className="flex flex-col gap-2">
                    <span className="text-xs text-secondary-text">
                        1. variant 语义色（default / accent / success / warning / danger）；均带「详情」展开、onDismiss 关闭按钮与 actionLabel 操作按钮
                    </span>
                    <div className="flex flex-col gap-3">
                        {inlineTipSamples.map(({ key, variant, label, content }) =>
                            dismissedTips.includes(key) ? null : (
                                <div key={key} className="flex flex-col gap-1">
                                    <span className="text-[11px] text-muted">
                                        variant=&quot;{variant}&quot; · {label}
                                    </span>
                                    <InlineTipCard
                                        variant={variant}
                                        content={content}
                                        actionLabel="重试"
                                        onAction={() => console.log('[InlineTipCard] onAction:', key)}
                                        onDismiss={() => setDismissedTips((prev) => [...prev, key])}
                                    />
                                </div>
                            ),
                        )}
                        {dismissedTips.length > 0 ? (
                            <HrsButton
                                variant="ghost"
                                size="sm"
                                className="self-start"
                                onClick={() => setDismissedTips([])}
                            >
                                恢复已关闭的卡片（{dismissedTips.length}）
                            </HrsButton>
                        ) : null}
                    </div>
                </div>

                {/* 2. 极简用法：无详情、无按钮 */}
                <div className="flex flex-col gap-2 border-t border-border/60 pt-4">
                    <span className="text-xs text-secondary-text">
                        2. 极简用法：rawMessage 与 message 一致时不渲染「详情」；不传 actionLabel / onDismiss 则不显示按钮
                    </span>
                    <InlineTipCard
                        variant="accent"
                        content={{
                            title: '已开启自动刷新',
                            message: '自选股行情每 30 秒自动刷新一次，可在偏好设置中关闭。',
                            rawMessage: '自选股行情每 30 秒自动刷新一次，可在偏好设置中关闭。',
                            category: 'unknown',
                        }}
                    />
                </div>
            </div>

            {/* ============ HrsSelect 下拉选择器组件演示 ============ */}
            <div className="flex flex-col gap-4 rounded-lg border border-border/70 bg-card/75 p-6">
                <h3 className="text-sm font-medium text-primary-text">HrsSelect（下拉选择器）组件演示</h3>
                <p className="text-xs text-muted">
                    基于 HeroUI Select 封装，统一 options 数据入口、数据结构驱动渲染：扁平项与分组项可任意组合，
                    含 options 数组的项自动识别为分组（渲染 title 分组标题，分组间自动插入分割线）；
                    子项可通过 disabled 字段禁用（无法被选中）。
                    基础入参遵循 HeroUI 规格（value / onChange / selectionMode / isDisabled / isInvalid 等）。
                </p>

                {/* 1. 基础受控单选：尺寸对比 + disabled 子项 */}
                <div className="flex flex-col gap-3">
                    <span className="text-xs text-secondary-text">
                        基础受控单选（size xs / sm / md / lg 共享同一状态；「台股」为 disabled 子项，无法被选中）
                    </span>
                    <div className="flex flex-wrap items-start gap-4">
                        {(['xs', 'sm', 'md', 'lg'] as const).map((size) => (
                            <div key={size} className="w-56">
                                <HrsSelect
                                    size={size}
                                    label={`市场（size=${size}）`}
                                    placeholder="请选择市场"
                                    options={selectMarketOptions}
                                    value={selectMarket}
                                    onChange={(value) => setSelectMarket(value as Key | null)}
                                />
                            </div>
                        ))}
                    </div>
                </div>

                {/* 2. 分组单选：统一 options 入口，含 options 数组的项动态识别为分组 */}
                <div className="flex flex-col gap-2">
                    <span className="text-xs text-secondary-text">
                        分组单选（同样通过 options 传入，数据结构含 options 数组即识别为分组：
                        分组标题 title、分组间自动分隔、「日经 225」为 disabled）
                    </span>
                    <div className="w-72">
                        <HrsSelect
                            label="指数（按地区分组）"
                            placeholder="请选择指数"
                            options={selectMarketSections}
                            value={selectIndex}
                            onChange={(value) => setSelectIndex(value as Key | null)}
                        />
                    </div>
                </div>

                {/* 3. 多选：selectionMode="multiple"（受控 Key[]） + description 辅助说明 */}
                <div className="flex flex-col gap-2">
                    <span className="text-xs text-secondary-text">
                        多选（selectionMode=&quot;multiple&quot;，当前选中：{selectIndicators.length > 0 ? selectIndicators.join(' / ') : '无'}；
                        description 为触发器下方的辅助说明文本）
                    </span>
                    <div className="w-72">
                        <HrsSelect
                            label="技术指标"
                            placeholder="请选择技术指标"
                            description="可组合多个指标进行叠加分析"
                            selectionMode="multiple"
                            options={selectMultiOptions}
                            value={selectIndicators}
                            onChange={(value) => setSelectIndicators(value as Key[])}
                        />
                    </div>
                </div>

                {/* 4. 校验态（errorMessage 优先于 description）+ 整组件禁用 */}
                <div className="flex flex-wrap items-start gap-4">
                    <div className="w-72">
                        <HrsSelect
                            label="策略（isInvalid 校验态）"
                            placeholder="请选择策略"
                            isRequired
                            isInvalid={selectStrategy === null}
                            description="未选择时展示错误提示，选择后切换为本说明"
                            errorMessage={selectStrategy === null ? '请选择一个策略' : undefined}
                            options={[
                                { key: 'trend', label: '趋势跟踪' },
                                { key: 'mean-revert', label: '均值回归' },
                            ]}
                            value={selectStrategy}
                            onChange={(value) => setSelectStrategy(value as Key | null)}
                        />
                    </div>
                    <div className="w-72">
                        <HrsSelect
                            label="禁用态（isDisabled）"
                            placeholder="请选择"
                            isDisabled
                            options={selectMultiOptions}
                            value="ma"
                        />
                    </div>
                </div>
            </div>

            {/* ============ TextArea 多行文本输入组件演示 ============ */}
            <div className="flex flex-col gap-4 rounded-lg border border-border/70 bg-card/75 p-6">
                <h3 className="text-sm font-medium text-primary-text">TextArea（多行文本输入）组件演示</h3>
                <p className="text-xs text-muted">
                    基于 HeroUI TextArea 封装，支持 xs/sm/md/lg 四档尺寸与 primary/secondary 两种变体，
                    下方演示受控用法（共享同一状态）及不同尺寸、变体的视觉效果。
                </p>

                {/* 受控 + 不同尺寸 */}
                <div className="flex flex-col gap-3">
                    <div className="flex flex-col gap-1">
                        <span className="text-xs text-secondary-text">size=&quot;xs&quot;（受控，当前 {text.length} 字）</span>
                        <TextArea size="xs" value={text} onChange={(e) => setText(e.target.value)} placeholder="超紧凑尺寸" />
                    </div>
                    <div className="flex flex-col gap-1">
                        <span className="text-xs text-secondary-text">size=&quot;sm&quot;</span>
                        <TextArea size="sm" value={text} onChange={(e) => setText(e.target.value)} placeholder="默认尺寸" />
                    </div>
                    <div className="flex flex-col gap-1">
                        <span className="text-xs text-secondary-text">size=&quot;md&quot;</span>
                        <TextArea size="md" value={text} onChange={(e) => setText(e.target.value)} placeholder="中等尺寸" />
                    </div>
                    <div className="flex flex-col gap-1">
                        <span className="text-xs text-secondary-text">size=&quot;lg&quot;</span>
                        <TextArea size="lg" value={text} onChange={(e) => setText(e.target.value)} placeholder="大尺寸" />
                    </div>
                </div>

                {/* 变体 + 禁用 / 只读 */}
                <div className="flex flex-col gap-3">
                    <div className="flex flex-col gap-1">
                        <span className="text-xs text-secondary-text">variant=&quot;secondary&quot;（无阴影，适配 Surface）</span>
                        <TextArea variant="secondary" value={text} onChange={(e) => setText(e.target.value)} placeholder="Surface 内使用" />
                    </div>
                    <div className="flex flex-col gap-1">
                        <span className="text-xs text-secondary-text">disabled（禁用）</span>
                        <TextArea disabled value={text} placeholder="禁用状态" />
                    </div>
                    <div className="flex flex-col gap-1">
                        <span className="text-xs text-secondary-text">只读展示（仅传 value 无 onChange，自动补 readOnly）</span>
                        <TextArea value={text} placeholder="只读状态" />
                    </div>
                </div>
            </div>


            {/* ============ 错误 Toast（浮层）组件演示 ============ */}
            <div className="flex flex-col gap-4 rounded-lg border border-border/70 bg-card/75 p-6">
                <h3 className="text-sm font-medium text-primary-text">Toast（浮层）组件演示</h3>
                <p className="text-xs text-muted">
                    命令式触发，应用根（App.tsx）已挂载一次 {'<Toast />'} 宿主。下方按「主题配色 × 弹出位置」矩阵演示：每行一种配色，点击行内不同方位按钮即可在视口对应角落弹出对应风格的浮层，默认 6s 自动消失。
                </p>

                {/* 主题配色 × 位置 矩阵 */}
                <div className="flex flex-col gap-3">
                    {(
                        [
                            { variant: 'default' as ToastVariant, label: 'Default' },
                            { variant: 'accent' as ToastVariant, label: 'Accent' },
                            { variant: 'success' as ToastVariant, label: 'Success' },
                            { variant: 'warning' as ToastVariant, label: 'Warning' },
                            { variant: 'danger' as ToastVariant, label: 'Danger' },
                        ]
                    ).map(({ variant, label }) => (
                        <div key={variant} className="flex flex-wrap items-center gap-2">
                            <span className="w-16 shrink-0 text-xs font-medium text-muted">{label}</span>
                            {(['top start', 'top', 'top end', 'bottom start', 'bottom', 'bottom end'] as ToastPlacement[]).map((placement) => (
                                <HrsButton
                                    key={placement}
                                    variant={toastVariantToButton[variant]}
                                    size="sm"
                                    onClick={() =>
                                        showToast({
                                            title: `${label} 提示（${placement}）`,
                                            description:
                                                '这是一段用户友好的描述文案，用于演示 Toast 浮层在不同主题配色与弹出位置下的视觉效果。',
                                            rawMessage:
                                                'Raw server error: 500 Internal Server Error at /api/v1/watchlist，详细堆栈信息略。',
                                            variant,
                                            placement,
                                        })
                                    }
                                >
                                    {placement}
                                </HrsButton>
                            ))}
                        </div>
                    ))}
                </div>

                {/* 便捷方法：info / success / warning / danger（variant 预设） */}
                <div className="mt-2 flex flex-col gap-2 border-t border-border/60 pt-4">
                    <span className="text-xs font-medium text-muted">便捷方法（showToast.{'{'}info | success | warning | danger{'}'}，variant 预设）</span>
                    <div className="flex flex-wrap items-center gap-2">
                        {(
                            [
                                { method: 'info' as const, buttonVariant: 'primary' as const, title: 'info（accent）', description: '信息/强调风格，等价 variant: accent。' },
                                { method: 'success' as const, buttonVariant: 'success' as const, title: 'success', description: '成功风格，等价 variant: success。' },
                                { method: 'warning' as const, buttonVariant: 'warning' as const, title: 'warning', description: '警告风格，等价 variant: warning。' },
                                { method: 'danger' as const, buttonVariant: 'danger' as const, title: 'danger', description: '错误风格，等价 variant: danger。' },
                            ]
                        ).map(({ method, buttonVariant, title, description }) => (
                            <HrsButton
                                key={method}
                                variant={buttonVariant}
                                size="sm"
                                onClick={() =>
                                    showToast[method]({
                                        title: `showToast.${method} · ${title}`,
                                        description,
                                        placement: 'top start',
                                    })
                                }
                            >
                                showToast.{method}
                            </HrsButton>
                        ))}
                    </div>
                </div>
            </div>


            {/* ============ Chip 组件演示 ============ */}
            <div className="flex flex-col gap-5 rounded-lg border border-border/70 bg-card/75 p-6">
                <h3 className="text-sm font-medium text-primary-text">Chip 组件演示</h3>

                {/* 1. color × variant 矩阵 */}
                <div className="flex flex-col gap-2">
                    <span className="text-xs text-muted">color × variant 矩阵</span>
                    <div className="flex flex-col gap-2">
                        {/* 列头：color 名称 */}
                        <div className="flex flex-wrap items-center gap-2 border-b border-border/40 pb-1">
                            <span className="w-20 shrink-0 text-[11px] font-medium text-muted">variant \ color</span>
                            {(['default', 'accent', 'success', 'warning', 'danger', 'blue', 'purple', 'indigo'] as const).map((color) => (
                                <span key={color} className="w-[3.25rem] shrink-0 text-center text-[11px] font-medium text-muted">
                                    {color}
                                </span>
                            ))}
                        </div>
                        {(['primary', 'secondary', 'tertiary', 'soft'] as const).map((variant) => (
                            <div key={variant} className="flex flex-wrap items-center gap-2">
                                <span className="w-20 shrink-0 text-[11px] text-muted">{variant}</span>
                                {(['default', 'accent', 'success', 'warning', 'danger', 'blue', 'purple', 'indigo'] as const).map((color) => (
                                    <Chip key={color} variant={variant} color={color} className="w-[3.25rem] justify-center">
                                        {color}
                                    </Chip>
                                ))}
                            </div>
                        ))}
                    </div>
                </div>

                {/* 2. 尺寸 */}
                <div className="flex flex-col gap-2">
                    <span className="text-xs text-muted">size</span>
                    <div className="flex flex-wrap items-center gap-2">
                        <Chip size="xs" color="accent">xs尺寸</Chip>
                        <Chip size="sm" color="accent">sm尺寸</Chip>
                        <Chip size="md" color="accent">md尺寸</Chip>
                        <Chip size="lg" color="accent">lg尺寸</Chip>
                        <Chip size="xl" color="accent">xl尺寸</Chip>
                    </div>
                </div>

                {/* 3. 圆角 */}
                <div className="flex flex-col gap-2">
                    <span className="text-xs text-muted">radius</span>
                    <div className="flex flex-wrap items-center gap-2">
                        <Chip radius="full" color="success">full</Chip>
                        <Chip radius="sm" color="success">sm</Chip>
                        <Chip radius="md" color="success">md</Chip>
                        <Chip radius="lg" color="success">lg</Chip>
                    </div>
                </div>

                {/* 4. children 内容（图标、文字由调用方组合） */}
                <div className="flex flex-col gap-2">
                    <span className="text-xs text-muted">children（图标 + 文字自组合）</span>
                    <div className="flex flex-wrap items-center gap-2">
                        <Chip color="accent">
                            <Star className="h-3.5 w-3.5" />
                            <span>带前缀图标</span>
                        </Chip>
                        <Chip color="warning">
                            <span>带后缀图标</span>
                            <ArrowRight className="h-3.5 w-3.5" />
                        </Chip>
                    </div>
                </div>

                {/* 5. 禁用态 */}
                <div className="flex flex-col gap-2">
                    <span className="text-xs text-muted">isDisabled</span>
                    <div className="flex flex-wrap items-center gap-2">
                        <Chip isDisabled color="danger" variant="soft">禁用标签</Chip>
                    </div>
                </div>

                {/* 6. 关闭按钮（受控交互） */}
                <div className="flex flex-col gap-2">
                    <span className="text-xs text-muted">onClose（点击 × 移除，受控）</span>
                    <div className="flex flex-wrap items-center gap-2">
                        {chips.length === 0 && <span className="text-xs text-muted">已全部关闭</span>}
                        {chips.map((c) => (
                            <Chip
                                key={c}
                                color="accent"
                                variant="soft"
                                onClose={() => setChips((prev) => prev.filter((x) => x !== c))}
                            >
                                {c}
                            </Chip>
                        ))}
                    </div>
                </div>
            </div>
            <div className="flex flex-col gap-4 rounded-lg border border-border/70 bg-card/75 p-6">
                <Input
                    aria-label="Search projects"
                    className="w-64 rounded-xl border border-border/80 bg-default text-foreground placeholder:text-muted"
                    placeholder="Search projects..."
                />
            </div>

            <div className="flex flex-col gap-4 rounded-lg border border-border/70 bg-card/75 p-6">
                <HrsButton variant="primary" size="sm" onClick={openModel}>
                    Open Modal
                </HrsButton>

                <Modal
                    isOpen={isOpen}
                    onClose={() => {
                        console.log(555555555555)
                        setIsOpen(false);
                    }}
                >
                    <Modal.Header>
                        <Modal.Heading>Modal Title</Modal.Heading>
                        <p className="mt-1 text-sm leading-5 text-muted">这是一段描述文案，用于补充说明弹窗的用途或操作内容。</p>
                    </Modal.Header>
                    <Modal.Body>
                        <p>Modal content</p>
                        <p>Modal content</p>
                        <p>Modal content</p>
                        <p>Modal content</p>
                        <p>Modal content</p>
                        <p>Modal content</p>
                        <p>Modal content</p>
                    </Modal.Body>
                    <Modal.Footer>
                        <HrsButton variant="secondary" onClick={() => setIsOpen(false)}>
                            取消
                        </HrsButton>
                        <HrsButton variant="primary" onClick={() => setIsOpen(false)}>
                            确认
                        </HrsButton>
                    </Modal.Footer>
                </Modal>




            </div>
            <div className="flex flex-col gap-4 rounded-lg border border-border/70 bg-card/75 p-6">
                <Input
                    className="w-100"
                    placeholder="新分组名称（xs）"
                    size="xs"
                    value={newName}

                />
                <Input
                    className="w-200"
                    placeholder="新分组名称（sm）"
                    size="sm"
                    value={newName}
                />
                <Input
                    className="w-full"
                    placeholder="新分组名称（md）"
                    size="md"
                    value={newName}

                />
                <Input
                    placeholder="新分组名称（lg）"
                    size="lg"
                    value={newName}
                />
            </div>

            <div className="rounded-lg border border-border/70 bg-card/75 p-6">
                <p className="mb-4 text-xs font-medium text-muted">按钮 Variant × Size 矩阵（行=variant，列=size；单元格内文字为该 size 缩写）</p>
                <div className="grid grid-cols-[minmax(7rem,auto)_repeat(5,minmax(0,1fr))] gap-x-3 gap-y-2 items-center">
                    <div />
                    {(['xs', 'sm', 'md', 'lg', 'xl'] as const).map((size) => (
                        <div key={size} className="text-center text-xs font-semibold text-muted-text">
                            {size}
                        </div>
                    ))}
                    {(
                        [
                            'secondary', 'outline', 'ghost', 'primary', 'primary-soft',
                            'success', 'success-soft', 'warning', 'warning-soft', 'danger', 'danger-soft',
                            // 'settings-primary', 'settings-secondary',
                            // 'action-primary', 'action-secondary', 'home-action-ai', 'home-action-report',
                        ] as const
                    ).map((variant) => (
                        <Fragment key={variant}>
                            <div className="text-xs font-medium text-foreground">{variant}</div>
                            {(['xs', 'sm', 'md', 'lg', 'xl'] as const).map((size) => (
                                <div key={size} className="flex justify-center">
                                    <HrsButton
                                        variant={variant}
                                        size={size}
                                        onClick={variant === 'primary' ? clsickFn : undefined}
                                    >
                                        {size}
                                    </HrsButton>
                                </div>
                            ))}
                        </Fragment>
                    ))}
                </div>
            </div>



        </AppPage >
    );
};

export default CodeTestPage;
