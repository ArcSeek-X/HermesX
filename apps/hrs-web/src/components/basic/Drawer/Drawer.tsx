/**
 * 侧滑抽屉组件（HrsDrawer）
 * ------------------------------------------------------------
 * 文件作用：
 *   基于 HeroUI Drawer 二次封装的侧滑弹窗，用于详情面板、筛选面板、表单等
 *   需要临时占用屏幕一侧 / 一端、但不脱离当前页面的场景。
 *
 * 设计要点：
 *   - 底座为 HeroUI 的 Drawer（@heroui/react），完整保留其原生能力：
 *     焦点陷阱、Esc 关闭、滚动锁定、拖拽关闭（drag-to-dismiss）、
 *     进入 / 退出动画、react-aria 无障碍语义；
 *   - HeroUI Drawer 原生没有 size 概念（宽高由 CSS 固定），此处补齐 xs / sm /
 *     md / lg / xl / xxl / full 七档，并且只控制「贴边轴」：左右方向控宽度、
 *     上下方向控高度；
 *     宽高均做响应式降级——窄视口下宽度不再按 vw 百分比截断（那样各档会被压成
 *     同一个值、失去区分度），改为铺满可用区域；矮视口下高度保留 dvh 比例但兜
 *     一个最小可用高度（详见 HORIZONTAL_SIZE_MAP / VERTICAL_SIZE_MAP 注释）；
 *   - 遮罩沿用项目 Modal 的渐变叠加方案，与站内弹层视觉保持一致；
 *   - 所有插槽样式通过 className 暴露，外部传入的类名永远最后合并，可全局覆写。
 *
 * 使用方式（两种）：
 *
 * 【声明式（推荐）】isOpen / onClose 控制显隐，children 用 Header / Body / Footer 组织
 * ```tsx
 * <HrsDrawer isOpen={open} onClose={() => setOpen(false)} title="板块详情" size="lg">
 *   <HrsDrawer.Body>...任意内容...</HrsDrawer.Body>
 *   <HrsDrawer.Footer>
 *     <Button variant="ghost" onClick={() => setOpen(false)}>取消</Button>
 *     <Button onClick={handleSave}>保存</Button>
 *   </HrsDrawer.Footer>
 * </HrsDrawer>
 * ```
 *
 * 【复合组件】需要完全自定义结构（自定义 Trigger、自定义 Dialog 内容等）时，
 * 直接使用 HrsDrawer.Root / Trigger / Backdrop / Content / Dialog 等原生插槽。
 * ```tsx
 * <HrsDrawer.Root>
 *   <HrsDrawer.Trigger><Button>打开</Button></HrsDrawer.Trigger>
 *   <HrsDrawer.Backdrop variant="blur">
 *     <HrsDrawer.Content placement="bottom">
 *       <HrsDrawer.Dialog>
 *         <HrsDrawer.Handle />
 *         <HrsDrawer.CloseTrigger />
 *         <HrsDrawer.Header><HrsDrawer.Heading>标题</HrsDrawer.Heading></HrsDrawer.Header>
 *         <HrsDrawer.Body>内容</HrsDrawer.Body>
 *       </HrsDrawer.Dialog>
 *     </HrsDrawer.Content>
 *   </HrsDrawer.Backdrop>
 * </HrsDrawer.Root>
 * ```
 * ------------------------------------------------------------
 * @author Lensgcx (GaoCangxiong)
 */
import { Children, isValidElement, type ComponentProps, type ReactNode } from 'react';
import { Drawer as HeroUIDrawer } from '@heroui/react';
import { cn } from '../../../utils/cn';
import { Separator } from '../Separator';

/** 滑出方向（对齐 HeroUI Drawer.Content 的 placement 规格） */
export type HrsDrawerPlacement = 'top' | 'bottom' | 'left' | 'right';

/** 遮罩变体（对齐 HeroUI Drawer.Backdrop 的 variant 规格） */
export type HrsDrawerVariant = 'opaque' | 'blur' | 'transparent';

/** 尺寸档位：左右方向控宽度，上下方向控最大高度 */
export type HrsDrawerSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | 'xxl' | 'full';

/**
 * 面板宽度上限：容器宽度（等于视口宽）减去一段固定留白。
 * 用固定留白而非 vw 百分比，保证任意分辨率下遮罩都留有可点击区域
 * （用于「点击遮罩关闭」），也不会出现「差一点点满屏」的中间态。
 */
const MAX_PANEL_WIDTH = 'max-w-[calc(100%_-_3rem)]';

/**
 * 左右方向（left / right）的宽度档位。
 *
 * 宽度是对视口最敏感的维度：一旦视口放不下该档的设计宽度，若按 vw 百分比
 * 截断（如 HeroUI 默认的 max-w-[85vw]），sm / md / lg / xl 会被压到同一个
 * 值，档位彻底失去区分度。因此改为「阈值 + 降档」策略：
 *   - 小于 Tailwind `sm`(640px)：铺满可用宽度，即移动端侧滑面板的通用形态，
 *     不再用 vw 百分比去凑宽度；
 *   - ≥ `sm`(640px)：使用紧凑宽度；≥ `md`(768px)：使用标准宽度。
 * 各档统一受 MAX_PANEL_WIDTH 兜底，避免极端窄窗口溢出。
 */
