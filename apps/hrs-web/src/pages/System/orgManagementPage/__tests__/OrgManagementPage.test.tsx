/**
 * 组织管理页集成测试：查询/操作失败只通过 Toast 提示，不在页面内重复展示横幅。
 * 覆盖 Toast 重试、StrictMode 下不重复、候选树加载失败不打开编辑弹窗。
 */

import { StrictMode } from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { Toast, dismissAllToasts } from '@components/basic/Toast';
import { organizationApi, OrganizationApiError } from '@/api/system/organization';
import OrgManagementPage from '../orgManagementPage';

const connectionMessage = '无法读取 system 组织接口，请检查服务及路由转发。写入超时时请先重新查询核对结果，勿重复提交。';
const emptyPage = { list: [], total: 0, pages: 0, pageNum: 1, pageSize: 10 };
const organizationView = () => (
  <StrictMode>
    <MemoryRouter initialEntries={['/system/orgManagement']}>
      <OrgManagementPage />
      <Toast />
    </MemoryRouter>
  </StrictMode>
);

afterEach(() => {
  cleanup();
  dismissAllToasts();
  vi.restoreAllMocks();
});

it('shows a single floating error without a page banner and allows retry from the Toast', async () => {
  const queryOrganizations = vi.spyOn(organizationApi, 'queryOrganizations')
    .mockRejectedValueOnce(new OrganizationApiError('SERVICE_UNAVAILABLE', 'unavailable'))
    .mockResolvedValue(emptyPage);
  const { container, rerender } = render(organizationView());

  const errorDescription = await screen.findByText(connectionMessage);
  expect(errorDescription.closest('.hrs-toast')).not.toBeNull();
  expect(container.querySelector('main')).not.toContainElement(errorDescription);
  expect(container.querySelector('[role="alert"]')).toBeNull();
  expect(document.querySelectorAll('.hrs-toast')).toHaveLength(1);

  // StrictMode 重渲染不应重复弹 Toast，也不应重复发起查询
  rerender(organizationView());
  expect(document.querySelectorAll('.hrs-toast')).toHaveLength(1);
  expect(queryOrganizations).toHaveBeenCalledTimes(1);

  // 点击 Toast 重试后错误消失，回到空数据状态
  fireEvent.click(screen.getByRole('button', { name: '重试' }));
  await screen.findByText('暂无数据');
  expect(queryOrganizations).toHaveBeenCalledTimes(2);
  expect(document.querySelectorAll('.hrs-toast')).toHaveLength(0);
});

it('also uses a Toast when parent candidates cannot be loaded before opening the editor', async () => {
  vi.spyOn(organizationApi, 'queryOrganizations').mockResolvedValue(emptyPage);
  vi.spyOn(organizationApi, 'getParentCandidates')
    .mockRejectedValue(new OrganizationApiError('SERVICE_UNAVAILABLE', 'unavailable'));
  const { container, unmount } = render(organizationView());
  await screen.findByText('暂无数据');

  // 候选树加载失败时只提示，不打开编辑弹窗
  fireEvent.click(screen.getByRole('button', { name: '新增组织' }));
  const errorDescription = await screen.findByText(connectionMessage);
  expect(errorDescription.closest('.hrs-toast')).not.toBeNull();
  expect(container.querySelector('main')).not.toContainElement(errorDescription);
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

  unmount();
  await waitFor(() => expect(document.querySelectorAll('.hrs-toast')).toHaveLength(0));
});
