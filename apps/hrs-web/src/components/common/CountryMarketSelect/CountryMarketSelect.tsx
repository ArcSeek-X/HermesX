/**
 * CountryMarketSelect
 * 国家 / 市场下拉控件：将国家字典渲染为「国旗 + 国名」的单选 / 多选列表，支持拼音分组或平铺。
 *
 * 设计要点：
 * - 数据解耦：仅依赖 `options: CountryMarketOptionDef[]` 入参，不耦合具体业务。
 * - 单选 / 多选统一对外契约：`value` / `onChange` 恒为 `string[]`（单选为 0 或 1 个元素），降低调用方心智负担。
 * - 空数组语义 = 「全部 / 未选」：多选表示不筛选，单选表示未选择并显示 placeholder。
 */

import { memo, useMemo } from 'react';
import { pinyin } from 'pinyin-pro';
import { HrsSelect, type HrsSelectDataSourceDef, type HrsSelectOptionDef, type HrsSelectSize } from '../../basic/HrsSelect';
import type { CountryMarketOptionDef } from './types';

/** 取不到拼音首字母（非中文名）的国家归入此分组，排在 A-Z 之后 */
const OTHER_COUNTRY_GROUP = '#';

/** 国名拼音首字母（A~Z），用于分组；取不到时归 `#` 组 */
function pinyinInitialOf(name: string): string {
  const [initial = ''] = pinyin(name, { pattern: 'first', toneType: 'none', type: 'array' });
  const letter = initial.charAt(0).toUpperCase();
  return /[A-Z]/.test(letter) ? letter : OTHER_COUNTRY_GROUP;
}

export interface CountryMarketSelectProps {
  /** 国家字典（输入）：来自数据源，如 `useLiveCalendarCountries`；必填 */
  options: CountryMarketOptionDef[];
  /** 已选国家 ID 列表（受控）：`string[]`，元素为各 `countryMarketId`；`[]` 表示全部 / 未选 */
  value: string[];
  /** 选中变更回调：回传 `string[]`（元素为 `countryMarketId`） */
  onChange: (next: string[]) => void;
  /** 是否多选，默认 false（单选） */
  multiple?: boolean;
  /** 展示形态：'A-Z'（默认，按拼音分组）| 'flattening'（平铺不分组） */
  groupBy?: 'A-Z' | 'flattening';
  /** 未选占位文案，默认「全部国家/地区」 */
  placeholder?: string;
  /** 尺寸档位（透传 HrsSelect），默认 'sm' */
  size?: HrsSelectSize;
  /** 弹层追加 className；默认限高 400px 并自身滚动 */
  popoverClassName?: string;
  /** 根节点 className */
  className?: string;
}

export const CountryMarketSelect = memo(
  ({
    options,
    value,
    onChange,
    multiple = false,
    groupBy = 'A-Z',
    placeholder = '全部国家/地区',
    size = 'sm',
    popoverClassName = 'max-h-[400px]! overflow-y-auto',
    className,
  }: CountryMarketSelectProps) => {
    // 国家 ID → 国旗地址，渲染选项时按 key 直查，避免逐项遍历 options
    const marketFlagMap = useMemo(() => {
      const map = new Map<string, string>();
      for (const country of options) {
        if (country.flagUri) map.set(country.countryMarketId, country.flagUri);
      }
      return map;
    }, [options]);

    // 按全拼排序后，依 groupBy 输出分组或平铺的 HrsSelect 数据源
    const countryDataSource = useMemo<HrsSelectDataSourceDef>(() => {
      const pinyinSorted = [...options]
        .map((country) => ({
          country,
          initial: pinyinInitialOf(country.countryMarketName),
          full: pinyin(country.countryMarketName, { toneType: 'none' }),
        }))
        .sort((a, b) =>
          a.initial === b.initial ? a.full.localeCompare(b.full) : a.initial.localeCompare(b.initial),
        );

      const flatOptions: HrsSelectOptionDef[] = pinyinSorted.map((item) => ({
        key: item.country.countryMarketId,
        label: item.country.countryMarketName,
      }));

      if (groupBy === 'flattening') {
        return [{ key: 'country-all-flat', options: flatOptions }];
      }

      // 按首字母聚合分组，# 组置后
      const grouped = new Map<string, HrsSelectOptionDef[]>();
      pinyinSorted.forEach((item, index) => {
        const opts = grouped.get(item.initial);
        if (opts) opts.push(flatOptions[index]);
        else grouped.set(item.initial, [flatOptions[index]]);
      });

      return [...grouped.entries()]
        .sort(([a], [b]) =>
          a === OTHER_COUNTRY_GROUP ? 1 : b === OTHER_COUNTRY_GROUP ? -1 : a.localeCompare(b),
        )
        .map(([initial, opts]) => ({ key: `country-group-${initial}`, title: initial, options: opts }));
    }, [options, groupBy]);

    const renderCountryOption = (option: HrsSelectOptionDef) => {
      const flagUri = marketFlagMap.get(String(option.key));
      return (
        <span className="flex min-w-0 items-center gap-1.5">
          {flagUri ? (
            <img className="h-3 w-4 shrink-0 object-cover" src={flagUri} alt="" aria-hidden />
          ) : null}
          <span className="truncate text-xs">{option.label}</span>
        </span>
      );
    };

    return (
      <HrsSelect
        size={size}
        selectionMode={multiple ? 'multiple' : 'single'}
        options={countryDataSource}
        placeholder={placeholder}
        value={multiple ? value : (value[0] ?? null)}
        onChange={(next) => {
          if (multiple) {
            onChange(Array.isArray(next) ? next.map(String) : []);
          } else {
            onChange(next == null ? [] : [String(next)]);
          }
        }}
        renderItem={renderCountryOption}
        className={className}
        // ! 为 Tailwind v4 的 important 修饰符，压制 react-aria Popover 注入的 inline max-height
        popoverClassName={popoverClassName}
      />
    );
  },
);
CountryMarketSelect.displayName = 'CountryMarketSelect';