const HORIZONTAL_SIZE_MAP: Record<HrsDrawerSize, string> = {
    xs: `w-full ${MAX_PANEL_WIDTH} sm:w-56 md:w-64`,
    sm: `w-full ${MAX_PANEL_WIDTH} sm:w-64 md:w-72`,
    md: `w-full ${MAX_PANEL_WIDTH} sm:w-72 md:w-96`,
    lg: `w-full ${MAX_PANEL_WIDTH} sm:w-80 md:w-[28rem]`,
    xl: `w-full ${MAX_PANEL_WIDTH} sm:w-96 md:w-[36rem]`,
    xxl: `w-full ${MAX_PANEL_WIDTH} sm:w-[28rem] md:w-[48rem]`,
    full: 'w-full max-w-full',
};

/**
 * 上下方向（top / bottom）的高度档位。
 *
 * 高度敏感度低于宽度：抽屉高度由内容驱动，dvh 只是上限，即便被压缩也不会像
 * 宽度那样「吞掉整个可用区域」，所以这里仍按 dvh 比例分档，不做铺满降级。
 * 唯一例外是极矮视口（如横屏手机），纯比例会被压到几乎不可用，因此用
 * `min(100dvh, max(最小可用高, Xdvh))` 收口：
 *   - 常规视口：等价于 `Xdvh`，行为与纯比例一致；
 *   - 矮视口：退化为最小可用高度，且始终不超过一屏。
 */
const VERTICAL_SIZE_MAP: Record<HrsDrawerSize, string> = {
    xs: 'max-h-[min(100dvh,max(10rem,25dvh))]',
    sm: 'max-h-[min(100dvh,max(14rem,35dvh))]',
    md: 'max-h-[min(100dvh,max(18rem,50dvh))]',
    lg: 'max-h-[min(100dvh,max(24rem,70dvh))]',
    xl: 'max-h-[min(100dvh,max(30rem,85dvh))]',
    xxl: 'max-h-[min(100dvh,max(36rem,95dvh))]',
    full: 'max-h-dvh',
};

/** 是否为上下方向（决定 size 走宽度档还是高度档） */
const isVerticalPlacement = (placement: HrsDrawerPlacement): boolean =>
    placement === 'top' || placement === 'bottom';

/** 遮罩变体 → 渐变叠加样式映射（与项目 Modal 保持一致） */
const VARIANT_GRADIENT_MAP: Record<HrsDrawerVariant, string> = {
    opaque: 'bg-linear-to-t from-black/20 via-black/10 to-transparent dark:from-zinc-800/20 dark:via-zinc-800/15',
    blur: 'bg-linear-to-t from-black/50 via-black/25 to-transparent dark:from-zinc-800/40 dark:via-zinc-800/20',
    transparent: 'bg-transparent',
};

/** 声明式抽屉属性：继承 HeroUI Drawer.Root 全部原生类型 + 项目增量字段 */
export type HrsDrawerProps = ComponentProps<typeof HeroUIDrawer> & {
    /** 滑出方向，默认 'right' */
    placement?: HrsDrawerPlacement;
    /** 尺寸档位，默认 'md'（左右方向控宽度，上下方向控高度；xs ~ xxl 由小到大） */
    size?: HrsDrawerSize;
    /** 遮罩变体，默认 'opaque' */
    variant?: HrsDrawerVariant;
    /** 点击遮罩 / 拖拽可关闭，默认 true */
    isDismissable?: boolean;
    /** 禁用 Esc 关闭，默认 false */
    isKeyboardDismissDisabled?: boolean;
    /** 隐藏右上角关闭按钮，默认 false */
    hideCloseButton?: boolean;
    /** 显示顶部拖拽手柄（Drawer.Handle），默认 false */
    showHandle?: boolean;
    /** 快捷标题；与 children 中的 Header 可共存，title 渲染在最前 */
    title?: ReactNode;
    /** 快捷底部内容；与 children 中的 Footer 可共存 */
    footer?: ReactNode;
    /** 关闭回调（遮罩点击、Esc、关闭按钮、拖拽关闭均会触发） */
    onClose?: () => void;
    /** Dialog 面板自定义 className */
    dialogClassName?: string;
    /** Backdrop 遮罩自定义 className */
    backdropClassName?: string;
    /** Content 定位容器自定义 className */
    contentClassName?: string;
    /** Header 自定义 className */
    headerClassName?: string;
    /** Body 自定义 className */
    bodyClassName?: string;
    /** Footer 自定义 className */
    footerClassName?: string;
};

