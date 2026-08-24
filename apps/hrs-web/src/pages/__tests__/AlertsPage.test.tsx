// 测试库：fireEvent 模拟交互、render/screen 渲染与查询、waitFor 等待异步
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
// 测试框架：beforeEach/describe/it/vi/expect
import { beforeEach, describe, expect, it, vi } from 'vitest';
// 被测页面组件
import AlertsPage from '../AlertsPage';

// 用 vi.hoisted 在 mock 之前创建可被外部引用的共享 mock：
// 把告警 API 的全部方法替换成可控 mock，便于在用例里注入响应、断言调用参数
const {
  listRules,
  createRule,
  deleteRule,
  enableRule,
  disableRule,
  testRule,
  listTriggers,
  listNotifications,
} = vi.hoisted(() => ({
  listRules: vi.fn(),
  createRule: vi.fn(),
  deleteRule: vi.fn(),
  enableRule: vi.fn(),
  disableRule: vi.fn(),
  testRule: vi.fn(),
  listTriggers: vi.fn(),
  listNotifications: vi.fn(),
}));

// mock 告警 API：把 alertsApi 的各方法指向上面的 mock 函数
vi.mock('../../api/alerts', () => ({
  alertsApi: {
    listRules,
    createRule,
    deleteRule,
    enableRule,
    disableRule,
    testRule,
    listTriggers,
    listNotifications,
  },
}));

// mock 组合 API：本页只用到 getAccounts，直接返回空账户列表（避免真实请求）
vi.mock('../../api/portfolio', () => ({
  portfolioApi: {
    getAccounts: vi.fn().mockResolvedValue({ accounts: [] }),
  },
}));

// 统一的「解析后错误」结构：模拟后端返回的 HTTP 错误经前端错误解析层处理后的形态
const parsedError = {
  title: '加载失败',
  message: '告警 API 不可用',
  rawMessage: '告警 API 不可用',
  category: 'http_error' as const,
  status: 500,
};

// 一条基准告警规则数据：价格上穿 1800 的茅台规则，作为列表默认返回项
const rule = {
  id: 1,
  name: '茅台价格突破',
  targetScope: 'single_symbol' as const,
  target: '600519',
  alertType: 'price_cross' as const,
  parameters: { direction: 'above' as const, price: 1800 },
  severity: 'warning' as const,
  enabled: true,
  source: 'api',
  createdAt: '2026-05-18T09:00:00',
  updatedAt: '2026-05-18T09:30:00',
};

// 创建一个可手动控制完成时机的 Promise（deferred），用于模拟请求乱序返回
function createDeferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve;
  });
  return { promise, resolve };
}

// 每个用例前：清空 mock、设定各 API 的默认返回（规则列表、触发历史、通知空态、
// 测试、创建/禁用/启用/删除的成功响应），保证正常渲染路径可用
beforeEach(() => {
  vi.clearAllMocks();
  listRules.mockResolvedValue({ items: [rule], total: 1, page: 1, pageSize: 20 });
  listTriggers.mockResolvedValue({
    items: [
      {
        id: 10,
        ruleId: 1,
        target: '600519',
        observedValue: 1801,
        threshold: 1800,
        reason: '600519 price above 1800',
        dataSource: 'realtime_quote',
        dataTimestamp: '2026-05-18T09:30:00',
        triggeredAt: '2026-05-18T09:30:01',
        status: 'triggered',
      },
    ],
    total: 1,
    page: 1,
    pageSize: 20,
  });
  listNotifications.mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 20 });
  testRule.mockResolvedValue({
    ruleId: 1,
    status: 'triggered',
    triggered: true,
    observedValue: 1801,
    message: '600519 price above 1800',
  });
  createRule.mockResolvedValue(rule);
  disableRule.mockResolvedValue({ ...rule, enabled: false });
  enableRule.mockResolvedValue(rule);
  deleteRule.mockResolvedValue({ deleted: 1 });
});

