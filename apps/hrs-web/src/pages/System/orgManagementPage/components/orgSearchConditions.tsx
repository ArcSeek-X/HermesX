/**
 * 组织管理搜索条件：按名称/性质/类型/状态筛选，触发查询与重置。
 * 新增组织入口在页面 PageHeader 的 rightSlot；性质/类型字典尚未接入，保留禁用占位。
 * 筛选字段的值直接写入表单草稿，只有提交时才由页面发起查询，避免输入过程触发请求。
 */

import { Search, RotateCcw } from 'lucide-react';
import { AnimCard } from '@components';
import { HrsInput } from '@components/basic/HrsInput';
import { HrsSelect } from '@components/basic/HrsSelect';
import { HrsButton } from '@components/basic/HrsButton';
import { useUiLanguage } from '../../../../contexts/UiLanguageContext';
import type { OrganizationSearchDef } from '../../../../types/systemOrganization';

interface OrgSearchConditionsProps {
  /** 输入：页面当前的搜索表单草稿，包含名称/性质/类型/状态四个字段 */
  organizationSearch: OrganizationSearchDef;
  /** 输出：字段变更后回传整份新草稿，由页面更新 store */
  onSearchChange: (organizationSearch: OrganizationSearchDef) => void;
  /** 输出：提交当前草稿发起查询 */
  onQueryOrganizations: () => void;
  /** 输出：清空筛选条件并恢复默认第一页 */
  onResetSearch: () => void;
  /** 输入：查询进行中，提交按钮展示加载态并禁用 */
  isFetchingOrganizations: boolean;
}

export function OrgSearchConditions(props: OrgSearchConditionsProps) {
  const { t } = useUiLanguage();

  return (
    <AnimCard className="min-w-0 shrink-0 !min-h-0 px-3 py-2">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          props.onQueryOrganizations();
        }}
        className="flex w-full min-w-0 items-end gap-3"
      >
        {/* 四个筛选条件放在可横向滚动的网格中，窄屏不挤压右侧按钮 */}
        <div className="min-w-0 flex-1 overflow-x-auto">
          <div className="grid min-w-[34rem] grid-cols-4 items-end gap-3">
            <label className="flex min-w-0 flex-col gap-1 text-sm text-muted-text">
              {t('orgManagement.field.name')}
              <HrsInput
                value={props.organizationSearch.organizationName}
                maxLength={100}
                className="w-full"
                placeholder={t('orgManagement.search.name')}
                onChange={event => props.onSearchChange({
                  ...props.organizationSearch,
                  organizationName: event.target.value,
                })}
              />
            </label>

            {/* 字典接入前禁用，避免提交无意义筛选值 */}
            <HrsSelect
              className="w-full"
              label={t('orgManagement.field.nature')}
              options={[]}
              isDisabled
              placeholder={t('orgManagement.dictionaryPending')}
            />
            <HrsSelect
              className="w-full"
              label={t('orgManagement.field.type')}
              options={[]}
              selectionMode="multiple"
              isDisabled
              placeholder={t('orgManagement.dictionaryPending')}
            />

            <HrsSelect
              className="w-full"
              label={t('orgManagement.field.status')}
              value={props.organizationSearch.organizationStatus}
              options={[
                { key: '', label: t('orgManagement.allStatuses') },
                { key: '1', label: t('orgManagement.enabled') },
                { key: '0', label: t('orgManagement.disabled') },
              ]}
              onChange={organizationStatus => props.onSearchChange({
                ...props.organizationSearch,
                organizationStatus: (organizationStatus ?? '') as OrganizationSearchDef['organizationStatus'],
              })}
            />
          </div>
        </div>

        {/* 查询/重置固定在右侧，不随筛选区滚动 */}
        <div className="ml-auto flex shrink-0 items-center gap-2 whitespace-nowrap">
          <HrsButton type="submit" size="sm" isLoading={props.isFetchingOrganizations}>
            <Search size={16} />
            {t('orgManagement.query')}
          </HrsButton>
          <HrsButton type="button" size="sm" variant="outline" onClick={props.onResetSearch}>
            <RotateCcw size={16} />
            {t('orgManagement.reset')}
          </HrsButton>
        </div>
      </form>
    </AnimCard>
  );
}