/** 声明式抽屉（内部实现） */
const HrsDrawerRoot = ({
    children,
    isOpen,
    defaultOpen,
    onOpenChange,
    onClose,
    placement = 'right',
    size = 'md',
    variant = 'opaque',
    isDismissable = true,
    isKeyboardDismissDisabled,
    hideCloseButton = false,
    showHandle = false,
    title,
    footer,
    dialogClassName,
    backdropClassName,
    contentClassName,
    headerClassName,
    bodyClassName,
    footerClassName,
    ...props
}: HrsDrawerProps) => {
    // 1) 从 children 中分拣 Header / Body / Footer，其余节点兜底进 Body
    const headerParts: ReactNode[] = [];
    const bodyParts: ReactNode[] = [];
    const footerParts: ReactNode[] = [];

    Children.forEach(children, (child: ReactNode) => {
        if (isValidElement(child) && child.type === HeroUIDrawer.Footer) {
            footerParts.push((child.props as { children?: ReactNode }).children);
        } else if (isValidElement(child) && child.type === HeroUIDrawer.Header) {
            headerParts.push((child.props as { children?: ReactNode }).children);
        } else if (isValidElement(child) && child.type === HeroUIDrawer.Body) {
            bodyParts.push((child.props as { children?: ReactNode }).children);
        } else {
            bodyParts.push(child);
        }
    });

    // 2) 区域存在性：有标题 / 有 Header 内容 / 需要关闭按钮时都算有 Header
    const hasHeader = !!title || headerParts.length > 0 || !hideCloseButton;
    const hasFooter = !!footer || footerParts.length > 0;

    // 3) 尺寸：面板只在一个轴向受控——左右方向控宽度，上下方向控高度（另一轴交给 HeroUI 默认）
    const sizeClass = isVerticalPlacement(placement)
        ? VERTICAL_SIZE_MAP[size]
        : HORIZONTAL_SIZE_MAP[size];

    return (
        <HeroUIDrawer.Root
            {...props}
            isOpen={isOpen}
            defaultOpen={defaultOpen}
            onOpenChange={(open) => {
                onOpenChange?.(open);
                if (!open) onClose?.();
            }}
        >
            <HeroUIDrawer.Backdrop
                variant={variant}
                isDismissable={isDismissable}
                isKeyboardDismissDisabled={isKeyboardDismissDisabled}
                className={cn('hrs-drawer-backdrop', VARIANT_GRADIENT_MAP[variant], backdropClassName)}
            >
                <HeroUIDrawer.Content
                    placement={placement}
                    className={cn('hrs-drawer-content', contentClassName)}
                >
                    <HeroUIDrawer.Dialog className={cn('hrs-drawer-dialog', sizeClass, dialogClassName)}>
                        {showHandle && <HeroUIDrawer.Handle />}

                        {/* Header + 关闭按钮：关闭按钮为绝对定位，故给标题区留出右侧安全距离 */}
                        {hasHeader && (
                            <HeroUIDrawer.Header
                                className={cn('hrs-drawer-header', !hideCloseButton && 'pe-8', headerClassName)}
                            >
                                {title && <HeroUIDrawer.Heading className='xxxxxxxx'>{title}</HeroUIDrawer.Heading>}
                                {headerParts}
                                {!hideCloseButton && <HeroUIDrawer.CloseTrigger />}
                            </HeroUIDrawer.Header>
                        )}

                        {/* Header 与 Body 之间的分割线：default 变体 + 两端渐隐 */}
                        {hasHeader && <Separator className="my-3" gradient />}

                        <HeroUIDrawer.Body className={cn('hrs-drawer-body', bodyClassName)}>
                            {bodyParts}
                        </HeroUIDrawer.Body>

                        {/* Body 与 Footer 之间的分割线：与 Header 下方的分割线对称 */}
                        {hasFooter && <Separator className="my-3" gradient />}
                        {hasFooter && (
                            <HeroUIDrawer.Footer className={cn('hrs-drawer-footer', footerClassName)}>
                                {footer}
                                {footerParts}
                            </HeroUIDrawer.Footer>
                        )}
                    </HeroUIDrawer.Dialog>
                </HeroUIDrawer.Content>
            </HeroUIDrawer.Backdrop>
        </HeroUIDrawer.Root>
    );
};

/** 对外导出：Object.assign 合并「声明式用法」与「复合组件插槽」 */
export const HrsDrawer = Object.assign(HrsDrawerRoot, {
    Root: HeroUIDrawer.Root,
    Trigger: HeroUIDrawer.Trigger,
    Backdrop: HeroUIDrawer.Backdrop,
    Content: HeroUIDrawer.Content,
    Dialog: HeroUIDrawer.Dialog,
    Header: HeroUIDrawer.Header,
    Heading: HeroUIDrawer.Heading,
    Body: HeroUIDrawer.Body,
    Footer: HeroUIDrawer.Footer,
    Handle: HeroUIDrawer.Handle,
    CloseTrigger: HeroUIDrawer.CloseTrigger,
});
