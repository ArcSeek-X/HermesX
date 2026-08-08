/**
 * @file AlertsPage.tsx
 * @description 告警中心页面，管理告警规则的创建、启用/禁用、删除、测试，并展示触发历史和通知记录
 * @module pages
 */

import type React from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { BellRing } from 'lucide-react';
import { alertsApi } from '../api/alerts';
import type { ParsedApiError } from '../api/error';
import { getParsedApiError } from '../api/error';
import { AlertRuleForm } from '../components/alerts/AlertRuleForm';
import {
  AlertRuleList,
  type AlertRuleBusyState,
  type AlertRuleEnabledFilter,
  type AlertTypeFilter,
} from '../components/alerts/AlertRuleList';
import { AlertTriggerHistory } from '../components/alerts/AlertTriggerHistory';
import { ApiErrorAlert, AppPage, Card, EmptyState, InlineAlert, Loading, PageHeader } from '../components/common';
import type {
  AlertNotificationItem,
  AlertRuleCreateRequest,
  AlertRuleItem,
  AlertRuleTestResponse,
  AlertTriggerItem,
  AlertType,
} from '../types/alerts';
import { formatDateTime } from '../utils/format';
import { usePreference } from '../hooks/usePreference';

/** 每页请求的数据条数 */
const PAGE_SIZE = 20;

/**
 * 将启用状态筛选值转换为 API 查询参数
 * @param value - 筛选值 ('all' | 'enabled' | 'disabled')
 * @returns boolean | undefined - 转换后的查询参数，'all' 时返回 undefined 表示不筛选
 */
function enabledFilterToQuery(value: AlertRuleEnabledFilter): boolean | undefined {
  if (value === 'enabled') return true;
  if (value === 'disabled') return false;
  return undefined;
}

/**
 * 将告警类型筛选值转换为 API 查询参数
 * @param value - 筛选值 ('all' 或具体告警类型)
 * @returns AlertType | undefined - 'all' 时返回 undefined 表示不筛选
 */
function alertTypeFilterToQuery(value: AlertTypeFilter): AlertType | undefined {
  return value === 'all' ? undefined : value;
}

/**
 * 根据测试结果判断展示样式
 * @param result - 告警规则测试响应
 * @returns 'success' | 'warning' | 'danger' - 对应 InlineAlert 的展示样式
 */
function testVariant(result: AlertRuleTestResponse): 'success' | 'warning' | 'danger' {
  if (result.status === 'evaluation_error') return 'danger';
  return result.triggered ? 'success' : 'warning';
}

/**
 * 渲染告警规则测试结果的详细信息
 * @param result - 告警规则测试响应
 * @returns React.ReactNode - 包含状态、触发情况及各目标评估结果的节点
 */
