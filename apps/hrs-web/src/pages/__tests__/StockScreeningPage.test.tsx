// 测试库：act 包裹异步状态更新、fireEvent 模拟交互、render/screen 渲染与查询、waitFor 等待异步
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
// 测试框架：beforeEach/describe/it/vi/expect
import { beforeEach, describe, expect, it, vi } from 'vitest';
// 被测页面组件
import StockScreeningPage from '../StockScreeningPage';

// 用 vi.hoisted 在 mock 之前创建可被外部引用的共享 mock：
// 把 AlphaSift 适配层 API 与路由跳转都替换成可控 mock。
// 这里还额外维护 lastScreenResult，使 startScreenTask（提交任务）与
// getScreenTask（轮询结果）能共享同一份选股结果，模拟真实「提交即出结果」的链路。
const {
  enableAlphaSift,
  getAlphaSiftStatus,
  getHotspotDetail,
  getHotspots,
  getStrategies,
  getScreenTask,
  navigate,
  resetLastScreenResult,
  screenStocks,
  startScreenTask,
} = vi.hoisted(() => {
  let lastScreenResult: unknown = null;
  const screenStocks = vi.fn();
  // startScreenTask：调用 screenStocks 拿到结果写入 lastScreenResult，返回「任务已提交」响应
  const startScreenTask = vi.fn(async (payload: unknown) => {
    lastScreenResult = await screenStocks(payload);
    return {
      taskId: 'screen-task-1',
      traceId: 'screen-task-1',
      status: 'pending',
      message: 'AlphaSift 选股任务已提交',
      strategy: 'dual_low',
      market: 'cn',
      maxResults: 3,
    };
  });
  // getScreenTask：按 taskId 返回已完成任务，result 复用 lastScreenResult
  const getScreenTask = vi.fn(async (taskId: string) => {
    void taskId;
    return {
      taskId: 'screen-task-1',
      traceId: 'screen-task-1',
      status: 'completed',
      progress: 100,
      message: '任务执行完成',
      result: lastScreenResult,
    };
  });
  return {
    enableAlphaSift: vi.fn(),
    getAlphaSiftStatus: vi.fn(),
    getHotspotDetail: vi.fn(),
    getHotspots: vi.fn(),
    getStrategies: vi.fn(),
    getScreenTask,
    navigate: vi.fn(),
    resetLastScreenResult: () => {
      lastScreenResult = null;
    },
    screenStocks,
    startScreenTask,
  };
});

// mock 路由：保留真实实现，只把 useNavigate 换成可控 mock，便于断言跳转到分析页
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => navigate,
  };
});

// mock AlphaSift 适配层 API：把 alphasiftApi 各方法指向上面的 mock 函数
vi.mock('../../api/alphasift', () => ({
  alphasiftApi: {
    enable: () => enableAlphaSift(),
    getStatus: () => getAlphaSiftStatus(),
    getHotspotDetail: (payload: unknown) => getHotspotDetail(payload),
    getHotspots: (payload: unknown) => getHotspots(payload),
    getStrategies: () => getStrategies(),
    getScreenTask: (taskId: string) => getScreenTask(taskId),
    screen: (payload: unknown) => screenStocks(payload),
    startScreen: (payload: unknown) => startScreenTask(payload),
  },
}));

// 策略列表的基准响应：仅含一个 dual_low（双低/价值）策略
const mockStrategiesResponse = {
  enabled: true,
  strategies: [
    {
      id: 'dual_low',
      name: 'Dual Low',
      title: 'Dual Low',
      description: 'Low valuation strategy',
      category: 'value',
      tag: 'value',
      tags: ['value'],
      marketScope: ['cn'],
    },
  ],
  strategyCount: 1,
};

