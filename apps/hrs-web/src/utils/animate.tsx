import type { ReactNode } from 'react';
import { motion, AnimatePresence } from 'motion/react';

/**
 * 数据更新时的值淡入动画组件
 *
 * 用于占位值（如 '--'）被真实数据替换时的自然过渡：值变化时旧内容淡出、
 * 新内容淡入并带轻微上移，避免直接替换的生硬感。
 *
 * - `valueKey`：值的唯一标识（用展示文本即可），变化时触发切换动画
 * - `initial={false}`：首屏挂载不触发该动画，避免与卡片整体入场动画叠加
 * - `mode="wait"`：旧值先淡出、新值再淡入，过渡更柔和
 *
 * 注意：`valueKey` 必须是简单字符串（不要用 React 元素，否则 JSON.stringify
 * 可能引发循环引用崩溃）。复合/JSX 值请由调用方用数据字段拼出稳定标识传入。
 */
export function AnimatedValue({ valueKey, children }: { valueKey: string; children: ReactNode }) {
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.span
        key={valueKey}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={{ duration: 0.35, ease: 'easeOut' }}
      >
        {children}
      </motion.span>
    </AnimatePresence>
  );
}
