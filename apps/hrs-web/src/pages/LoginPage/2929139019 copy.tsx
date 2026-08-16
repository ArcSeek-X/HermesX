

/**
 * 登录表单卡片组件
 * 自包含账号/密码状态与提交逻辑，提供表单校验、加载态、登录失败错误展示与提交按钮微光动画
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
    // 进入提交中状态，禁用表单和按钮
    setIsSubmitting(true);
    try {
      alert(password)
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
      className="relative group z-20 pointer-events-auto"
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

        {/* ===== 密码输入表单（HeroUI Form + TextField 包裹，输入框保持项目 PasswordInput） ===== */}
        <Form onSubmit={handleSubmit} className="flex flex-col gap-6">
          {/* ===== 账号输入框（HeroUI TextField 包裹，输入框复用项目基础 Input） ===== */}
          <TextField
            name="username"
            id="username"
            value={username}
            onChange={(value) => setUsername(value)}
            isDisabled={isSubmitting}
            fullWidth
            isRequired
          >
            <Label>{t('login.username')}</Label>
            <Input
              id="username"
              prefixNode={<User className="h-4 w-4 text-muted-text/55" />}
              placeholder={t('login.usernamePlaceholder')}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={isSubmitting}
              autoComplete="username"
            />
            <FieldError>Username must be at least 3 characters</FieldError>
          </TextField>

          <TextField
            name="password"
            id="password"
            value={password}
            onChange={(value) => setPassword(value)}
            isDisabled={isSubmitting}
            fullWidth
            isRequired
            validate={(value) => {
              if (!value) return t('login.passwordRequired');
              return null;
            }}
          >
            <Label>{t('login.loginPassword')}</Label>
            {/* 输入框本体复用项目 PasswordInput：内置 Lock 图标与可见性切换，
                其内部 Input 与 TextField 通过相同 id（password）建立 label 关联 */}
            <PasswordInput
              id="password"
              type="password"
              iconType="password"
              allowTogglePassword
              placeholder={t('login.loginPasswordPlaceholder')}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isSubmitting}
              autoFocus
              autoComplete="current-password"
            />
          </TextField>

          {/* ===== 错误提示区（全局登录失败，由 SettingsAlert 展示） ===== */}
          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="overflow-hidden"
            >
              <SettingsAlert
                title={t('login.validationFailed')}
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

      {/* 提交按钮微光动画所需的 keyframes（提炼自 LoginPage） */}
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