// 创建一个可手动控制完成时机的 Promise（deferred，含 resolve/reject），用于模拟异步请求乱序/延迟
function createDeferred<T>() {
  let resolve: (value: T) => void = () => {};
  let reject: (reason?: unknown) => void = () => {};
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

describe('StockScreeningPage', () => {
  // 每个用例前：重置所有 mock、清空 sessionStorage，并设定默认响应——
  // 策略列表、热点详情（含降级/stale 信息）、热点列表（空）。
  // 注意这里用 mockReset 而非 mockClear，以确保 from 链（如 mockResolvedValueOnce）被清空。
  beforeEach(() => {
    enableAlphaSift.mockReset();
    getAlphaSiftStatus.mockReset();
    getHotspotDetail.mockReset();
    getHotspots.mockReset();
    getStrategies.mockReset();
    getScreenTask.mockClear();
    navigate.mockReset();
    resetLastScreenResult();
    screenStocks.mockReset();
    startScreenTask.mockClear();
    getStrategies.mockResolvedValue(mockStrategiesResponse);
    getHotspotDetail.mockResolvedValue({
      enabled: true,
      provider: 'akshare',
      topic: 'AI算力',
      name: 'AI算力',
      canonicalTopic: '算力',
      summary: 'AI算力 盘中发酵。',
      qualityStatus: 'stale',
      missingFields: ['live_stocks'],
      fallbackUsed: true,
      stale: true,
      staleAgeHours: 2.5,
      sourceErrors: ['akshare timeout'],
      route: [{ title: '盘中发酵', description: '出现大笔买入。', source: 'eastmoney_board_change' }],
      stocks: [{
        code: '300000',
        name: '中际旭创',
        role: '核心龙头',
        hotStockScore: 88,
        source: 'last_good_cache.leader_stocks',
        sourceConfidence: 0.65,
        fallbackUsed: true,
      }],
      stockCount: 1,
    });
    getHotspots.mockResolvedValue({ enabled: true, provider: 'akshare', hotspots: [], hotspotCount: 0 });
    window.sessionStorage.clear();
  });

  // 用例 1：配置已开启但可用性检查发现适配层不可用时，应重新同步「未开启」状态，
  // 禁用运行按钮，并展示适配层不可用的错误（含 pip install 提示）
  it('re-syncs enabled state when AlphaSift availability check fails after config is enabled', async () => {
    // 状态检查返回两次：先未启用（未安装）、再已启用但不可用
    getAlphaSiftStatus
      .mockResolvedValueOnce({
        enabled: false,
        available: false,
        installSpecIsDefault: true,
      })
      .mockResolvedValueOnce({
        enabled: true,
        available: false,
        installSpecIsDefault: true,
      });
    // 点击「开启 AlphaSift」时启用调用失败
    enableAlphaSift.mockRejectedValueOnce(new Error('AlphaSift 适配层不可用。请执行 pip install -r requirements.txt'));

    render(<StockScreeningPage />);

    // 断言：初始展示「选股未开启」，运行按钮禁用
    expect(await screen.findByText('选股未开启')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /运行选股/ })).toBeDisabled();

    // 点击开启，状态检查应被调用 2 次；仍停留在「未开启」且运行按钮禁用
    fireEvent.click(screen.getByRole('button', { name: '开启 AlphaSift' }));

    await waitFor(() => expect(getAlphaSiftStatus).toHaveBeenCalledTimes(2));
    expect(screen.getByText('选股未开启')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /运行选股/ })).toBeDisabled();
    // 断言：展示适配层不可用提示与原始错误信息
    expect(screen.getByText(/适配层当前不可用/)).toBeInTheDocument();
    expect(screen.getByText('AlphaSift 适配层不可用。请执行 pip install -r requirements.txt')).toBeInTheDocument();
  });

  // 用例 2：按需加载热点题材——初始不请求详情，展开/刷新后请求列表，点击题材再请求详情；
  // 并校验降级信息、发酵时间线、概念股及「分析」跳转
  it('loads AlphaSift hotspot themes on demand', async () => {
    getAlphaSiftStatus.mockResolvedValueOnce({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    // 第一次列表（初始，空）+ 第二次列表（刷新后，含 AI算力）：验证 refresh 参数
    getHotspots
      .mockResolvedValueOnce({
        enabled: true,
        provider: 'akshare',
        providerUsed: 'akshare',
        hotspots: [],
        hotspotCount: 0,
        cacheUsed: true,
        cachedAt: '2026-06-07T08:00:00Z',
      })
      .mockResolvedValueOnce({
        enabled: true,
        provider: 'akshare',
        providerUsed: 'akshare',
        hotspots: [
          {
            topic: 'AI算力',
            name: 'AI算力',
            heatScore: 88,
            trendScore: 12,
            persistenceScore: 66,
            changePct: 4.2,
            stage: '加速主升',
            sampleStockCount: 8,
            leaders: ['中际旭创', '工业富联'],
          },
        ],
        hotspotCount: 1,
      });

    render(<StockScreeningPage />);

    expect(await screen.findByText('选股已开启')).toBeInTheDocument();
    // 初始列表请求：provider=akshare、top=12、refresh=false
    await waitFor(() => expect(getHotspots).toHaveBeenCalledWith({ provider: 'akshare', top: 12, refresh: false }));
    // 初始不应请求详情
    expect(getHotspotDetail).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: /展开热点题材/ }));
    fireEvent.click(screen.getByRole('button', { name: /刷新热点题材/ }));

    // 刷新后列表请求：refresh=true
    await waitFor(() => expect(getHotspots).toHaveBeenCalledWith({ provider: 'akshare', top: 12, refresh: true }));
    fireEvent.click(await screen.findByRole('button', { name: /AI算力/ }));
    // 点击题材后请求详情：topic=AI算力、refresh=false
    await waitFor(() => expect(getHotspotDetail).toHaveBeenCalledWith({ topic: 'AI算力', provider: 'akshare', refresh: false }));
    await waitFor(() => expect(screen.getAllByText('AI算力').length).toBeGreaterThan(0));
    // 校验详情面板：领先标签、龙头、覆盖股数、时间线、标准题材、降级质量、缺失字段、发酵路线、概念股
    expect(screen.getByText('强势领先')).toBeInTheDocument();
    expect(screen.getByText(/中际旭创、工业富联/)).toBeInTheDocument();
    expect(screen.getByText(/覆盖 8 股/)).toBeInTheDocument();
    expect(await screen.findByText('发酵时间线')).toBeInTheDocument();
    expect(screen.getByText('标准题材：算力')).toBeInTheDocument();
    expect(screen.getByText('质量 stale')).toBeInTheDocument();
    expect(screen.getByText('缓存回退 2.5h')).toBeInTheDocument();
    expect(screen.getByText('详情数据已降级，展开查看原因')).toBeInTheDocument();
    expect(screen.getByText(/缺失字段：live_stocks/)).toBeInTheDocument();
    expect(screen.getByText('盘中发酵')).toBeInTheDocument();
    expect(screen.getByText('概念股')).toBeInTheDocument();
    expect(screen.getByText('中际旭创')).toBeInTheDocument();
    expect(screen.getByText(/来源 last_good_cache\.leader_stocks · 置信 65% · 回退/)).toBeInTheDocument();

    // 点击「分析 中际旭创」应跳转到首页并携带待分析股票信息
    fireEvent.click(screen.getByRole('button', { name: '分析 中际旭创' }));
    expect(navigate).toHaveBeenCalledWith('/home', {
      state: {
        stockCode: '300000',
        stockName: '中际旭创',
        autoAnalyze: true,
        selectionSource: 'alphasift_hotspot',
      },
    });
  });

  // 用例 3：初始加载时后端返回的英文「无缓存」提示，应被本地化为中文，且不展示原始英文
  it('localizes backend hotspot no-cache hint on initial load', async () => {
    getAlphaSiftStatus.mockResolvedValueOnce({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    getHotspots.mockResolvedValueOnce({
      enabled: true,
      provider: 'akshare',
      providerUsed: 'akshare',
      hotspots: [],
      hotspotCount: 0,
      message: 'No cached AlphaSift hotspot snapshot. Click refresh to fetch live hotspots.',
    });

    render(<StockScreeningPage />);

    // 断言：展示中文提示，且不展示原始英文 message
    expect(await screen.findByText('暂无缓存热点题材，展开后可点击刷新拉取实时数据。')).toBeInTheDocument();
    expect(screen.queryByText(/No cached AlphaSift hotspot snapshot/)).not.toBeInTheDocument();
  });

  // 用例 4：热点源连接失败时，应先展示用户可读的空消息，而非原始 sourceError 细节
  it('shows backend hotspot empty message before raw source diagnostics', async () => {
    getAlphaSiftStatus.mockResolvedValueOnce({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    getHotspots.mockResolvedValueOnce({
      enabled: true,
      provider: 'akshare',
      providerUsed: 'HrsEastMoneyHotspotProvider',
      hotspots: [],
      hotspotCount: 0,
      sourceErrors: ['eastmoney_hotspot_unavailable', "RemoteDisconnected('Remote end closed connection without response')"],
      message: '热点源连接中断，暂无可用缓存。',
    });

    render(<StockScreeningPage />);

    expect(await screen.findByText('热点源连接中断，暂无可用缓存。')).toBeInTheDocument();
    expect(screen.queryByText(/RemoteDisconnected/)).not.toBeInTheDocument();
  });

  // 用例 5：详情应优先展示合并后的「发酵路线摘要（route）」，隐藏原始的「时间线（timeline）」原始文本
  it('prefers merged hotspot route summaries over raw timeline items', async () => {
    getAlphaSiftStatus.mockResolvedValueOnce({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    getHotspots.mockResolvedValueOnce({
      enabled: true,
      provider: 'akshare',
      providerUsed: 'akshare',
      hotspots: [{ topic: 'AI算力', name: 'AI算力', heatScore: 88, stage: '加速主升' }],
      hotspotCount: 1,
    });
    getHotspotDetail.mockResolvedValueOnce({
      enabled: true,
      provider: 'akshare',
      topic: 'AI算力',
      name: 'AI算力',
      summary: 'AI算力 当前热点详情。',
      route: [{ title: 'route-summary', description: 'compact route summary', source: 'news_search' }],
      timeline: [{ title: 'raw-timeline', description: 'full raw timeline text should stay hidden', source: 'raw_news' }],
      stocks: [],
      stockCount: 0,
    });

    render(<StockScreeningPage />);

    await waitFor(() => expect(getHotspots).toHaveBeenCalledWith({ provider: 'akshare', top: 12, refresh: false }));
    fireEvent.click(screen.getByRole('button', { name: /展开热点题材/ }));
    fireEvent.click(await screen.findByRole('button', { name: /AI算力/ }));

    // 断言：route 摘要出现，raw timeline 文本被隐藏
    expect(await screen.findByText('route-summary')).toBeInTheDocument();
    expect(screen.getByText('compact route summary')).toBeInTheDocument();
    expect(screen.queryByText('raw-timeline')).not.toBeInTheDocument();
    expect(screen.queryByText('full raw timeline text should stay hidden')).not.toBeInTheDocument();
  });

  // 用例 6：热点列表响应里若已预取 details，点击题材时应直接用预取数据，不再额外请求详情
  it('uses prefetched hotspot details from the hotspot list response', async () => {
    getAlphaSiftStatus.mockResolvedValueOnce({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    getHotspots.mockResolvedValueOnce({
      enabled: true,
      provider: 'akshare',
      providerUsed: 'akshare',
      hotspots: [{ topic: 'Moly', name: 'Moly', heatScore: 96, stage: 'warming' }],
      hotspotCount: 1,
      details: {
        Moly: {
          enabled: true,
          provider: 'akshare',
          topic: 'Moly',
          name: 'Moly',
          summary: 'Moly event summary',
          route: [{ title: 'prefetched catalyst', description: 'substitution drove the theme', source: 'news_search' }],
          stocks: [{ code: '603799', name: 'Moly Leader', role: 'leader', hotStockScore: 90 }],
          stockCount: 1,
        },
      },
    });

    render(<StockScreeningPage />);

    await waitFor(() => expect(getHotspots).toHaveBeenCalledWith({ provider: 'akshare', top: 12, refresh: false }));
    fireEvent.click(screen.getByRole('button', { name: /展开热点题材/ }));
    fireEvent.click(await screen.findByRole('button', { name: /Moly/ }));

    // 断言：预取的摘要与概念股出现，且没有发起独立的详情请求（用预取数据）
    expect(await screen.findByText('prefetched catalyst')).toBeInTheDocument();
    expect(screen.getByText('substitution drove the theme')).toBeInTheDocument();
    expect(screen.getByText('Moly Leader')).toBeInTheDocument();
    expect(getHotspotDetail).not.toHaveBeenCalled();
  });

  it('loads selected hotspot detail once when switching themes', async () => {
    getAlphaSiftStatus.mockResolvedValueOnce({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    getHotspots.mockResolvedValueOnce({
      enabled: true,
      provider: 'akshare',
      providerUsed: 'akshare',
      hotspots: [
        {
          topic: 'AI算力',
          name: 'AI算力',
          heatScore: 88,
          stage: '加速主升',
        },
        {
          topic: '机器人执行器',
          name: '机器人执行器',
          heatScore: 80,
          stage: '轮动扩散',
        },
      ],
      hotspotCount: 2,
    });

    render(<StockScreeningPage />);

    expect(await screen.findByText('选股已开启')).toBeInTheDocument();
    await waitFor(() => expect(getHotspots).toHaveBeenCalledWith({ provider: 'akshare', top: 12, refresh: false }));
    expect(getHotspotDetail).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: /展开热点题材/ }));
    fireEvent.click(screen.getByRole('button', { name: /AI算力/ }));
    await waitFor(() => expect(getHotspotDetail).toHaveBeenCalledWith({ topic: 'AI算力', provider: 'akshare', refresh: false }));
    expect(getHotspotDetail).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('button', { name: /机器人执行器/ }));

    await waitFor(() =>
      expect(getHotspotDetail).toHaveBeenLastCalledWith({ topic: '机器人执行器', provider: 'akshare', refresh: false }),
    );
    await new Promise((resolve) => window.setTimeout(resolve, 0));
    expect(getHotspotDetail).toHaveBeenCalledTimes(2);
  });

  // 用例 7：在加载某一题材（AI算力）详情后，切换到另一个题材（机器人执行器）时，
  // 应清空旧详情、显示加载中占位，待新详情返回后再展示，避免串台
  it('clears loaded hotspot detail while loading a different theme', async () => {
    getAlphaSiftStatus.mockResolvedValueOnce({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    getHotspots.mockResolvedValueOnce({
      enabled: true,
      provider: 'akshare',
      providerUsed: 'akshare',
      hotspots: [
        {
          topic: 'AI算力',
          name: 'AI算力',
          heatScore: 88,
          stage: '加速主升',
        },
        {
          topic: '机器人执行器',
          name: '机器人执行器',
          heatScore: 80,
          stage: '轮动扩散',
        },
      ],
      hotspotCount: 2,
    });

    // AI算力详情立即返回；机器人执行器详情用 deferred 延后返回，便于观察加载占位
    const robotDetail = createDeferred<unknown>();
    getHotspotDetail
      .mockResolvedValueOnce({
        enabled: true,
        provider: 'akshare',
        topic: 'AI算力',
        name: 'AI算力',
        summary: 'AI算力 盘中发酵。',
        route: [{ title: '盘中发酵', description: '出现大笔买入。', source: 'eastmoney_board_change' }],
        stocks: [{ code: '300000', name: '中际旭创', role: '核心龙头', hotStockScore: 88 }],
        stockCount: 1,
      })
      .mockImplementationOnce(({ topic }: { topic: string }) => {
        if (topic === '机器人执行器') {
          return robotDetail.promise;
        }
        return Promise.reject(new Error(`unexpected topic: ${topic}`));
      });

    render(<StockScreeningPage />);

    expect(await screen.findByText('选股已开启')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /展开热点题材/ }));
    fireEvent.click(await screen.findByRole('button', { name: /AI算力/ }));
    expect(await screen.findByText('盘中发酵')).toBeInTheDocument();
    expect(screen.getByText('中际旭创')).toBeInTheDocument();

    // 点击切换到机器人执行器
    fireEvent.click(screen.getByRole('button', { name: /机器人执行器/ }));

    await waitFor(() =>
      expect(getHotspotDetail).toHaveBeenLastCalledWith({ topic: '机器人执行器', provider: 'akshare', refresh: false }),
    );
    expect(screen.getAllByText('机器人执行器').length).toBeGreaterThan(0);
    // 断言：新详情加载中应展示占位，且旧 AI算力 详情已被清空
    expect(screen.getByText('正在读取发酵路线与概念股...')).toBeInTheDocument();
    expect(screen.queryByText('盘中发酵')).not.toBeInTheDocument();
    expect(screen.queryByText('中际旭创')).not.toBeInTheDocument();

    // 机器人执行器详情返回后，应展示其路线与概念股
    await act(async () => {
      robotDetail.resolve({
        enabled: true,
        provider: 'akshare',
        topic: '机器人执行器',
        name: '机器人执行器',
        summary: '机器人执行器 继续发酵。',
        route: [{ title: '机器人发酵', description: '执行器链条扩散。', source: 'eastmoney_board_change' }],
        stocks: [{ code: '300111', name: '机器人龙头', role: '核心龙头', hotStockScore: 86 }],
        stockCount: 1,
      });
    });

    expect(await screen.findByText('机器人发酵')).toBeInTheDocument();
    expect(screen.getByText('机器人龙头')).toBeInTheDocument();
  });

  // 用例 8：切换题材后，旧的（AI算力）详情响应即使晚到也应被忽略，
  // 页面只能展示当前已选题材（机器人执行器）的数据，避免陈旧响应串台
  it('ignores stale hotspot detail responses when switching themes', async () => {
    getAlphaSiftStatus.mockResolvedValueOnce({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    getHotspots.mockResolvedValueOnce({
      enabled: true,
      provider: 'akshare',
      providerUsed: 'akshare',
      hotspots: [
        {
          topic: 'AI算力',
          name: 'AI算力',
          heatScore: 88,
          stage: '加速主升',
        },
        {
          topic: '机器人执行器',
          name: '机器人执行器',
          heatScore: 80,
          stage: '轮动扩散',
        },
      ],
      hotspotCount: 2,
    });

    // 两个详情都用 deferred 控制返回时机
    const aiDetail = createDeferred<unknown>();
    const robotDetail = createDeferred<unknown>();
    getHotspotDetail.mockImplementation(({ topic }: { topic: string }) => {
      if (topic === 'AI算力') {
        return aiDetail.promise;
      }
      if (topic === '机器人执行器') {
        return robotDetail.promise;
      }
      return Promise.reject(new Error(`unexpected topic: ${topic}`));
    });

    render(<StockScreeningPage />);

    expect(await screen.findByText('选股已开启')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /展开热点题材/ }));
    fireEvent.click(await screen.findByRole('button', { name: /AI算力/ }));
    await waitFor(() => expect(getHotspotDetail).toHaveBeenCalledWith({ topic: 'AI算力', provider: 'akshare', refresh: false }));

    // 切换到机器人执行器
    fireEvent.click(screen.getByRole('button', { name: /机器人执行器/ }));

    await waitFor(() =>
      expect(getHotspotDetail).toHaveBeenLastCalledWith({ topic: '机器人执行器', provider: 'akshare', refresh: false }),
    );
    // 先 resolve 机器人执行器详情
    await act(async () => {
      robotDetail.resolve({
        enabled: true,
        provider: 'akshare',
        topic: '机器人执行器',
        name: '机器人执行器',
        summary: '机器人执行器 继续发酵。',
        route: [{ title: '机器人发酵', description: '执行器链条扩散。', source: 'eastmoney_board_change' }],
        stocks: [{ code: '300111', name: '机器人龙头', role: '核心龙头', hotStockScore: 86 }],
        stockCount: 1,
      });
    });

    expect(await screen.findByText('机器人发酵')).toBeInTheDocument();

    // 再 resolve 旧的 AI算力 详情（晚到），应被忽略
    await act(async () => {
      aiDetail.resolve({
        enabled: true,
        provider: 'akshare',
        topic: 'AI算力',
        name: 'AI算力',
        summary: 'AI算力 旧响应。',
        route: [{ title: 'AI旧发酵', description: '旧请求晚到。', source: 'eastmoney_board_change' }],
        stocks: [{ code: '300000', name: '中际旭创', role: '核心龙头', hotStockScore: 88 }],
        stockCount: 1,
      });
    });

    // 断言：仍展示机器人执行器，旧的 AI旧发酵/中际旭创 不应出现
    expect(screen.getByText('机器人发酵')).toBeInTheDocument();
    expect(screen.getByText('机器人龙头')).toBeInTheDocument();
    expect(screen.queryByText('AI旧发酵')).not.toBeInTheDocument();
    expect(screen.queryByText('中际旭创')).not.toBeInTheDocument();
  });

  // 用例 9：刷新热点题材后，若同一题材仍在榜内，应重新拉取该题材详情并显示最新数据
  it('reloads selected hotspot detail when refreshed themes keep the same topic', async () => {
    getAlphaSiftStatus.mockResolvedValueOnce({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    getHotspots
      .mockResolvedValueOnce({
        enabled: true,
        provider: 'akshare',
        providerUsed: 'akshare',
        hotspots: [
          {
            topic: 'AI算力',
            name: 'AI算力',
            heatScore: 88,
            stage: '加速主升',
          },
          {
            topic: '机器人执行器',
            name: '机器人执行器',
            heatScore: 80,
            stage: '轮动扩散',
          },
        ],
        hotspotCount: 2,
      })
      .mockResolvedValueOnce({
        enabled: true,
        provider: 'akshare',
        providerUsed: 'akshare',
        hotspots: [
          {
            topic: 'AI算力',
            name: 'AI算力',
            heatScore: 91,
            stage: '高位发酵',
          },
        ],
        hotspotCount: 1,
      });
    getHotspotDetail
      .mockResolvedValueOnce({
        enabled: true,
        provider: 'akshare',
        topic: 'AI算力',
        name: 'AI算力',
        summary: 'AI算力 盘中发酵。',
        route: [{ title: '盘中发酵', description: '出现大笔买入。', source: 'eastmoney_board_change' }],
        stocks: [{ code: '300000', name: '中际旭创', role: '核心龙头', hotStockScore: 88 }],
        stockCount: 1,
      })
      .mockResolvedValueOnce({
        enabled: true,
        provider: 'akshare',
        topic: 'AI算力',
        name: 'AI算力',
        summary: 'AI算力 刷新后继续发酵。',
        route: [{ title: '刷新发酵', description: '刷新后仍在榜内。', source: 'eastmoney_board_change' }],
        stocks: [{ code: '601138', name: '工业富联', role: '核心龙头', hotStockScore: 90 }],
        stockCount: 1,
      });

    render(<StockScreeningPage />);

    expect(await screen.findByText('选股已开启')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /展开热点题材/ }));
    fireEvent.click(await screen.findByRole('button', { name: /AI算力/ }));
    await waitFor(() => expect(getHotspotDetail).toHaveBeenCalledTimes(1));

    // 点击刷新热点题材：列表请求 refresh=true，且已选 AI算力 详情被重新拉取（refresh=true）
    fireEvent.click(screen.getByRole('button', { name: /刷新热点题材/ }));

    await waitFor(() => expect(getHotspots).toHaveBeenCalledWith({ provider: 'akshare', top: 12, refresh: true }));
    await waitFor(() => expect(getHotspotDetail).toHaveBeenCalledTimes(2));
    expect(getHotspotDetail).toHaveBeenLastCalledWith({ topic: 'AI算力', provider: 'akshare', refresh: true });
    // 断言：展示刷新后的新热度（91）对应详情「刷新发酵」与「工业富联」
    expect(await screen.findByText('刷新发酵')).toBeInTheDocument();
    expect(screen.getByText('工业富联')).toBeInTheDocument();
  });

  // 用例 10：手动刷新热点题材失败时，应保留已有的热点卡片，并展示错误，而非清空或白屏
  it('keeps existing hotspot cards when manual refresh fails', async () => {
    getAlphaSiftStatus.mockResolvedValueOnce({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    getHotspots
      .mockResolvedValueOnce({
        enabled: true,
        provider: 'akshare',
        providerUsed: 'akshare',
        hotspots: [
          {
            topic: 'AI算力',
            name: 'AI算力',
            heatScore: 88,
            trendScore: 12,
            persistenceScore: 66,
            changePct: 4.2,
            stage: '加速主升',
            sampleStockCount: 8,
            leaders: ['中际旭创', '工业富联'],
          },
        ],
        hotspotCount: 1,
      })
      .mockRejectedValueOnce(new Error('manual refresh failed'));

    render(<StockScreeningPage />);

    expect(await screen.findByText('选股已开启')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /展开热点题材/ }));
    expect(await screen.findByText('强势领先')).toBeInTheDocument();
    expect(screen.getByText(/中际旭创、工业富联/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /刷新热点题材/ }));

    await waitFor(() => expect(getHotspots).toHaveBeenCalledWith({ provider: 'akshare', top: 12, refresh: true }));
    expect(await screen.findByText(/manual refresh failed/)).toBeInTheDocument();
    expect(screen.getByText('强势领先')).toBeInTheDocument();
    expect(screen.getByText(/中际旭创、工业富联/)).toBeInTheDocument();
    expect(screen.queryByText(/点击刷新后会拉取热点概念/)).not.toBeInTheDocument();
  });

  // 用例 11：当策略输入框填入非预设的策略 id 时，应回退显示为「自定义策略」，并照常提交选股
  it('shows input strategy when strategy is not in preset list', async () => {
    getAlphaSiftStatus.mockResolvedValueOnce({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    screenStocks.mockResolvedValue({
      enabled: true,
      candidates: [],
      candidateCount: 0,
    });

    render(<StockScreeningPage />);

    expect(await screen.findByText('选股已开启')).toBeInTheDocument();
    // 在「策略参数」输入框填入非预设策略
    fireEvent.change(screen.getByLabelText('策略参数'), {
      target: { value: 'custom_strategy_alpha' },
    });

    expect(screen.getByDisplayValue('custom_strategy_alpha')).toBeInTheDocument();

    // 运行选股：断言 screen 被调用一次，并展示「自定义策略（custom_strategy_alpha）」标签
    fireEvent.click(screen.getByRole('button', { name: /运行选股/ }));
    await waitFor(() => expect(screenStocks).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByText(/自定义策略 \(custom_strategy_alpha\)/)).toBeInTheDocument());
  });

  // 用例 12：市场下拉应仅含 cn，且点击各策略按钮后选中的策略 id 正确（最终为 shrink_pullback）
  it('uses supported AlphaSift strategy ids and cn market', async () => {
    getStrategies.mockResolvedValueOnce({
      enabled: true,
      strategies: [
        { id: 'balanced_alpha', name: '平衡选股', description: 'desc', category: '框架' },
        { id: 'capital_heat', name: '资金热度', description: 'desc', category: '动量' },
        { id: 'dual_low', name: '双低', description: 'desc', category: '价值' },
        { id: 'oversold_reversal', name: '超跌', description: 'desc', category: '反转' },
        { id: 'shrink_pullback', name: '缩量回踩', description: 'desc', category: '趋势' },
      ],
      strategyCount: 5,
    });
    getAlphaSiftStatus.mockResolvedValueOnce({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    screenStocks.mockResolvedValue({
      enabled: true,
      candidates: [],
      candidateCount: 0,
    });

    render(<StockScreeningPage />);

    expect(await screen.findByText('选股已开启')).toBeInTheDocument();

    const marketSelect = screen.getByLabelText('市场') as HTMLSelectElement;
    expect(Array.from(marketSelect.options).map((option) => option.value)).toEqual(['cn']);

    [
      ['平衡选股', 'balanced_alpha'],
      ['资金热度', 'capital_heat'],
      ['超跌', 'oversold_reversal'],
      ['缩量回踩', 'shrink_pullback'],
    ].forEach(([label, id]) => {
      fireEvent.click(screen.getByRole('button', { name: new RegExp(label) }));
      expect(screen.getByDisplayValue(id)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /运行选股/ }));
    await waitFor(() => expect(screenStocks).toHaveBeenCalledTimes(1));
    expect(screenStocks).toHaveBeenCalledWith({
      market: 'cn',
      strategy: 'shrink_pullback',
      maxResults: 3,
    });
  });

  // 用例 13：切换策略时，应先清空上一次选股结果（候选列表），回到「等待运行」状态，
  // 并展示当前策略名 + 市场
  it('clears previous screening candidates when strategy changes', async () => {
    getStrategies.mockResolvedValueOnce({
      enabled: true,
      strategies: [
        { id: 'dual_low', name: '双低选股', description: 'desc', category: '价值' },
        { id: 'capital_heat', name: '资金热度', description: 'desc', category: '动量' },
      ],
      strategyCount: 2,
    });
    getAlphaSiftStatus.mockResolvedValueOnce({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    screenStocks.mockResolvedValueOnce({
      enabled: true,
      candidates: [
        {
          rank: 1,
          code: '000001',
          name: '旧策略股票',
          score: 88.5,
          reason: 'old result',
          raw: {},
        },
      ],
      candidateCount: 1,
    });

    render(<StockScreeningPage />);

    expect(await screen.findByText('选股已开启')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /运行选股/ }));

    expect(await screen.findByText('旧策略股票')).toBeInTheDocument();
    expect(screen.getByText('选股完成')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /资金热度/ }));

    expect(screen.queryByText('旧策略股票')).not.toBeInTheDocument();
    expect(screen.getByText('等待运行')).toBeInTheDocument();
    expect(screen.getByText('当前策略：资金热度 · A 股')).toBeInTheDocument();
  });

  // 用例 14：运行选股后在 sessionStorage 记录进行中任务；页面卸载再挂载（remount）时，
  // 应通过 getScreenTask 恢复任务进度，最终展示结果并清理 sessionStorage
  it('restores an in-flight screening task after remounting the page', async () => {
    getAlphaSiftStatus.mockResolvedValue({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    screenStocks.mockResolvedValueOnce({
      enabled: true,
      candidates: [
        {
          rank: 1,
          code: '000001',
          name: '恢复后的候选',
          score: 88.5,
          reason: 'restored result',
          raw: {},
        },
      ],
      candidateCount: 1,
    });
    getScreenTask
      .mockResolvedValueOnce({
        taskId: 'screen-task-1',
        traceId: 'screen-task-1',
        status: 'processing',
        progress: 35,
        message: '正在执行 AlphaSift 选股',
        result: null,
      })
      .mockResolvedValueOnce({
        taskId: 'screen-task-1',
        traceId: 'screen-task-1',
        status: 'completed',
        progress: 100,
        message: '任务执行完成',
        result: {
          enabled: true,
          candidates: [
            {
              rank: 1,
              code: '000001',
              name: '恢复后的候选',
              score: 88.5,
              reason: 'restored result',
              raw: {},
            },
          ],
          candidateCount: 1,
        },
      });

    const firstRender = render(<StockScreeningPage />);

    expect(await screen.findByText('选股已开启')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /运行选股/ }));

    // 选股运行中，且进行中任务 id 已写入 sessionStorage（用于跨 remount 恢复）
    expect(await screen.findByText('选股运行中')).toBeInTheDocument();
    expect(window.sessionStorage.getItem('hrs.alphasift.activeScreenTask.v1')).toContain('screen-task-1');

    // 卸载并重新挂载页面，模拟用户离开后返回
    firstRender.unmount();
    render(<StockScreeningPage />);

    // 断言：从 sessionStorage 恢复出候选结果，完成后 sessionStorage 任务记录被清理
    expect(await screen.findByText('恢复后的候选')).toBeInTheDocument();
    expect(screen.getByText('选股完成')).toBeInTheDocument();
    expect(window.sessionStorage.getItem('hrs.alphasift.activeScreenTask.v1')).toBeNull();
  });

  // 用例 15：从 sessionStorage 恢复进行中任务后，若状态轮询超时（ECONNABORTED），
  // 应保持任务可恢复、展示「轮询超时将自动重试」提示，且不展示底层连接错误原文
  it('keeps a restored screening task recoverable when status polling times out', async () => {
    getAlphaSiftStatus.mockResolvedValue({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    window.sessionStorage.setItem('hrs.alphasift.activeScreenTask.v1', JSON.stringify({
      taskId: 'screen-task-1',
      market: 'cn',
      strategy: 'dual_low',
      maxResults: 3,
    }));
    getScreenTask.mockRejectedValueOnce(Object.assign(new Error('timeout of 30000ms exceeded'), {
      code: 'ECONNABORTED',
    }));

    render(<StockScreeningPage />);

    expect(await screen.findByText('选股任务运行中')).toBeInTheDocument();
    await waitFor(() => expect(getScreenTask).toHaveBeenCalledTimes(1));
    expect(screen.getByText('选股运行中')).toBeInTheDocument();
    expect(screen.getByText('选股任务仍在后台运行，状态轮询暂时超时，将自动重试。')).toBeInTheDocument();
    expect(screen.queryByText(/连接上游服务超时/)).not.toBeInTheDocument();
    expect(window.sessionStorage.getItem('hrs.alphasift.activeScreenTask.v1')).toContain('screen-task-1');
  });

  // 用例 16：LLM 重排失败降级时，应明确展示「LLM 已降级 / 未重排」提示与原因，
  // 而非把 LLM 字段当作正常空值静默展示，且不暴露原始英文错误（Missing gemini_api_key）
  it('surfaces AlphaSift LLM fallback instead of showing empty LLM fields as normal', async () => {
    getAlphaSiftStatus.mockResolvedValueOnce({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    screenStocks.mockResolvedValueOnce({
      enabled: true,
      candidates: [
        {
          rank: 1,
          code: '000001',
          name: '平安银行',
          score: 88.5,
          reason: '本地后置评分: value_quality',
          amount: 1042000000,
          factorScores: {
            value: 87.44,
            liquidity: 93.33,
          },
          raw: {},
        },
      ],
      candidateCount: 1,
      snapshotCount: 5193,
      afterFilterCount: 20,
      llmRanked: false,
      warnings: ['LLM ranking failed, falling back to screen_score: Missing gemini_api_key'],
    });

    render(<StockScreeningPage />);

    expect(await screen.findByText('选股已开启')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /运行选股/ }));

    expect(await screen.findByText('LLM 已降级')).toBeInTheDocument();
    expect(screen.getByText(/缺少可用 LLM API Key/)).toBeInTheDocument();
    expect(screen.queryByText(/Missing gemini_api_key/)).not.toBeInTheDocument();
    expect(screen.getByText('未重排')).toBeInTheDocument();
    expect(screen.getByText('本次 LLM 重排失败或未返回判断，当前展示的是本地因子评分结果。')).toBeInTheDocument();
    expect(screen.getByText('LLM 元数据未返回')).toBeInTheDocument();
    expect(screen.getAllByText('未返回（LLM 已降级）')).toHaveLength(2);
  });

  // 用例 17：snapshot 降级 warning 与 sourceError 内容相同时，应去重只展示一次，
  // 且本地化为中文「数据源降级：tushare（...）」，不展示原始英文错误
  it('deduplicates AlphaSift snapshot fallback warnings and source errors', async () => {
    getAlphaSiftStatus.mockResolvedValueOnce({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    screenStocks.mockResolvedValueOnce({
      enabled: true,
      candidates: [
        {
          rank: 1,
          code: '601919',
          name: '中远海控',
          score: 82.88,
          llmScore: 82,
          riskLevel: 'low',
          raw: {},
        },
      ],
      candidateCount: 1,
      llmRanked: true,
      warnings: ['Snapshot source fallback: tushare: tushare trade_cal returned no open trading days'],
      sourceErrors: ['tushare: tushare trade_cal returned no open trading days'],
    });

    render(<StockScreeningPage />);

    expect(await screen.findByText('选股已开启')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /运行选股/ }));

    expect(await screen.findByText('AlphaSift 提示')).toBeInTheDocument();
    expect(screen.getAllByText('数据源降级：tushare（交易日历暂无可用开市日）')).toHaveLength(1);
    expect(screen.queryByText(/trade_cal returned no open trading days/)).not.toBeInTheDocument();
  });

  // 用例 18：超长的源诊断信息（含 URL/异常堆栈）应被净化并本地化，alert 容器限制宽度（max-w-full），
  // 不展示 HTTPConnectionPool、URL、RemoteDisconnected 等原始细节
  it('sanitizes long AlphaSift source diagnostics and keeps the alert constrained', async () => {
    getAlphaSiftStatus.mockResolvedValueOnce({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    screenStocks.mockResolvedValueOnce({
      enabled: true,
      candidates: [
        {
          rank: 1,
          code: '600016',
          name: '民生银行',
          score: 80.12,
          raw: {},
        },
      ],
      candidateCount: 1,
      llmRanked: true,
      warnings: [
        "Snapshot source fallback: efinance: HTTPConnectionPool(host='push2.eastmoney.com', port=80): Max retries exceeded with url: /api/qt/clist/get?pn=1&pz=200&po=1&fields=f12%2Cf14%2Cf2%2Cf3 (Caused by ProtocolError('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))",
        "Snapshot source fallback: akshare_em: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))",
      ],
    });

    render(<StockScreeningPage />);

    expect(await screen.findByText('选股已开启')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /运行选股/ }));

    const efinanceWarning = await screen.findByText('数据源降级：efinance（网络连接中断）');
    const alert = efinanceWarning.closest('[role="alert"]');
    expect(alert).toHaveClass('max-w-full');
    expect(efinanceWarning).toBeInTheDocument();
    expect(screen.getByText('数据源降级：akshare_em（网络连接中断）')).toBeInTheDocument();
    expect(screen.queryByText(/HTTPConnectionPool/)).not.toBeInTheDocument();
    expect(screen.queryByText(/\/api\/qt\/clist\/get/)).not.toBeInTheDocument();
    expect(screen.queryByText(/RemoteDisconnected/)).not.toBeInTheDocument();
  });

  // 用例 19：展示 HRS 增强结果——行情摘要、新闻、增强计数元数据；
  // 当 HRS 新闻不可用时也应展示对应提示
  it('shows HRS enrichment summary, news, and enrichment metadata', async () => {
    getAlphaSiftStatus.mockResolvedValueOnce({
      enabled: true,
      available: true,
      installSpecIsDefault: true,
    });
    screenStocks.mockResolvedValueOnce({
      enabled: true,
      candidates: [
        {
          rank: 1,
          code: '600519',
          name: '贵州茅台',
          score: 91.2,
          reason: 'AlphaSift pick',
          hrsAnalysisSummary: 'HRS行情：现价 1688，涨跌幅 1.2%；HRS新闻：贵州茅台最新公告',
          hrsNews: [{ title: '贵州茅台最新公告', source: '测试源' }],
          hrsContext: {
            enriched: true,
            warnings: ['stock_news_unavailable'],
          },
          raw: {},
        },
      ],
      candidateCount: 1,
      hrsEnrichment: {
        enabled: true,
        requestedCount: 1,
        enrichedCount: 1,
      },
    });

    render(<StockScreeningPage />);

    expect(await screen.findByText('选股已开启')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /运行选股/ }));

    // 断言：增强计数「1 / 1」，且展示行情摘要、新闻列表、增强提示（含 stock_news_unavailable 警告）
    expect(await screen.findByText('HRS增强：1 / 1')).toBeInTheDocument();

    expect(screen.getByText('HRS 增强摘要')).toBeInTheDocument();
    expect(screen.getByText(/HRS行情：现价 1688/)).toBeInTheDocument();
    expect(screen.getByText('HRS 新闻')).toBeInTheDocument();
    expect(screen.getByText('贵州茅台最新公告')).toBeInTheDocument();
    expect(screen.getByText('HRS 增强提示')).toBeInTheDocument();
    expect(screen.getByText('stock_news_unavailable')).toBeInTheDocument();
  });
});
