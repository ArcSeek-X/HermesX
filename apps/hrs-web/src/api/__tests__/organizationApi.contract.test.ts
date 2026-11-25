import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AxiosError, AxiosHeaders, type AxiosAdapter } from 'axios';
import apiClient, { clearAllApiCache } from '@/api';
import { organizationApi } from '@/api/system/organization';
import { createEmptyOrgWriteDataFn } from '@/pages/System/orgManagementPage/utils/organizationTree';

vi.mock('@/components/basic/Toast/Toast', () => ({ showToast: { danger: vi.fn() } }));
const originalAdapter = apiClient.defaults.adapter;
const adapter = vi.fn<AxiosAdapter>();
const organizationQuery = { pageNum: 1, pageSize: 10, filterList: [] };
const organizationFixture = () => ({ ...createEmptyOrgWriteDataFn(), organizationId: 7, name: '总部', ancestors: '',
  createBy: 'manager', updateBy: 'manager', createTime: '2026-11-24 00:00:00', updateTime: '2026-11-24 00:00:00', children: [] });
let responseBody: unknown;
const wrapResult = (resultData: unknown) => ({ resultCode: '200', resultMsg: '操作成功。', resultData });

beforeEach(() => {
  clearAllApiCache(); adapter.mockReset(); apiClient.defaults.adapter = adapter;
  responseBody = wrapResult({ list: [organizationFixture()], total: 1, pages: 1, pageNum: 1, pageSize: 10 });
  adapter.mockImplementation(async config => ({ data: responseBody, status: 200, statusText: 'OK', headers: {}, config }));
});
afterEach(() => { apiClient.defaults.adapter = originalAdapter; clearAllApiCache(); });

describe('organization common response contract', () => {
  it('sends POST pagination and typed filters without mainSearch or keyword', async () => {
    const filteredQuery = { ...organizationQuery, filterList: [{ fieldName: 'status' as const, comparison: 'EQUAL' as const, fieldValue: 0 as const }] };
    expect((await organizationApi.queryOrganizations(filteredQuery)).list[0].organizationId).toBe(7);
    expect(adapter.mock.calls[0][0]).toMatchObject({ method: 'post', url: '/api/system/organization/list-organization', handleErrorLocally: true });
    expect(JSON.parse(adapter.mock.calls[0][0].data)).toEqual(filteredQuery);
  });

  it('never caches detail and candidate tree reads', async () => {
    responseBody = wrapResult([organizationFixture()]);
    await organizationApi.getParentCandidates(); await organizationApi.getParentCandidates();
    responseBody = wrapResult(organizationFixture());
    await organizationApi.getOrganization(7); await organizationApi.getOrganization(7);
    expect(adapter).toHaveBeenCalledTimes(4);
    expect(adapter.mock.calls.every(([request]) => request.skipCache)).toBe(true);
  });

  it('keeps edit/delete identifiers in JSON, and validates the delete result', async () => {
    responseBody = wrapResult(organizationFixture());
    await organizationApi.editOrganization(7, { ...createEmptyOrgWriteDataFn(), name: '总部' });
    expect(adapter.mock.calls[0][0].url).toBe('/api/system/organization/edit-organization');
    expect(JSON.parse(adapter.mock.calls[0][0].data).organizationId).toBe(7);
    responseBody = wrapResult(true); await organizationApi.deleteOrganization(7);
    expect(adapter.mock.calls[1][0].url).toBe('/api/system/organization/delete-organization');
    expect(JSON.parse(adapter.mock.calls[1][0].data)).toEqual({ organizationId: 7 });
    responseBody = wrapResult(null);
    await expect(organizationApi.deleteOrganization(7)).rejects.toMatchObject({ resultCode: 'INVALID_RESPONSE' });
  });

  it('rejects malformed pagination, duplicate nodes and broken parent links', async () => {
    for (const invalidPage of [
      { list: [], total: 1, pages: 0, pageNum: 1, pageSize: 10 },
      { list: [organizationFixture(), organizationFixture()], total: 2, pages: 1, pageNum: 1, pageSize: 10 },
      { list: [{ ...organizationFixture(), children: [{ ...organizationFixture(), organizationId: 8, parentId: 9 }] }], total: 1, pages: 1, pageNum: 1, pageSize: 10 },
    ]) {
      responseBody = wrapResult(invalidPage);
      await expect(organizationApi.queryOrganizations(organizationQuery)).rejects.toMatchObject({ resultCode: 'INVALID_RESPONSE' });
    }
  });

  it('preserves common business/security codes from HTTP errors', async () => {
    for (const resultCode of ['HAS_CHILDREN', 'CSRF_INVALID', 'UNAUTHENTICATED']) {
      adapter.mockImplementation(async config => { throw new AxiosError('request rejected', 'ERR_BAD_REQUEST', config, undefined,
        { data: { resultCode, resultMsg: '失败', resultData: null }, status: 403, statusText: 'Forbidden', headers: new AxiosHeaders(), config }); });
      await expect(organizationApi.deleteOrganization(7)).rejects.toMatchObject({ resultCode });
    }
  });
});