describe('AlertsPage', () => {
  // 用例 1：初次加载应展示页面说明、规则列表、触发历史与「无通知」空态，
  // 并断言三个列表接口都以默认分页参数被调用
  it('loads rules, trigger history, and notification empty state', async () => {
    render(<AlertsPage />);

    // 页面说明文案出现
    expect(screen.getByText('管理事件告警、日线技术指标、自选股、持仓/账户联动和大盘红绿灯规则，执行一次性测试，并查看后台评估任务记录的触发历史。')).toBeInTheDocument();
    // 规则名、触发历史原因文案、通知空态出现
    expect(await screen.findByText('茅台价格突破')).toBeInTheDocument();
    expect(await screen.findByText('600519 price above 1800')).toBeInTheDocument();
    expect(await screen.findByText('暂无通知尝试记录')).toBeInTheDocument();
    // 断言：三个列表接口以默认筛选/分页参数被调用
    expect(listRules).toHaveBeenCalledWith({
      enabled: undefined,
      alertType: undefined,
      page: 1,
      pageSize: 20,
    });
    expect(listTriggers).toHaveBeenCalledWith({ page: 1, pageSize: 20 });
    expect(listNotifications).toHaveBeenCalledWith({ page: 1, pageSize: 20 });
  });

  // 用例 2：点击「测试」执行一次性 dry-run；结果应只展示声明字段，
  // 不展示非展示用的内部字段（如 dataSource=realtime_quote）
  it('runs a dry-run test and renders only declared response fields', async () => {
    listTriggers.mockResolvedValueOnce({ items: [], total: 0, page: 1, pageSize: 20 });
    render(<AlertsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '测试' }));

    // 断言：testRule 以规则 id=1 被调用，结果区出现「测试结果」与关键字段
    await waitFor(() => expect(testRule).toHaveBeenCalledWith(1));
    expect(await screen.findByText('测试结果')).toBeInTheDocument();
    expect(screen.getByText(/600519 price above 1800/)).toBeInTheDocument();
    expect(screen.getByText(/观察值：1801/)).toBeInTheDocument();
    // 不应把内部字段 dataSource 直接渲染出来
    expect(screen.queryByText(/realtime_quote/)).not.toBeInTheDocument();
  });

  // 用例 3：批量 dry-run——渲染汇总（评估/触发/降级/跳过计数）与每个标的的明细结果，
  // 验证多目标场景下降级（degraded）与未触发（not_triggered）的展示
  it('renders batch dry-run summary and target results', async () => {
    testRule.mockResolvedValueOnce({
      ruleId: 1,
      targetScope: 'watchlist',
      status: 'triggered',
      triggered: true,
      observedValue: 11,
      message: 'Evaluated 2 targets',
      evaluatedCount: 2,
      triggeredCount: 1,
      degradedCount: 1,
      skippedCount: 0,
      targetResults: [
        {
          target: '600519',
          displayTarget: '自选股 - 600519',
          status: 'triggered',
          recordStatus: 'triggered',
          triggered: true,
          observedValue: 11,
          message: 'triggered',
        },
        {
          target: '000001',
          displayTarget: '自选股 - 000001',
          status: 'not_triggered',
          recordStatus: 'degraded',
          triggered: false,
          observedValue: null,
          message: 'degraded',
        },
      ],
    });
    render(<AlertsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '测试' }));

    // 汇总文案：评估 2、触发 1、降级 1、跳过 0
    expect(await screen.findByText(/评估 2 · 触发 1 · 降级 1 · 跳过 0/)).toBeInTheDocument();
    // 各标的明细显示（含降级标的的记录态 not_triggered / degraded）
    expect(screen.getByText('自选股 - 600519')).toBeInTheDocument();
    expect(screen.getByText(/not_triggered \/ degraded/)).toBeInTheDocument();
  });

  // 用例 4：通过表单创建规则，断言 createRule 被调用时标的代码被规整为大写、
  // 参数方向/阈值被正确封装，并出现创建成功提示
  it('creates a rule through the page form and reloads rules', async () => {
    render(<AlertsPage />);

    await screen.findByText('茅台价格突破');
    fireEvent.change(screen.getByLabelText('标的代码'), { target: { value: 'aapl' } });
    fireEvent.change(screen.getByLabelText('价格阈值'), { target: { value: '200' } });
    fireEvent.click(screen.getByRole('button', { name: '创建规则' }));

    await waitFor(() => {
      // 小写 aapl 应被规整为 AAPL
      expect(createRule).toHaveBeenCalledWith(expect.objectContaining({
        target: 'AAPL',
        alertType: 'price_cross',
        parameters: { direction: 'above', price: 200 },
      }));
    });
    expect(await screen.findByText(/已创建告警规则/)).toBeInTheDocument();
  });

  // 用例 5：创建接口失败时，表单应保持已填值不被清空，便于用户修改重试
  it('keeps create form values when create API fails', async () => {
    createRule.mockRejectedValueOnce({ parsedError });
    render(<AlertsPage />);

    await screen.findByText('茅台价格突破');
    fireEvent.change(screen.getByLabelText('标的代码'), { target: { value: 'aapl' } });
    fireEvent.change(screen.getByLabelText('价格阈值'), { target: { value: '200' } });
    fireEvent.click(screen.getByRole('button', { name: '创建规则' }));

    // 断言：出现错误提示「加载失败」，且两个输入框仍保留原值
    expect(await screen.findByText('加载失败')).toBeInTheDocument();
    expect(screen.getByLabelText('标的代码')).toHaveValue('aapl');
    expect(screen.getByLabelText('价格阈值')).toHaveValue(200);
  });

  // 用例 6：当删除操作使当前页（第 2 页）变空时，分页应回退到有效页（第 1 页）
  it('clamps rules pagination when a mutation leaves the current page empty', async () => {
    const page2Rule = { ...rule, id: 2, name: '第二页规则', target: 'AAPL' };
    // 设置 listRules 的四次返回值：第1页 -> 第2页 -> 删除后第2页空 -> 回退第1页
    listRules
      .mockResolvedValueOnce({ items: [rule], total: 21, page: 1, pageSize: 20 })
      .mockResolvedValueOnce({ items: [page2Rule], total: 21, page: 2, pageSize: 20 })
      .mockResolvedValueOnce({ items: [], total: 20, page: 2, pageSize: 20 })
      .mockResolvedValue({ items: [rule], total: 20, page: 1, pageSize: 20 });

    render(<AlertsPage />);

    expect(await screen.findByText('茅台价格突破')).toBeInTheDocument();
    // 翻到第 2 页并删除该页规则
    fireEvent.click(screen.getByRole('button', { name: '2' }));
    expect(await screen.findByText('第二页规则')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('删除 第二页规则'));
    fireEvent.click(await screen.findByRole('button', { name: '删除' }));

    // 断言：deleteRule 以 id=2 被调用；重新加载时回到第 1 页，并可看到第 1 页规则
    await waitFor(() => expect(deleteRule).toHaveBeenCalledWith(2));
    await waitFor(() => {
      expect(listRules).toHaveBeenCalledWith({
        enabled: undefined,
        alertType: undefined,
        page: 1,
        pageSize: 20,
      });
    });
    expect(await screen.findByText('茅台价格突破')).toBeInTheDocument();
  });

  // 用例 7：筛选请求乱序返回时，页面应展示最新（筛选后）结果，旧请求结果不应覆盖
  it('keeps the latest rules response when filter requests resolve out of order', async () => {
    // 用 deferred 分别掌控「初始请求」和「筛选请求」的返回时机
    const initialRequest = createDeferred<{ items: Array<typeof rule>; total: number; page: number; pageSize: number }>();
    const filteredRequest = createDeferred<{ items: Array<typeof rule>; total: number; page: number; pageSize: number }>();
    const staleRule = { ...rule, id: 3, name: '旧筛选规则', enabled: true };
    const filteredRule = { ...rule, id: 4, name: '停用规则', enabled: false };
    // 第一次调用返回初始请求（滞后 resolve），第二次返回筛选请求（先 resolve）
    listRules
      .mockReset()
      .mockReturnValueOnce(initialRequest.promise)
      .mockReturnValueOnce(filteredRequest.promise);

    render(<AlertsPage />);

    // 改变启停状态为「停用」，触发第二次筛选请求（共 2 次调用）
    fireEvent.change(screen.getByLabelText('启停状态'), { target: { value: 'disabled' } });
    await waitFor(() => expect(listRules).toHaveBeenCalledTimes(2));

    // 先 resolve 筛选请求，页面应展示「停用规则」
    filteredRequest.resolve({ items: [filteredRule], total: 1, page: 1, pageSize: 20 });
    expect(await screen.findByText('停用规则')).toBeInTheDocument();

    // 后 resolve 初始（旧）请求，旧规则不应出现，页面仍展示筛选结果
    initialRequest.resolve({ items: [staleRule], total: 1, page: 1, pageSize: 20 });
    await waitFor(() => expect(screen.queryByText('旧筛选规则')).not.toBeInTheDocument());
    expect(screen.getByText('停用规则')).toBeInTheDocument();
  });

  // 用例 8：规则列表接口失败时，应通过 InlineTipCard 展示解析后的错误标题与消息
  it('renders API errors through InlineTipCard', async () => {
    listRules.mockRejectedValueOnce({ parsedError });

    render(<AlertsPage />);

    expect(await screen.findByText('加载失败')).toBeInTheDocument();
    expect(screen.getByText('告警 API 不可用')).toBeInTheDocument();
  });
});
