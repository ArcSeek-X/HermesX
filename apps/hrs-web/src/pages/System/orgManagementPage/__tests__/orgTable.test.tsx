/** 组织树表测试：空数据走组件默认空态，分页控件始终渲染。 */

import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { OrgTable } from '../components/orgTable';

vi.mock('@/contexts/UiLanguageContext', () => ({ useUiLanguage: () => ({ t: (messageKey: string) => messageKey }) }));

it('renders default empty state and keeps pagination controls when no organizations', () => {
  const tableProps = {
    orgTableData: { list: [], total: 0, pages: 0, pageNum: 1, pageSize: 10 },
    onPageChange: vi.fn(),
    onAddChild: vi.fn(),
    onEditOrganization: vi.fn(),
    onDeleteOrganization: vi.fn(),
    isOrgFetchingState: false,
    areOrganizationActionsDisabled: false,
  };

  render(<OrgTable {...tableProps} />);
  expect(screen.getByText('暂无数据')).toBeInTheDocument();
  expect(screen.getByText('上一页')).toBeInTheDocument();
  expect(screen.getByText('下一页')).toBeInTheDocument();
});
