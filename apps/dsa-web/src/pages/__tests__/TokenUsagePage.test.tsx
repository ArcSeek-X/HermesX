// 测试库：act 包裹状态更新、fireEvent 模拟交互、render/screen 渲染与查询、waitFor 等待异步
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
// 测试框架：beforeEach/describe/it/vi/expect
import { beforeEach, describe, expect, it, vi } from 'vitest';
// 国际化 Provider：本页面支持中英文文案，需要包裹以触发文案切换
import { UiLanguageProvider } from '../../contexts/UiLanguageContext';
// 被测页面组件
import TokenUsagePage from '../TokenUsagePage';

// 用 vi.hoisted 在 mock 之前创建可被外部引用的共享 mock：
// 把 api/index 的默认导出里 get 方法替换成可控 mock，用于断言请求 URL/参数并注入响应
const { get } = vi.hoisted(() => ({
  get: vi.fn(),
}));

// mock api/index：只保留默认导出的 get 方法为 mock，其余逻辑（如有）不依赖
vi.mock('../../api/index', () => ({
  default: { get },
}));

// 仪表盘接口的「月维度」基准响应数据：含总量、按调用类型、按模型、最近调用等字段
const dashboardResponse = {
  period: 'month',
  from_date: '2026-06-01',
  to_date: '2026-06-11',
  total_calls: 3,
  total_prompt_tokens: 120,
  total_completion_tokens: 280,
  total_tokens: 400,
  by_call_type: [
    {
      call_type: 'analysis',
      calls: 2,
      prompt_tokens: 100,
      completion_tokens: 200,
      total_tokens: 300,
    },
    {
      call_type: 'agent',
      calls: 1,
      prompt_tokens: 20,
      completion_tokens: 80,
      total_tokens: 100,
    },
  ],
  by_model: [
    {
      model: 'openai/gpt-test',
      calls: 2,
      prompt_tokens: 100,
      completion_tokens: 200,
      total_tokens: 300,
      max_total_tokens: 240,
    },
    {
      model: 'custom-router',
      calls: 1,
      prompt_tokens: 20,
      completion_tokens: 80,
      total_tokens: 100,
      max_total_tokens: 100,
    },
  ],
  recent_calls: [
    {
      id: 1,
      called_at: '2026-06-11T09:30:00',
      call_type: 'analysis',
      model: 'openai/gpt-test',
      stock_code: '600519',
      prompt_tokens: 40,
      completion_tokens: 200,
      total_tokens: 240,
    },
  ],
};

// 基于基准响应生成自定义响应：传入 overrides 覆盖任意字段，避免重复构造整段数据
function makeDashboardResponse(overrides: Partial<typeof dashboardResponse> = {}) {
  return {
    ...dashboardResponse,
    ...overrides,
  };
}

// 创建一个「可手动控制完成时机的 Promise」（deferred），用于模拟请求乱序返回的场景：
// 调 resolve/reject 时外部才能拿到结果，便于先 resolve 后发的请求、再 resolve 先发的请求
function createDeferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, resolve, reject };
}

// 统一渲染入口：包裹 UiLanguageProvider 以正确加载文案
function renderPage() {
  return render(
    <UiLanguageProvider>
      <TokenUsagePage />
    </UiLanguageProvider>
  );
}

// 每个用例前：清空 localStorage、默认中文环境、清空 mock 记录，并让 get 默认返回月维度数据
beforeEach(() => {
  window.localStorage.clear();
  window.localStorage.setItem('dsa.uiLanguage', 'zh');
  vi.clearAllMocks();
  get.mockResolvedValue({ data: dashboardResponse });
});

