import { describe, expect, it } from 'vitest';
import { buildOrgFilterDataFn, createEmptyOrgWriteDataFn, createEmptyOrgSearchDataFn, buildOrgParentOptionDataFn } from '../utils/organizationTree';
import type { OrganizationNodeDef } from '@/types/systemOrganization';

function organization(organizationId: number, enterpriseId: number | null, children: OrganizationNodeDef[] = []): OrganizationNodeDef {
  return { ...createEmptyOrgWriteDataFn(), organizationId, enterpriseId, children, name: `组织${organizationId}`, ancestors: '', createBy: 'manager', updateBy: 'manager', createTime: '', updateTime: '' };
}
describe('organization tree derivations', () => {
  it('keeps disabled status as numeric zero and types as an array', () => {
    expect(buildOrgFilterDataFn({ ...createEmptyOrgSearchDataFn(), organizationName: '  研发 ', organizationTypes: ['1', '2'], organizationStatus: '0' })).toEqual([
      { fieldName: 'name', comparison: 'LIKE', fieldValue: '研发' }, { fieldName: 'type', comparison: 'IN', fieldValue: ['1', '2'] },
      { fieldName: 'status', comparison: 'EQUAL', fieldValue: 0 },
    ]);
  });
  it('excludes self, every descendant and other enterprises from edit candidates', () => {
    const tree = [organization(1, 100, [organization(2, 100, [organization(3, 100)])]), organization(4, 200), organization(5, 100)];
    expect(buildOrgParentOptionDataFn(tree, 2, 100).map(candidate => candidate.key)).toEqual(['1', '5']);
  });
});
