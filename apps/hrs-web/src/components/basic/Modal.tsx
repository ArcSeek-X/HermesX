/**
 * 模态框组件（Modal）
 *
 * 基于 HeroUI Modal 二次封装，支持两种模式：
 *
 * 【声明式（推荐）】isOpen / onClose 控制显隐，children 用 Header / Body / Footer 组织
 * 【复合组件】Root / Backdrop / Container / Dialog 自由组合，支持全部配置
 *
 * @example
 * ```tsx
 * // 声明式（推荐）
 * <Modal isOpen={open} onClose={() => setOpen(false)} size="md">
 *   <Modal.Header>
 *     <Modal.Heading>编辑持仓</Modal.Heading>
 *   </Modal.Header>
 *   <Modal.Body>
 *     <input ... />
 *   </Modal.Body>
 *   <Modal.Footer>
 *     <Button variant="secondary" onClick={() => setOpen(false)}>取消</Button>
 *     <Button onClick={handleSave}>保存</Button>
 *   </Modal.Footer>
 * </Modal>
 *
 * // 复合组件（完全自定义）
 * <Modal.Root>
 *   <Modal.Backdrop variant="blur">
 *     <Modal.Container size="lg">
 *       <Modal.Dialog>
 *         <Modal.Header><Modal.Heading>标题</Modal.Heading></Modal.Header>
 *         <Modal.Body>内容</Modal.Body>
 *         <Modal.Footer>
 *           <Button slot="close">确认</Button>
 *         </Modal.Footer>
 *       </Modal.Dialog>
 *     </Modal.Container>
 *   </Modal.Backdrop>
 * </Modal.Root>
 * ```
 */
import { Children, isValidElement, type ReactNode } from 'react';
import { Modal as HeroUIModal } from '@heroui/react';
import { cn } from '../../utils/cn';
import { Separator } from './Separator';

/** 尺寸 → Dialog 圆角映射 */
const SIZE_RADIUS_MAP: Record<string, string> = {
  xs: 'rounded-lg',
  sm: 'rounded-lg',
  md: 'rounded-xl',
  lg: 'rounded-xl',
  full: 'rounded-none',
  cover: 'rounded-xl',
};

/** 遮罩变体 → 渐变样式映射 */
const VARIANT_GRADIENT_MAP: Record<string, string> = {
  opaque: 'bg-linear-to-t from-black/20 via-black/10 to-transparent dark:from-zinc-800/20 dark:via-zinc-800/15',
  blur: 'bg-linear-to-t from-black/50 via-black/25 to-transparent dark:from-zinc-800/40 dark:via-zinc-800/20',
  transparent: 'bg-transparent',
};


/** 声明式 Modal 属性 */
interface HrsModalProps {
  /** 子组件内容（Header / Body / Footer） */
  children: React.ReactNode;
  /** 是否显示 */
  isOpen?: boolean;
  /** 尺寸，默认 'md' */
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'full' | 'cover';
  /** 位置，默认 'center' */
  placement?: 'auto' | 'top' | 'center' | 'bottom';
  /** 滚动行为，默认 'inside' */
  scroll?: 'inside' | 'outside';
  /** 遮罩变体，默认 'opaque' */
  variant?: 'opaque' | 'blur' | 'transparent';
  /** 点击遮罩可关闭，默认 true */
  isDismissable?: boolean;
  /** 隐藏关闭按钮，默认 false */
  hideCloseButton?: boolean;
  /** Dialog 自定义 className */
  dialogClassName?: string;
  /** Backdrop 自定义 className */
  backdropClassName?: string;
  /** Header 自定义 className */
  headerClassName?: string;
  /** Body 自定义 className */
  bodyClassName?: string;
  /** Footer 自定义 className */
  footerClassName?: string;
  /** 关闭回调 */
  onClose?: () => void;
}


/** 声明式 Modal（内部实现） */
const HrsModal: React.FC<HrsModalProps> = ({
  children,
  isOpen,
  onClose,
  size = 'md',
  placement = 'center',
  scroll = 'inside',
  variant = 'opaque',
  isDismissable = true,
  hideCloseButton = false,
  dialogClassName,
  backdropClassName,
  headerClassName,
  bodyClassName,
  footerClassName,
}) => {
  // ---- 提取 Header / Body / Footer ----
  const bodyParts: ReactNode[] = [];
  const headerParts: ReactNode[] = [];
  const footerParts: ReactNode[] = [];

  Children.forEach(children, (child: ReactNode) => {
    if (isValidElement(child) && child.type === HeroUIModal.Footer) {
      footerParts.push((child.props as { children?: ReactNode }).children);
    } else if (isValidElement(child) && child.type === HeroUIModal.Header) {
      headerParts.push((child.props as { children?: ReactNode }).children);
    } else if (isValidElement(child) && child.type === HeroUIModal.Body) {
      bodyParts.push((child.props as { children?: ReactNode }).children);
    }
  });

  const resolvedFooter = footerParts.length > 0 ? footerParts : null;

  return (
    <HeroUIModal.Root isOpen={isOpen} onOpenChange={(open) => { if (!open) onClose?.(); }}>
      <HeroUIModal.Backdrop 
        variant={variant}
        isDismissable={isDismissable} 
        className={cn('hrs-modal-backdrop', VARIANT_GRADIENT_MAP[variant], backdropClassName)}
      >
        <HeroUIModal.Container size={size} placement={placement} scroll={scroll}>
          <HeroUIModal.Dialog className={cn('hrs-modal-dialog', SIZE_RADIUS_MAP[size] ?? 'rounded-lg', dialogClassName)}>
            {/* Header + 关闭按钮 */}
            {(headerParts.length > 0 || !hideCloseButton) && (
              <HeroUIModal.Header className={cn('hrs-modal-header gap-2', headerClassName)}>
                {headerParts}
                {!hideCloseButton && <HeroUIModal.CloseTrigger />}
              </HeroUIModal.Header>
            )}

            {/* Header 与 Body 之间的分割线：default 变体 + 两端渐隐 */}
            <Separator className="my-3" gradient/>

            {/* Body */}
            <HeroUIModal.Body className={cn('hrs-modal-body', bodyClassName)}>
              {bodyParts}
            </HeroUIModal.Body>

            {/* Footer（可选） */}
            {resolvedFooter && (
              <HeroUIModal.Footer className={cn('hrs-modal-footer', footerClassName)}>
                {resolvedFooter}
              </HeroUIModal.Footer>
            )}
          </HeroUIModal.Dialog>
        </HeroUIModal.Container>
      </HeroUIModal.Backdrop>
    </HeroUIModal.Root>
  );
};

/** Modal 对外导出（Object.assign 合并声明式 + 复合组件） */
export const Modal = Object.assign(HrsModal, {
  Root: HeroUIModal.Root,
  Trigger: HeroUIModal.Trigger,
  Backdrop: HeroUIModal.Backdrop,
  Container: HeroUIModal.Container,
  Dialog: HeroUIModal.Dialog,
  Header: HeroUIModal.Header,
  Heading: HeroUIModal.Heading,
  Icon: HeroUIModal.Icon,
  Body: HeroUIModal.Body,
  Footer: HeroUIModal.Footer,
  CloseTrigger: HeroUIModal.CloseTrigger,
});
