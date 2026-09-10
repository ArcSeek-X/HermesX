/**
 * @file ReportMarkdown.test.tsx
 * @description ReportMarkdown 兼容包装组件的单元测试：覆盖抽屉渲染与面板挂载。
 * @author Lensgcx (GaoCangxiong)
 */
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { historyApi } from '../../../api/history';
import { ReportMarkdown } from '../ReportMarkdown';

vi.mock('../../../api/history', () => ({
  historyApi: {
    getMarkdown: vi.fn(),
  },
}));

describe('ReportMarkdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('uses localized copy labels for English reports', async () => {
    vi.mocked(historyApi.getMarkdown).mockResolvedValue('# Full report');

    render(
      <ReportMarkdown
        recordId={1}
        stockName="Apple"
        stockCode="AAPL"
        reportLanguage="en"
        onClose={() => {}}
      />
    );

    expect(await screen.findByRole('button', { name: 'Copy Markdown Source' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Copy Plain Text' })).toBeInTheDocument();
  });
});
