/**
 * @file LoginPage.tsx
 * @description 登录页，提供管理员密码登录，包含深色紫色弧线背景与 3D 视差动画效果
 * @module pages
 */
import type * as React from 'react';
import { useEffect } from 'react';
import { motion, useMotionValue, useTransform, useSpring } from "motion/react";
import { Network } from "lucide-react";
import { ParticleBackground } from '../../components';
import { UiLanguageToggle } from '../../components/i18n/UiLanguageToggle';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import LoginCard from './LoginCard';

/**
 * 登录页组件
 * 提供管理员密码登录：验证用户输入的密码以完成登录。
 * 包含鼠标视差 3D 倾斜动画、粒子背景、底部紫色弧线（参考 Next-Gen AI Studio 风格）视觉设计
 * @returns 登录页的 JSX 元素
 */
const LoginPage: React.FC = () => {
  /** UI 语言翻译函数 */
  const { t } = useUiLanguage();

  // 设置页面标题
  useEffect(() => {
    document.title = t('auth.login.pageTitle');
  }, [t]);

  // 3D 倾斜效果的鼠标位置值（归一化到 -0.5 ~ 0.5）
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  // 使用弹簧物理平滑鼠标移动，使动画更自然
  const smoothX = useSpring(mouseX, { damping: 30, stiffness: 200 });
  const smoothY = useSpring(mouseY, { damping: 30, stiffness: 200 });

  /**
   * 监听全局鼠标移动，更新视差动画的输入值
   * 将鼠标坐标归一化到 [-0.5, 0.5] 区间，驱动 3D 倾斜效果
   */
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const x = e.clientX / window.innerWidth - 0.5;
      const y = e.clientY / window.innerHeight - 0.5;
      mouseX.set(x);
      mouseY.set(y);
    };
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [mouseX, mouseY]);

  return (
    <div className="relative flex min-h-screen flex-col justify-center overflow-hidden bg-[var(--login-bg-main)] py-12 font-sans selection:bg-[var(--login-accent-soft)] sm:px-6 lg:px-8 [perspective:1500px]">
      {/* ===== 动态粒子背景 ===== */}
      <ParticleBackground />

      {/* ===== 右上角语言切换 ===== */}
      <div className="absolute right-4 top-4 z-30">
        <UiLanguageToggle />
      </div>

      {/* ===== 底部球形光晕背景（参考 Next-Gen AI Studio：黑底 + 半球形蓝色渐变光晕 + 弧线顶部轮廓亮边） ===== */}
      {/* 半球填充层：从屏幕底部升起的主色光晕，向四周渐隐 */}
      <div className="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(ellipse_95%_62%_at_50%_118%,var(--login-arc-core)_0%,var(--login-arc-primary)_45%,transparent_78%)]" />
      {/* 弧线轮廓层：在球弧顶部勾勒一圈高亮边缘，增强科技感 */}
      <div className="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(ellipse_72%_42%_at_50%_114%,transparent_45%,var(--login-arc-glow)_72%,transparent_94%)]" />


      {/* ===== 视差发光光球（跟随鼠标移动产生 3D 视差效果） ===== */}
      <motion.div
        style={{
          x: useTransform(smoothX, [-0.5, 0.5], [-50, 50]),
          y: useTransform(smoothY, [-0.5, 0.5], [-50, 50]),
        }}
        className="absolute left-[20%] top-[20%] -z-10 h-[300px] w-[300px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[var(--login-accent-glow)] blur-[100px]"
      />
      <motion.div
        style={{
          x: useTransform(smoothX, [-0.5, 0.5], [60, -60]),
          y: useTransform(smoothY, [-0.5, 0.5], [60, -60]),
        }}
        className="absolute right-[20%] bottom-[10%] -z-10 h-[400px] w-[400px] translate-x-1/2 translate-y-1/2 rounded-full bg-[var(--login-arc-glow)] blur-[120px]"
      />

      {/* ===== 登录卡片主容器 ===== */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="flex flex-col items-center justify-center mb-10 relative"
        >
          <div className="mt-8 flex flex-col items-center">
            {/* ===== 品牌标题 ===== */}
            <h2 className="text-4xl font-extrabold tracking-tighter text-[var(--login-text-primary)] sm:text-6xl">
              <span className="bg-gradient-to-r from-[var(--login-text-primary)] via-[var(--login-text-primary)] to-[var(--login-text-secondary)] bg-clip-text text-transparent">Hermes</span>
              <span className="bg-gradient-to-r from-[var(--login-brand-start)] to-[var(--login-brand-end)] bg-clip-text text-transparent drop-shadow-[0_0_20px_var(--login-accent-glow)]">X</span>
            </h2>
            <h3 className="mt-1 text-xl font-bold uppercase tracking-[0.5em] text-[var(--login-text-muted)]">
              Analysis Engine
            </h3>
          </div>

          {/* ===== 系统版本徽章 ===== */}
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="mt-6 flex items-center gap-2 rounded-full border border-[var(--login-accent-border)] bg-[var(--login-accent-soft)] px-3 py-1 text-[10px] font-medium text-[var(--login-accent-text)] backdrop-blur-sm"
          >
            <Network className="h-3 w-3" />
            <span>V3.X QUANTITATIVE SYSTEM</span>
          </motion.div>
        </motion.div>

        {/* ===== 登录表单卡片（表单状态、校验、提交逻辑均封装在 LoginCard 内） ===== */}
        <LoginCard />

        {/* Footer info */}
        <motion.p 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-8 text-center font-mono text-xs uppercase tracking-wider text-[var(--login-text-muted)]"
        >
          Secure Connection Established via HRS-V3-TLS
        </motion.p>
      </div>
    </div>
  );
};

export default LoginPage;
