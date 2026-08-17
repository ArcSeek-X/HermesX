import type { CSSProperties, ReactNode } from 'react';
import { motion } from 'motion/react';
import { cn } from '../../../utils/cn';

/** Card 通用卡片入参 */
export type AnimCardProps = {
  /** 网格序号，用于入场动画错位延迟（从 0 起算） */
  ordinal?: number;
  /** 卡片主体内容插槽 */
  children?: ReactNode;
  /** 附加到卡片根元素的 class */
  className?: string;
  /** 卡片视觉风格：default 默认 / gradient 渐变边框 */
  variant?: 'default' | 'gradient';
  /** 渐变边框角度（度），仅 gradient 模式生效，默认 135（左上角对角线） */
  gradBorderAngle?: number;
  /** 渐变背景（左上角淡蓝色径向渐变 + 顶部白色线性高光），默认关闭 */
  gradientBackground?: boolean;
};

const baseStyle = 'relative flex overflow-hidden rounded-lg bg-card border border-subtle min-h-[110px]';

// 左上角主题色渐变背景（由 gradientBackground 参数控制，默认关闭；颜色随 --primary 同步换肤）
const gradientBackgroundStyle =
  "before:content-[''] before:absolute before:inset-0 before:z-0 before:rounded-[inherit] before:pointer-events-none before:bg-[linear-gradient(180deg,rgba(255,255,255,0.05),transparent_44%),radial-gradient(circle_at_top_right,hsl(var(--primary)/0.06),transparent_50%)]";


// 视觉风格对应的 CSS 类名（default 单层卡片；gradient 渐变边框衬底，需搭配 gradient-border-card-inner）
const variantStyles = {
  default:'',
  gradient: 'gradient-border-card',
} as const;

export default function AnimCard({
  ordinal = 0,
  className,
  variant = 'default',
  gradBorderAngle = 135,
  gradientBackground = false,
  children,
}: AnimCardProps) {

  // 渐变模式：外层渐变衬底 + 内层底色盖板，形成渐变描边（参考 basic/Card 双层写法）
  if (variant === 'gradient') {
    return (
      <motion.div
        className={cn('hrs-animCard', variantStyles.gradient, className)}
        style={{ '--gradient-angle': `${gradBorderAngle}deg` } as CSSProperties}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut', delay: ordinal * 0.05 }}
      >
        <div className="gradient-border-card-inner">{children}</div>
      </motion.div>
    );
  }

  // 默认模式：单层卡片
  return (
    <motion.div
      className={cn(
        'hrs-animCard',
        baseStyle,
        variantStyles.default,
        gradientBackground && gradientBackgroundStyle,
        className,
      )}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut', delay: ordinal * 0.05 }}
    >
      {/*
        开启渐变背景时：::before 伪元素（absolute + z-0）会盖住无定位内容，
        需将内容提升到 z-10 之上，flex-1/min-w-0 保证其在 flex 容器内铺满。
      */}
      {gradientBackground ? (
        <div className="relative z-10 flex-1 min-w-0">{children}</div>
      ) : (
        children
      )}
    </motion.div>
  );
}
