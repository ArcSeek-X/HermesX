import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useOrgManagement } from '../useOrgManagement';
import { organizationApi } from '@/api/system/organization';
import { createEmptyOrgWriteDataFn } from '@/pages/System/orgManagementPage/utils/organizationTree';
import type { OrganizationNodeDef, OrganizationPageDef } from '@/types/systemOrganization';

vi.mock('@/api/system/organization', () => ({ organizationApi: { queryOrganizations: vi.fn(), getParentCandidates: vi.fn(), getOrganization: vi.fn(),
  createOrganization: vi.fn(), editOrganization: vi.fn(), deleteOrganization: vi.fn() }, OrganizationApiError: class extends Error {} }));
const organizationFixture = (): OrganizationNodeDef => ({ ...createEmptyOrgWriteDataFn(), organizationId: 7, name: '总部', ancestors: '',
  createBy: 'manager', updateBy: 'manager', createTime: '2026-11-24 00:00:00', updateTime: '2026-11-24 00:00:00', children: [] });
const orgTableData = (): OrganizationPageDef => ({ list: [organizationFixture()], total: 1, pages: 1, pageNum: 1, pageSize: 10 });
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(fulfill => { resolve = fulfill; }); return { promise, resolve }; }
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(organizationApi.queryOrganizations).mockResolvedValue(orgTableData());
  vi.mocked(organizationApi.getParentCandidates).mockResolvedValue([organizationFixture()]);
  vi.mocked(organizationApi.getOrganization).mockResolvedValue(organizationFixture());
  vi.mocked(organizationApi.createOrganization).mockResolvedValue(organizationFixture());
});

describe('organization page lifecycle', () => {
  it('ignores an old query response after a newer filter has completed', async () => {
    const initialQuery = deferred<OrganizationPageDef>();
    vi.mocked(organizationApi.queryOrganizations).mockReturnValueOnce(initialQuery.promise);
    const { result } = renderHook(useOrgManagement);
    await waitFor(() => expect(organizationApi.queryOrganizations).toHaveBeenCalledTimes(1));
    act(() => result.current.setOrgSearchDraftFn({ organizationName: '研发', organizationNature: '', organizationTypes: [], organizationStatus: '0' }));
    act(() => result.current.queryOrgTableFn());
    await waitFor(() => expect(result.current.isOrgFetchingState).toBe(false));
    const newerPage = result.current.orgTableData;
    await act(async () => initialQuery.resolve({ ...orgTableData(), list: [] }));
    expect(result.current.orgTableData).toBe(newerPage);
    expect(organizationApi.queryOrganizations).toHaveBeenLastCalledWith({ pageNum: 1, pageSize: 10, filterList: [
      { fieldName: 'name', comparison: 'LIKE', fieldValue: '研发' }, { fieldName: 'status', comparison: 'EQUAL', fieldValue: 0 },
    ] });
  });

  it('uses full candidate/detail data for edits and keeps drafts after a write failure', async () => {
    const existingOrganization = { ...organizationFixture(), nature: 'existing-nature', type: 'existing-type', remark: '不能丢失' };
    vi.mocked(organizationApi.getOrganization).mockResolvedValue(existingOrganization);
    const { result } = renderHook(useOrgManagement);
    await waitFor(() => expect(result.current.orgTableData.total).toBe(1));
    await act(async () => result.current.openOrgEditorDialogFn(organizationFixture()));
    expect(result.current.orgEditorDialogData?.initialFields).toMatchObject({ nature: 'existing-nature', type: 'existing-type', remark: '不能丢失' });
    vi.mocked(organizationApi.editOrganization).mockRejectedValue(new Error('write failed'));
    await act(async () => result.current.submitOrgFormFn(existingOrganization));
    expect(result.current.orgEditorDialogData).not.toBeNull();
    expect(result.current.orgActionErrorData).toBeInstanceOf(Error);
    expect(result.current.isOrgSavingState).toBe(false);
  });

  it('locks duplicate saves and distinguishes a successful write from failed refresh', async () => {
    const pendingSave = deferred<OrganizationNodeDef>();
    vi.mocked(organizationApi.createOrganization).mockReturnValue(pendingSave.promise);
    const { result } = renderHook(useOrgManagement);
    await waitFor(() => expect(result.current.orgTableData.total).toBe(1));
    await act(async () => result.current.openOrgEditorDialogFn());
    act(() => { void result.current.submitOrgFormFn({ ...createEmptyOrgWriteDataFn(), name: '新组织' }); void result.current.submitOrgFormFn({ ...createEmptyOrgWriteDataFn(), name: '新组织' }); });
    expect(organizationApi.createOrganization).toHaveBeenCalledTimes(1);
    vi.mocked(organizationApi.queryOrganizations).mockRejectedValue(new Error('refresh failed'));
    await act(async () => pendingSave.resolve(organizationFixture()));
    await waitFor(() => expect(result.current.orgActionFeedbackCode).toBe('savedRefreshFailed'));
    expect(result.current.orgEditorDialogData).toBeNull();
    expect(result.current.isOrgSavingState).toBe(false);
  });

  it('moves back to the last root page after deleting its last item', async () => {
    const { result } = renderHook(useOrgManagement);
    await waitFor(() => expect(result.current.orgTableData.total).toBe(1));
    vi.mocked(organizationApi.queryOrganizations).mockResolvedValueOnce({ ...orgTableData(), pageNum: 2, total: 11, pages: 2 });
    act(() => result.current.changeOrgTablePageFn(2));
    await waitFor(() => expect(result.current.orgTableData.pageNum).toBe(2));
    vi.mocked(organizationApi.queryOrganizations).mockResolvedValueOnce({ ...orgTableData(), list: [], pageNum: 2 }).mockResolvedValueOnce(orgTableData());
    act(() => result.current.openOrgDeletionFn(organizationFixture()));
    await act(async () => result.current.confirmOrgDeletionFn());
    expect(result.current.orgTableData.pageNum).toBe(1);
    expect(result.current.orgActionFeedbackCode).toBe('deleted');
    expect(organizationApi.queryOrganizations).toHaveBeenLastCalledWith({ pageNum: 1, pageSize: 10, filterList: [] });
  });
});