describe('TokenUsagePage', () => {
  // 用例 1：正常渲染——校验标题、总量、模型明细、调用类型、最近调用，以及请求参数正确性
  it('renders token summary, model breakdowns, and recent calls from the dashboard API shape', async () => {
    renderPage();

    // 标题与总 token 数（400）出现
    expect(await screen.findByRole('heading', { name: 'Token 用量监控' })).toBeInTheDocument();
    expect(await screen.findByText('400')).toBeInTheDocument();
    // 模型名与调用类型文案各出现 2 次（顶部汇总 + 明细表）
    expect(screen.getAllByText('openai/gpt-test')).toHaveLength(2);
    expect(screen.getAllByText('个股分析')).toHaveLength(2);
    // 最近调用里包含股票代码 600519
    expect(screen.getByText(/600519/)).toBeInTheDocument();
    // 断言：页面使用 month 周期、limit=50 调用了 dashboard 接口
    expect(get).toHaveBeenCalledWith('/api/v1/usage/dashboard', {
      params: { period: 'month', limit: 50 },
    });
  });

  // 用例 2：英文环境下渲染英文文案，且不应出现中文标题
  it('renders English copy when the UI language is English', async () => {
    window.localStorage.setItem('dsa.uiLanguage', 'en');

    renderPage();

    // 标题、周期按钮、调用类型、说明文案均为英文
    expect(await screen.findByRole('heading', { name: 'Token usage' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Today' })).toBeInTheDocument();
    expect(screen.getAllByText('Stock analysis')).toHaveLength(2);
    expect(screen.getByText('Latest 50 LLM token audit records.')).toBeInTheDocument();
    // 中文标题不应出现（确认文案确实切换了）
    expect(screen.queryByText('Token 用量监控')).not.toBeInTheDocument();
  });

  // 用例 3：请求乱序返回时，应展示最新周期（today）的数据，旧请求回来后不被覆盖
  it('keeps the newest period data when dashboard requests resolve out of order', async () => {
    // 用 deferred 分别掌控「月」和「今日」两个请求的返回时机
    const monthRequest = createDeferred<{ data: typeof dashboardResponse }>();
    const todayRequest = createDeferred<{ data: typeof dashboardResponse }>();
    // 今日维度的响应：总量 900，区别于月维度的 400，便于断言最终展示的是哪份数据
    const todayResponse = makeDashboardResponse({
      period: 'today',
      from_date: '2026-06-15',
      to_date: '2026-06-15',
      total_calls: 9,
      total_prompt_tokens: 700,
      total_completion_tokens: 200,
      total_tokens: 900,
      by_call_type: [
        {
          call_type: 'analysis',
          calls: 9,
          prompt_tokens: 700,
          completion_tokens: 200,
          total_tokens: 900,
        },
      ],
      by_model: [
        {
          model: 'openai/gpt-test',
          calls: 9,
          prompt_tokens: 700,
          completion_tokens: 200,
          total_tokens: 900,
          max_total_tokens: 300,
        },
      ],
      recent_calls: [],
    });

    get.mockImplementation((_url, config) => {
      const period = config?.params?.period;
      if (period === 'month') {
        return monthRequest.promise;
      }
      if (period === 'today') {
        return todayRequest.promise;
      }
      return Promise.resolve({ data: dashboardResponse });
    });

    renderPage();

    await waitFor(() => {
      expect(get).toHaveBeenCalledWith('/api/v1/usage/dashboard', {
        params: { period: 'month', limit: 50 },
      });
    });

    fireEvent.click(screen.getByRole('button', { name: '今日' }));

    await waitFor(() => {
      expect(get).toHaveBeenLastCalledWith('/api/v1/usage/dashboard', {
        params: { period: 'today', limit: 50 },
      });
    });

    await act(async () => {
      todayRequest.resolve({ data: todayResponse });
    });

    expect(await screen.findByText('900')).toBeInTheDocument();

    await act(async () => {
      monthRequest.resolve({ data: dashboardResponse });
    });

    await waitFor(() => {
      expect(screen.getByText('900')).toBeInTheDocument();
    });
    expect(screen.queryByText('400')).not.toBeInTheDocument();
  });

  it('reloads dashboard when period changes', async () => {
    renderPage();

    await screen.findByRole('heading', { name: 'Token 用量监控' });
    fireEvent.click(screen.getByRole('button', { name: '今日' }));

    await waitFor(() => {
      expect(get).toHaveBeenLastCalledWith('/api/v1/usage/dashboard', {
        params: { period: 'today', limit: 50 },
      });
    });
  });
});
