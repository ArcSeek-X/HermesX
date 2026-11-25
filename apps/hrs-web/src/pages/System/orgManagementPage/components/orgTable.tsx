/**
 * 组织管理树表：当前页组织树 + 根组织分页，支持展开/折叠与行内增删改。
 * 表体是树形结构（treeColumnKey=name），展开态由 Table 内部默认管理，分页由页面 hook 管理。
 */

import { Plus, Pencil, Trash2 } from 'lucide-react';
import { AnimCard } from '@components';
import { Table, type TableColumnDef } from '@components/basic/Table';
import { Chip } from '@components/basic/Chip';
import { HrsButton } from '@components/basic/HrsButton';
import { Tooltip } from '@components/basic/Tooltip';
import { useUiLanguage } from '../../../../contexts/UiLanguageContext';
import type { OrganizationNodeDef, OrganizationPageDef } from '../../../../types/systemOrganization';
import { flattenOrgNodeDataFn } from '../utils/organizationTree';

interface OrgTableProps {
  /** 当前页数据：list 为组织树根节点，total/pages 为分页统计 */
  orgTableData: OrganizationPageDef;
  /** 分页页码变化回调 */
  onPageChange: (organizationPageNum: number) => void;
  /** 新增子组织 */
  onAddChild: (organization: OrganizationNodeDef) => void;
  /** 编辑组织 */
  onEditOrganization: (organization: OrganizationNodeDef) => void;
  /** 删除组织 */
  onDeleteOrganization: (organization: OrganizationNodeDef) => void;
  /** 查询进行中 */
  isOrgFetchingState: boolean;
  /** 增删改进行中，禁用行内操作按钮 */
  areOrganizationActionsDisabled: boolean;
}

export function OrgTable(props: OrgTableProps) {
  const { t } = useUiLanguage();

  /**
   * 构造纯文本列：超长内容用 tooltip 展示，空值显示破折号。
   *
   * @param fieldName 渲染的组织字段名
   * @param title 列标题文案
   * @param width 列最小宽度与默认宽度
   * @returns 对应字段的表格列定义
   */
  const buildTextColumn = (
    fieldName: 'code' | 'nature' | 'type' | 'leader' | 'phone' | 'email',
    title: string,
    width: number,
  ): TableColumnDef<OrganizationNodeDef> => ({
    key: fieldName,
    title,
    minWidth: width,
    defaultWidth: width,
    render: organization => (
      <Tooltip content={organization[fieldName]}>
        <span className="block truncate">{organization[fieldName] || '—'}</span>
      </Tooltip>
    ),
  });

  const columns: TableColumnDef<OrganizationNodeDef>[] = [
    {
      key: 'name',
      title: t('orgManagement.field.name'),
      minWidth: 230,
      defaultWidth: 260,
      isRowHeader: true,
      fixed: 'left',
      render: organization => (
        <div className="min-w-0">
          <span className="block truncate font-medium">{organization.name}</span>
          {organization.shortName && (
            <span className="block truncate text-xs text-muted-text">{organization.shortName}</span>
          )}
        </div>
      ),
    },
    {
      key: 'status',
      title: t('orgManagement.field.status'),
      minWidth: 90,
      defaultWidth: 90,
      render: organization => (
        <Chip size="xs" color={organization.status === 1 ? 'success' : 'default'} variant="soft">
          {t(organization.status === 1 ? 'orgManagement.enabled' : 'orgManagement.disabled')}
        </Chip>
      ),
    },

    buildTextColumn('nature', t('orgManagement.field.nature'), 110),
    buildTextColumn('type', t('orgManagement.field.type'), 110),
    buildTextColumn('leader', t('orgManagement.field.leader'), 110),
    buildTextColumn('phone', t('orgManagement.field.phone'), 150),
    buildTextColumn('email', t('orgManagement.field.email'), 190),
    buildTextColumn('code', t('orgManagement.field.code'), 170),
    {
      key: 'organizationActions',
      title: t('orgManagement.actions'),
      minWidth: 130,
      defaultWidth: 130,
      fixed: 'right',
      render: organization => (
        <div className="flex items-center gap-1">
          <Tooltip content={t('orgManagement.addChild')}>
            <HrsButton
              className="text-foreground-soft"
              size="xxs"
              variant="ghost"
              aria-label={t('orgManagement.addChild')}
              isDisabled={props.areOrganizationActionsDisabled}
              onClick={() => props.onAddChild(organization)}
            >
              <Plus size={14} />
            </HrsButton>
          </Tooltip>
          <Tooltip content={t('orgManagement.edit')}>
            <HrsButton
              className="text-foreground-soft"
              size="xxs"
              variant="ghost"
              aria-label={t('orgManagement.edit')}
              isDisabled={props.areOrganizationActionsDisabled}
              onClick={() => props.onEditOrganization(organization)}
            >
              <Pencil size={14} />
            </HrsButton>
          </Tooltip>
          <Tooltip content={t('orgManagement.delete')}>
            <HrsButton
              className="text-foreground-soft"
              size="xxs"
              variant="ghost"
              aria-label={t('orgManagement.delete')}
              isDisabled={props.areOrganizationActionsDisabled}
              onClick={() => props.onDeleteOrganization(organization)}
            >
              <Trash2 size={14} />
            </HrsButton>
          </Tooltip>
        </div>
      ),
    },
  ];

  return (
    <AnimCard
      aria-label={t('orgManagement.structure')}
      aria-busy={props.isOrgFetchingState}
      className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl bg-elevated"
    >
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-subtle px-4 py-3 text-sm">
        <h2 className="font-semibold text-foreground">{t('orgManagement.structure')}</h2>
        <span role="status" className="text-xs text-muted-text">
          {props.isOrgFetchingState
            ? t('orgManagement.fetching')
            : t('orgManagement.counts', {
              roots: props.orgTableData.total,
              nodes: flattenOrgNodeDataFn(props.orgTableData.list).length,
            })}
        </span>
      </div>

      <Table
        rows={props.orgTableData.list}
        columns={columns}
        rowKey="organizationId"
        treeColumnKey="name"
        selectionMode="none"
        fillHeight
        wrapperClassName="min-h-80"
        isLoading={props.isOrgFetchingState}
        pagination={{ ...props.orgTableData, onPageChange: props.onPageChange }}
      />
    </AnimCard>
  );
}