function renderTestResultMessage(result: AlertRuleTestResponse): React.ReactNode {
  const targetResults = result.targetResults ?? [];
  return (
    <div className="space-y-2">
      {/* 测试结果概要：消息、状态、是否触发、观察值 */}
      <div>
        {result.message}
        {' · 状态：'}
        {result.status}
        {' · 触发：'}
        {result.triggered ? '是' : '否'}
        {' · 观察值：'}
        {result.observedValue == null ? '--' : String(result.observedValue)}
      </div>
      {/* 多目标评估统计：仅当评估数 > 1 时展示 */}
      {result.evaluatedCount != null && result.evaluatedCount > 1 ? (
        <div className="text-xs">
          评估 {result.evaluatedCount} · 触发 {result.triggeredCount ?? 0} · 降级 {result.degradedCount ?? 0} · 跳过 {result.skippedCount ?? 0}
        </div>
      ) : null}
      {/* 各目标评估明细：仅当目标数 > 1 时展示，最多展示前 20 条 */}
      {targetResults.length > 1 ? (
        <div className="grid gap-1 text-xs">
          {targetResults.slice(0, 20).map((item) => (
            <div key={`${item.target}-${item.status}`} className="flex flex-wrap justify-between gap-2">
              <span>{item.displayTarget ?? item.target}</span>
              <span>
                {item.status}
                {item.recordStatus ? ` / ${item.recordStatus}` : ''}
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

/** 通知渠道内部标识与展示名称的映射表 */
const notificationChannelLabel: Record<string, string> = {
  __cooldown__: '业务冷却',
  __cooldown_read_failed__: '冷却读取失败',
  __noise_suppressed__: '通知降噪',
  __no_channel__: '无可用渠道',
  __dispatch__: '通知调度',
  __context__: '会话渠道',
};

/**
 * 格式化通知渠道名称，将内部标识转换为用户可读的中文标签
 * @param channel - 渠道内部标识
 * @returns string - 格式化后的渠道名称
 */
function formatNotificationChannel(channel: string): string {
  return notificationChannelLabel[channel] ?? channel;
}

/**
 * 格式化通知状态，根据成功标志和错误码返回中文状态描述
 * @param notification - 通知尝试记录项
 * @returns string - 格式化后的状态文本（成功/冷却抑制/降噪抑制/无渠道/失败）
 */
function formatNotificationStatus(notification: AlertNotificationItem): string {
  if (notification.success) return '成功';
  if (notification.errorCode === 'cooldown_active') return '冷却抑制';
  if (notification.errorCode === 'cooldown_read_failed') return '冷却读取失败';
  if (notification.errorCode === 'noise_suppressed') return '降噪抑制';
  if (notification.errorCode === 'no_channel') return '无渠道';
  return '失败';
}

/**
 * 告警中心页面组件
 * 管理告警规则的 CRUD 操作、一次性测试，展示触发历史和通知尝试记录
 */
const AlertsPage: React.FC = () => {
  // 页面标题设置
  useEffect(() => {
    document.title = '告警中心 - DSA';
  }, []);

  const [rules, setRules] = useState<AlertRuleItem[]>([]); // 告警规则列表
  const [rulesTotal, setRulesTotal] = useState(0); // 告警规则总数（用于分页）
  const [rulesPage, setRulesPage] = useState(1); // 当前规则列表页码
  // L4 缓存：筛选偏好（localStorage 永久保存）
  const [enabledFilter, setEnabledFilter] = usePreference<AlertRuleEnabledFilter>('alerts-enabled-filter', 'all'); // 启用状态筛选
  const [alertTypeFilter, setAlertTypeFilter] = usePreference<AlertTypeFilter>('alerts-type-filter', 'all'); // 告警类型筛选
  const [rulesLoading, setRulesLoading] = useState(false); // 规则列表加载状态
  const [rulesError, setRulesError] = useState<ParsedApiError | null>(null); // 规则列表错误信息
  const [rulesLoaded, setRulesLoaded] = useState(false); // 规则列表是否已首次加载完成

  const [triggers, setTriggers] = useState<AlertTriggerItem[]>([]); // 告警触发历史列表
  const [triggersLoading, setTriggersLoading] = useState(false); // 触发历史加载状态
  const [triggersError, setTriggersError] = useState<ParsedApiError | null>(null); // 触发历史错误信息

  const [notifications, setNotifications] = useState<AlertNotificationItem[]>([]); // 通知尝试记录列表
  const [notificationsLoading, setNotificationsLoading] = useState(false); // 通知记录加载状态
  const [notificationsError, setNotificationsError] = useState<ParsedApiError | null>(null); // 通知记录错误信息

  const [createLoading, setCreateLoading] = useState(false); // 创建规则提交中状态
  const [createError, setCreateError] = useState<ParsedApiError | null>(null); // 创建规则错误信息
  const [createSuccess, setCreateSuccess] = useState<string | null>(null); // 创建规则成功提示
  const [busyRule, setBusyRule] = useState<AlertRuleBusyState | null>(null); // 当前操作中的规则（切换/删除/测试）
  const [testResult, setTestResult] = useState<AlertRuleTestResponse | null>(null); // 规则测试结果
  const rulesRequestIdRef = useRef(0); // 请求序列号，用于取消过期的规则列表请求

  /**
   * 加载告警规则列表
   * 支持分页，自动处理越界页码回退；使用请求序列号防止竞态条件
   * @param pageOverride - 可选的页码覆盖，不传则使用当前 rulesPage
   * @returns 响应数据或 null（请求被取消时）
   */
  const loadRules = useCallback(async (pageOverride?: number) => {
    const requestId = rulesRequestIdRef.current + 1; // 生成新的请求序列号
    rulesRequestIdRef.current = requestId;
    const isLatestRequest = () => rulesRequestIdRef.current === requestId; // 判断当前请求是否为最新
    const requestedPage = pageOverride ?? rulesPage; // 确定请求页码
    const baseQuery = {
      enabled: enabledFilterToQuery(enabledFilter),
      alertType: alertTypeFilterToQuery(alertTypeFilter),
      pageSize: PAGE_SIZE,
    };
    setRulesLoading(true);
    try {
      let response = await alertsApi.listRules({ ...baseQuery, page: requestedPage });
      if (!isLatestRequest()) return null; // 丢弃过期请求的结果
      const lastPage = Math.max(1, Math.ceil(response.total / PAGE_SIZE));
      // 处理越界页码：请求页超出总页数时回退到最后一页
      if (response.items.length === 0 && response.total > 0 && requestedPage > lastPage) {
        setRulesPage(lastPage);
        response = await alertsApi.listRules({ ...baseQuery, page: lastPage });
        if (!isLatestRequest()) return null;
      } else if (pageOverride !== undefined && pageOverride !== rulesPage) {
        setRulesPage(pageOverride); // 同步页码状态
      }
      setRules(response.items);
      setRulesTotal(response.total);
      setRulesError(null);
      setRulesLoaded(true);
      return response;
    } catch (error) {
      if (!isLatestRequest()) return null;
      setRulesError(getParsedApiError(error));
      return null;
    } finally {
      if (isLatestRequest()) {
        setRulesLoading(false);
      }
    }
  }, [alertTypeFilter, enabledFilter, rulesPage]);

  /**
   * 加载告警触发历史（第一页）
   */
  const loadTriggers = useCallback(async () => {
    setTriggersLoading(true);
    try {
      const response = await alertsApi.listTriggers({ page: 1, pageSize: PAGE_SIZE });
      setTriggers(response.items);
      setTriggersError(null);
    } catch (error) {
      setTriggersError(getParsedApiError(error));
    } finally {
      setTriggersLoading(false);
    }
  }, []);

  /**
   * 加载通知尝试记录（第一页）
   */
  const loadNotifications = useCallback(async () => {
    setNotificationsLoading(true);
    try {
      const response = await alertsApi.listNotifications({ page: 1, pageSize: PAGE_SIZE });
      setNotifications(response.items);
      setNotificationsError(null);
    } catch (error) {
      setNotificationsError(getParsedApiError(error));
    } finally {
      setNotificationsLoading(false);
    }
  }, []);

  // 规则列表加载：依赖 loadRules（筛选条件或页码变化时触发）
  useEffect(() => {
    void loadRules();
  }, [loadRules]);

  // 触发历史和通知记录加载：规则列表首次加载完成后触发
  useEffect(() => {
    if (!rulesLoaded) return;
    void loadTriggers();
    void loadNotifications();
  }, [loadNotifications, loadTriggers, rulesLoaded]);

  /**
   * 创建告警规则
   * @param payload - 规则创建请求体
   * @returns boolean - 创建是否成功
   */
  const handleCreateRule = async (payload: AlertRuleCreateRequest) => {
    setCreateLoading(true);
    setCreateError(null);
    setCreateSuccess(null);
    try {
      const created = await alertsApi.createRule(payload);
      setCreateSuccess(`已创建告警规则「${created.name}」`);
      await loadRules(1);
      return true;
    } catch (error) {
      setCreateError(getParsedApiError(error));
      return false;
    } finally {
      setCreateLoading(false);
    }
  };

  /**
   * 切换告警规则的启用/禁用状态
   * @param rule - 目标告警规则
   */
  const handleToggleEnabled = async (rule: AlertRuleItem) => {
    setBusyRule({ id: rule.id, action: 'toggle' });
    try {
      if (rule.enabled) {
        await alertsApi.disableRule(rule.id); // 已启用 -> 禁用
      } else {
        await alertsApi.enableRule(rule.id); // 已禁用 -> 启用
      }
      await loadRules();
    } catch (error) {
      setRulesError(getParsedApiError(error));
    } finally {
      setBusyRule(null);
    }
  };

  /**
   * 删除告警规则
   * @param rule - 目标告警规则
   */
  const handleDeleteRule = async (rule: AlertRuleItem) => {
    setBusyRule({ id: rule.id, action: 'delete' });
    try {
      await alertsApi.deleteRule(rule.id);
      await loadRules();
    } catch (error) {
      setRulesError(getParsedApiError(error));
    } finally {
      setBusyRule(null);
    }
  };

  /**
   * 测试告警规则（一次性评估，不持久化触发记录）
   * @param rule - 目标告警规则
   */
  const handleTestRule = async (rule: AlertRuleItem) => {
    setBusyRule({ id: rule.id, action: 'test' });
    setTestResult(null);
    try {
      const result = await alertsApi.testRule(rule.id);
      setTestResult(result);
    } catch (error) {
      setRulesError(getParsedApiError(error));
    } finally {
      setBusyRule(null);
    }
  };

  return (
    <AppPage className="space-y-5">
      {/* ===== 页面标题区 ===== */}
      <PageHeader
        eyebrow="Alert Center"
        title="告警中心"
        description="管理事件告警、日线技术指标、自选股、持仓/账户联动和大盘红绿灯规则，执行一次性测试，并查看后台评估任务记录的触发历史。"
      />

      {/* ===== 错误与成功提示区 ===== */}
      {createError ? <ApiErrorAlert error={createError} onDismiss={() => setCreateError(null)} /> : null}
      {createSuccess ? (
        <InlineAlert
          title="创建成功"
          message={createSuccess}
          variant="success"
          action={(
            <button type="button" className="text-sm underline" onClick={() => setCreateSuccess(null)}>
              关闭
            </button>
          )}
        />
      ) : null}
      {rulesError ? <ApiErrorAlert error={rulesError} onDismiss={() => setRulesError(null)} /> : null}

      {/* ===== 规则表单与列表区 ===== */}
      <div className="grid items-stretch gap-5 xl:grid-cols-[380px_minmax(0,1fr)]">
        <AlertRuleForm onSubmit={handleCreateRule} isSubmitting={createLoading} />
        <div className="flex h-full min-h-0 flex-col gap-4">
          <AlertRuleList
            className="flex h-full min-h-0 flex-col"
            rules={rules}
            total={rulesTotal}
            page={rulesPage}
            pageSize={PAGE_SIZE}
            isLoading={rulesLoading}
            enabledFilter={enabledFilter}
            alertTypeFilter={alertTypeFilter}
            onEnabledFilterChange={(value) => {
              setEnabledFilter(value);
              setRulesPage(1);
            }}
            onAlertTypeFilterChange={(value) => {
              setAlertTypeFilter(value);
              setRulesPage(1);
            }}
            onPageChange={setRulesPage}
            onToggleEnabled={(rule) => void handleToggleEnabled(rule)}
            onDelete={(rule) => void handleDeleteRule(rule)}
            onTest={(rule) => void handleTestRule(rule)}
            busyRule={busyRule}
          />
          {testResult ? (
            <InlineAlert
              title="测试结果"
              variant={testVariant(testResult)}
              message={renderTestResultMessage(testResult)}
            />
          ) : null}
        </div>
      </div>

      {/* ===== 触发历史区 ===== */}
      {triggersError ? <ApiErrorAlert error={triggersError} onDismiss={() => setTriggersError(null)} /> : null}
      <AlertTriggerHistory triggers={triggers} isLoading={triggersLoading} />

      {/* ===== 通知尝试记录区 ===== */}
      {notificationsError ? <ApiErrorAlert error={notificationsError} onDismiss={() => setNotificationsError(null)} /> : null}
      <Card title="通知尝试记录" subtitle="通知结果" variant="bordered" padding="md">
        {notificationsLoading ? <Loading label="正在加载通知尝试记录" /> : null}
        {!notificationsLoading && notifications.length === 0 ? (
          <EmptyState
            icon={<BellRing className="h-6 w-6" />}
            title="暂无通知尝试记录"
            description="当前没有可展示的通知尝试明细；告警触发仍会按已配置通知渠道发送。"
          />
        ) : null}
        {!notificationsLoading && notifications.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] text-left text-sm">
              <thead className="border-b border-border/60 text-xs uppercase text-muted-text">
                <tr>
                  <th className="px-3 py-2 font-medium">渠道</th>
                  <th className="px-3 py-2 font-medium">状态</th>
                  <th className="px-3 py-2 font-medium">错误码</th>
                  <th className="px-3 py-2 font-medium">耗时</th>
                  <th className="px-3 py-2 font-medium">时间</th>
                  <th className="px-3 py-2 font-medium">诊断</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {notifications.map((notification) => (
                  <tr key={notification.id}>
                    <td className="px-3 py-3">{formatNotificationChannel(notification.channel)}</td>
                    <td className="px-3 py-3">{formatNotificationStatus(notification)}</td>
                    <td className="px-3 py-3">{notification.errorCode ?? '--'}</td>
                    <td className="px-3 py-3">{notification.latencyMs == null ? '--' : `${notification.latencyMs}ms`}</td>
                    <td className="px-3 py-3">{formatDateTime(notification.createdAt)}</td>
                    <td className="px-3 py-3">{notification.diagnostics ?? '--'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </Card>
    </AppPage>
  );
};

export default AlertsPage;
