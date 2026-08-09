/**
 * @file LoginPage.tsx
 * @description 登录页，提供管理员密码登录与首次密码设置功能，包含 3D 视差动画背景效果
 * @module pages
 */
import type React from 'react';
import { useState, useEffect } from 'react';
import { motion, useMotionValue, useTransform, useSpring } from "motion/react";
import { Lock, Loader2, Cpu, TrendingUp, Network, ShieldCheck } from "lucide-react";
import { Button, Input, ParticleBackground } from '../components/common';
import { UiLanguageToggle } from '../components/i18n/UiLanguageToggle';
import { useNavigate, useSearchParams } from 'react-router-dom';
import type { ParsedApiError } from '../api/error';
import { isParsedApiError } from '../api/error';
import { useAuth } from '../hooks';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import { SettingsAlert } from '../components/settings';

/**
 * 登录页组件
 * 支持两种模式：
 * 1. 首次设置密码：当系统尚未配置管理员密码时，引导用户设置初始密码
 * 2. 管理员登录：已有密码时，验证用户输入的密码以完成登录
 * 包含鼠标视差 3D 倾斜动画、粒子背景、赛博朋克风格视觉设计
 * @returns 登录页的 JSX 元素
 */
const LoginPage: React.FC = () => {
  /** 认证上下文：提供登录方法、密码状态与初始化状态 */
  const { login, passwordSet, setupState } = useAuth();
  /** UI 语言翻译函数 */
  const { t } = useUiLanguage();
  /** 路由导航函数 */
  const navigate = useNavigate();

  // 设置页面标题
  useEffect(() => {
    document.title = t('login.pageTitle');
  }, [t]);

  /** URL 查询参数，用于提取登录成功后的重定向地址 */
  const [searchParams] = useSearchParams();
  /** 原始重定向地址，从查询参数 redirect 中获取 */
  const rawRedirect = searchParams.get('redirect') ?? '';
  /** 安全校验后的重定向地址：仅允许相对路径（防止开放重定向攻击） */
  // 必须以 / 开头且不以 // 开头（// 会被浏览器解析为协议相对 URL，可能导致跳转到外部站点）
  const redirect =
    rawRedirect.startsWith('/') && !rawRedirect.startsWith('//') ? rawRedirect : '/';

  /** 用户输入的密码 */
  const [password, setPassword] = useState('');
  /** 首次设置密码时的确认密码 */
  const [passwordConfirm, setPasswordConfirm] = useState('');
  /** 表单提交中状态，用于禁用按钮和显示加载动画 */
  const [isSubmitting, setIsSubmitting] = useState(false);
  /** 登录/设置密码的错误信息，可为字符串或解析后的 API 错误对象 */
  const [error, setError] = useState<string | ParsedApiError | null>(null);

  /** 是否为首次设置密码模式：系统未设置密码或密码状态为 no_password 时为 true */
  const isFirstTime = setupState === 'no_password' || !passwordSet;

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

  /**
   * 表单提交事件处理函数
   * 首次设置模式下校验两次密码是否一致，然后调用登录接口
   * 登录成功后重定向到目标页面，失败则显示错误信息
   * @param e - 表单提交事件
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    // 首次设置模式：校验两次密码输入是否一致
    if (isFirstTime && password !== passwordConfirm) {
      setError(t('login.passwordMismatch'));
      return;
    }
    // 进入提交中状态，禁用表单和按钮
    setIsSubmitting(true);
    try {
      // 调用登录接口：首次设置模式传递确认密码，普通登录模式仅传密码
      const result = await login(password, isFirstTime ? passwordConfirm : undefined);
      if (result.success) {
        // 登录成功，重定向到目标页面（替换历史记录，避免后退回登录页）
        navigate(redirect, { replace: true });
      } else {
        // 登录失败，展示服务端返回的错误信息或默认失败提示
        setError(result.error ?? t('login.loginFailed'));
      }
    } finally {
      // 无论成功失败，恢复按钮可点击状态
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative flex min-h-screen flex-col justify-center overflow-hidden bg-[var(--login-bg-main)] py-12 font-sans selection:bg-[var(--login-accent-soft)] sm:px-6 lg:px-8 [perspective:1500px]">
      {/* ===== 动态粒子背景 ===== */}
      <ParticleBackground />

      {/* ===== 右上角语言切换 ===== */}
      <div className="absolute right-4 top-4 z-30">
        <UiLanguageToggle />
      </div>

      {/* ===== 赛博朋克网格背景 ===== */}
      <div className="absolute inset-0 z-0 bg-[linear-gradient(to_right,var(--login-grid-line)_1px,transparent_1px),linear-gradient(to_bottom,var(--login-grid-line)_1px,transparent_1px)] bg-[size:24px_24px] [mask-image:var(--login-grid-mask)]" />

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
        className="absolute right-[20%] bottom-[10%] -z-10 h-[400px] w-[400px] translate-x-1/2 translate-y-1/2 rounded-full bg-emerald-600/10 blur-[120px]"
      />

      {/* ===== 登录卡片主容器 ===== */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="flex flex-col items-center justify-center mb-10 relative"
        >
          {/* ===== 全屏背景 Logo（视差跟随鼠标） ===== */}
          <motion.div
            style={{
              x: useTransform(smoothX, [-0.5, 0.5], [-8, 8]),
              y: useTransform(smoothY, [-0.5, 0.5], [-8, 8]),
              rotate: useTransform(smoothX, [-0.5, 0.5], [-0.5, 0.5]),
            }}
            className="pointer-events-none absolute -top-[20vh] -z-10 opacity-80"
          >
            <div className="relative flex h-[120vh] w-[120vh] items-center justify-center rounded-full border border-[var(--login-accent-soft)] bg-gradient-to-br from-[var(--login-accent-soft)] to-[hsl(214_100%_20%_/_0.18)] shadow-[inset_0_0_200px_var(--login-accent-glow)] blur-[4px]">
              <Cpu className="h-[70vh] w-[70vh] text-[hsl(200_80%_22%_/_0.4)] brightness-50" />
              <TrendingUp className="absolute h-[25vh] w-[25vh] translate-x-[15vh] translate-y-[15vh] text-emerald-900/30 brightness-50" />
            </div>
          </motion.div>

          <div className="mt-8 flex flex-col items-center">
            {/* ===== 品牌标题 ===== */}
            <h2 className="text-4xl font-extrabold tracking-tighter text-[var(--login-text-primary)] sm:text-6xl">
              <span className="bg-gradient-to-r from-[var(--login-text-primary)] via-[var(--login-text-primary)] to-[var(--login-text-secondary)] bg-clip-text text-transparent">DAILY </span>
              <span className="bg-gradient-to-r from-[var(--login-brand-start)] to-[var(--login-brand-end)] bg-clip-text text-transparent drop-shadow-[0_0_20px_var(--login-accent-glow)]">STOCK</span>
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

        {/* ===== 登录表单卡片 ===== */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="relative group z-20 pointer-events-auto"
        >
          {/* 卡片边框发光效果 */}
          <div className="pointer-events-none absolute -inset-0.5 rounded-3xl bg-gradient-to-b from-[var(--login-accent-glow)] to-[hsl(214_100%_56%_/_0.18)] opacity-50 blur-sm transition duration-1000 group-hover:opacity-100 group-hover:duration-200" />

          <div className="pointer-events-auto relative flex flex-col overflow-hidden rounded-3xl border border-[var(--login-border-card)] bg-[var(--login-bg-card)]/80 p-8 shadow-2xl backdrop-blur-xl">
            {/* 卡片内部角落辉光 */}
            <div className="absolute -right-20 -top-20 h-40 w-40 rounded-full bg-[var(--login-accent-soft)] blur-[50px]" />
            <div className="absolute -bottom-20 -left-20 h-40 w-40 rounded-full bg-blue-600/10 blur-[50px]" />

            {/* ===== 卡片标题（根据模式显示"设置密码"或"管理员登录"） ===== */}
            <div className="mb-8">
              <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight text-[var(--login-text-primary)]">
                {isFirstTime ? (
                  <>
                    <ShieldCheck className="h-6 w-6 text-emerald-400" />
                    <span>{t('login.setupTitle')}</span>
                  </>
                ) : (
                  <>
                    <Lock className="h-5 w-5 text-[var(--login-accent-text)]" />
                    <span>{t('login.adminLogin')}</span>
                  </>
                )}
              </h1>
              <p className="mt-2 text-sm text-[var(--login-text-secondary)]">
                {isFirstTime
                  ? t('login.setupDescription')
                  : t('login.loginDescription')}
              </p>
            </div>

            {/* ===== 密码输入表单 ===== */}
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-4">
                <Input
                  id="password"
                  type="password"
                  appearance="login"
                  allowTogglePassword
                  iconType="password"
                  label={isFirstTime ? t('login.adminPassword') : t('login.loginPassword')}
                  placeholder={isFirstTime ? t('login.setupPasswordPlaceholder') : t('login.loginPasswordPlaceholder')}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isSubmitting}
                  autoFocus
                  autoComplete={isFirstTime ? 'new-password' : 'current-password'}
                />

                {isFirstTime && (
                  <Input
                    id="passwordConfirm"
                    type="password"
                    appearance="login"
                    allowTogglePassword
                    iconType="password"
                    label={t('login.confirmPassword')}
                    placeholder={t('login.confirmPasswordPlaceholder')}
                    value={passwordConfirm}
                    onChange={(e) => setPasswordConfirm(e.target.value)}
                    disabled={isSubmitting}
                    autoComplete="new-password"
                  />
                )}
              </div>

              {/* ===== 错误提示区 ===== */}
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="overflow-hidden"
                >
                  <SettingsAlert
                    title={isFirstTime ? t('login.setupFailed') : t('login.validationFailed')}
                    message={isParsedApiError(error) ? error.message : error}
                    variant="error"
                    className="!border-[var(--login-error-border)] !bg-[var(--login-error-bg)] !text-[var(--login-error-text)]"
                  />
                </motion.div>
              )}

              {/* ===== 提交按钮（含加载状态与微光动画） ===== */}
              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="group/btn relative h-12 w-full overflow-hidden rounded-xl border-0 bg-gradient-to-r from-[var(--login-brand-button-start)] to-[var(--login-brand-button-end)] font-medium text-[var(--login-button-text)] shadow-lg shadow-[0_18px_36px_hsl(214_100%_8%_/_0.24)] hover:from-[var(--login-brand-button-start-hover)] hover:to-[var(--login-brand-button-end-hover)]"
                disabled={isSubmitting}
              >
                <div className="relative z-10 flex items-center justify-center gap-2">
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>{isFirstTime ? t('login.setupSubmitting') : t('login.loginSubmitting')}</span>
                    </>
                  ) : (
                    <span>{isFirstTime ? t('login.setupSubmit') : t('login.loginSubmit')}</span>
                  )}
                </div>
                <div className="absolute inset-0 z-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite] pointer-events-none" />
              </Button>
            </form>
          </div>
        </motion.div>

        {/* Footer info */}
        <motion.p 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-8 text-center font-mono text-xs uppercase tracking-wider text-[var(--login-text-muted)]"
        >
          Secure Connection Established via DSA-V3-TLS
        </motion.p>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes shimmer {
          100% {
            transform: translateX(100%);
          }
        }
      `}} />
    </div>
  );
};

export default LoginPage;
