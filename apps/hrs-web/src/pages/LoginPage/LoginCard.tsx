/**
 * @file LoginCard.tsx
 * @description 登录表单卡片组件：账号/密码输入、HeroUI 表单校验、提交与错误展示（完全基于 HeroUI 重构）
 * @module pages/LoginPage
 */
import type * as React from 'react';
import { useState } from 'react';
import { motion } from "motion/react";
import { Lock } from "lucide-react";
import { Eye, EyeClosed } from "@gravity-ui/icons";
import {
  Alert,
  Button,
  FieldError,
  Form,
  Input,
  InputGroup,
  Label,
  Spinner,
  TextField,
} from '@heroui/react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import type { ParsedApiError } from '../../api/error';
import { isParsedApiError } from '../../api/error';
import { useAuth } from '../../hooks';
import { useUiLanguage } from '../../contexts/UiLanguageContext';

/**
 * 登录表单卡片组件
 * 自包含账号/密码状态与提交逻辑，表单校验、错误提示与提交按钮全部由 HeroUI 实现，
 * 密码框支持点击右侧图标切换明文/密文显示。
 * @returns 登录表单卡片的 JSX 元素
 */
const LoginCard: React.FC = () => {
  /** 认证上下文：提供登录方法 */
  const { login } = useAuth();
  /** UI 语言翻译函数 */
  const { t } = useUiLanguage();
  /** 路由导航函数 */
  const navigate = useNavigate();

  /** URL 查询参数，用于提取登录成功后的重定向地址 */
  const [searchParams] = useSearchParams();
  /** 原始重定向地址，从查询参数 redirect 中获取 */
  const rawRedirect = searchParams.get('redirect') ?? '';
  /** 安全校验后的重定向地址：仅允许相对路径（防止开放重定向攻击） */
  // 必须以 / 开头且不以 // 开头（// 会被浏览器解析为协议相对 URL，可能导致跳转到外部站点）
  const redirect =
    rawRedirect.startsWith('/') && !rawRedirect.startsWith('//') ? rawRedirect : '/';

  /** 用户输入的账号 */
  const [username, setUsername] = useState('');
  /** 用户输入的密码 */
  const [password, setPassword] = useState('');
  /** 密码是否明文显示（点击眼睛图标切换） */
  const [showPassword, setShowPassword] = useState(false);
  /** 表单提交中状态，用于禁用按钮和显示加载动画 */
  const [isSubmitting, setIsSubmitting] = useState(false);
  /** 登录的错误信息，可为字符串或解析后的 API 错误对象 */
  const [error, setError] = useState<string | ParsedApiError | null>(null);

  /**
   * 表单提交事件处理函数
   * 调用登录接口，成功后重定向到目标页面，失败则显示错误信息
   * @param e - 表单提交事件
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    // 空值守卫：账号或密码任一为空时不发起登录请求。
    // 具体的校验错误文案由 HeroUI 的 TextField validate + FieldError（aria 模式实时校验）展示。
    if (!username.trim() || !password) {
      return;
    }
    // 进入提交中状态，禁用表单和按钮
    setIsSubmitting(true);
    try {
      // 调用登录接口验证密码
      const result = await login(password);
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
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, delay: 0.1 }}
      className="hrs-login-card relative group z-20 pointer-events-auto"
    >
      {/* 卡片边框发光效果 */}
      <div className="pointer-events-none absolute -inset-0.5 rounded-3xl bg-gradient-to-b from-[var(--login-accent-glow)] to-[hsl(214_100%_56%_/_0.18)] opacity-50 blur-sm transition duration-1000 group-hover:opacity-100 group-hover:duration-200" />

      <div className="pointer-events-auto relative flex flex-col overflow-hidden rounded-3xl border border-[var(--login-border-card)] bg-[var(--login-bg-card)]/80 p-8 shadow-2xl backdrop-blur-xl">
        {/* 卡片内部角落辉光 */}
        <div className="absolute -right-20 -top-20 h-40 w-40 rounded-full bg-[var(--login-accent-soft)] blur-[50px]" />
        <div className="absolute -bottom-20 -left-20 h-40 w-40 rounded-full bg-blue-600/10 blur-[50px]" />

        {/* ===== 卡片标题 ===== */}
        <div className="mb-8">
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight text-[var(--login-text-primary)]">
            <Lock className="h-5 w-5 text-[var(--login-accent-text)]" />
            <span>{t('login.adminLogin')}</span>
          </h1>
          <p className="mt-2 text-sm text-[var(--login-text-secondary)]">
            {t('login.loginDescription')}
          </p>
        </div>

        {/* ===== 登录表单（HeroUI Form：aria 校验模式，校验失败时阻止提交并显示 FieldError） ===== */}
        <Form
          onSubmit={handleSubmit}
          validationBehavior="aria"
          className="hrs-login-form flex flex-col gap-6"
        >
          {/* ===== 账号输入框（HeroUI TextField + Input，validate 校验必填） ===== */}
          <TextField
            name="username"
            id="username"
            value={username}
            onChange={setUsername}
            isDisabled={isSubmitting}
            fullWidth
            validate={(value) => (!value.trim() ? t('login.usernameRequired') : null)}
          >
            <Label>{t('login.username')}</Label>
            <Input
              placeholder={t('login.usernamePlaceholder')}
              autoComplete="username"
              className="rounded-md"
            />
            <FieldError />
          </TextField>

          {/* ===== 密码输入框（HeroUI TextField + InputGroup，右侧眼睛图标切换明文/密文） ===== */}
          <TextField
            name="password"
            id="password"
            value={password}
            onChange={setPassword}
            isDisabled={isSubmitting}
            fullWidth
            validate={(value) => (!value ? t('login.passwordRequired') : null)}
          >
            <Label>{t('login.loginPassword')}</Label>
            <InputGroup fullWidth className="rounded-md min-h-10">
              <InputGroup.Input
                type={showPassword ? 'text' : 'password'}
                placeholder={t('login.loginPasswordPlaceholder')}
                autoComplete="current-password"
                autoFocus
                className="text-base!"
              />
              <InputGroup.Suffix>
                {/* 密码可见性切换按钮：不参与表单提交 */}
                <button
                  type="button"
                  aria-label={showPassword ? t('login.hidePassword') : t('login.showPassword')}
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="flex h-full items-center justify-center px-2 text-muted-text/60 transition-colors hover:text-muted-text focus-visible:outline-none"
                >
                  {showPassword ? (
                    <EyeClosed className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </InputGroup.Suffix>
            </InputGroup>
            <FieldError />
          </TextField>

          {/* ===== 错误提示区（全局登录失败，由 HeroUI Alert 展示） ===== */}
          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="overflow-hidden"
            >
              <Alert
                status="danger"
                className="!border-[var(--login-error-border)] !bg-[var(--login-error-bg)] !text-[var(--login-error-text)]"
              >
                <Alert.Title>{t('login.validationFailed')}</Alert.Title>
                <Alert.Description>
                  {isParsedApiError(error) ? error.message : error}
                </Alert.Description>
              </Alert>
            </motion.div>
          )}

          {/* ===== 提交按钮（HeroUI Button，含加载状态与微光动画） ===== */}
          <Button
            type="submit"
            variant="primary"
            size="lg"
            fullWidth
            isDisabled={isSubmitting}
            className="group/btn relative h-12 overflow-hidden rounded-xl border-0 bg-gradient-to-r from-[var(--login-brand-button-start)] to-[var(--login-brand-button-end)] font-medium text-[var(--login-button-text)] shadow-lg shadow-[0_18px_36px_hsl(214_100%_8%_/_0.24)] hover:from-[var(--login-brand-button-start-hover)] hover:to-[var(--login-brand-button-end-hover)]"
          >
            <div className="relative z-10 flex items-center justify-center gap-2">
              {isSubmitting ? (
                <>
                  <Spinner size="sm" />
                  <span>{t('login.loginSubmitting')}</span>
                </>
              ) : (
                <span>{t('login.loginSubmit')}</span>
              )}
            </div>
            <div className="absolute inset-0 z-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite] pointer-events-none" />
          </Button>
        </Form>
      </div>

      {/* 提交按钮微光动画所需的 keyframes */}
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes shimmer {
          100% {
            transform: translateX(100%);
          }
        }
      `}} />
    </motion.div>
  );
};

export default LoginCard;
