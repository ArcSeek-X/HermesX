/**
 * CountryMarketSelect.tsx
 * ------------------------------------------------------------
 * 国家 / 市场下拉控件：把一组国家字典（含国旗、国名）渲染为带拼音分组、
 * 带国旗的选项列表，供任意需要「按国家 / 市场筛选或单选」的场景复用
 * （如消息日历筛选、行情筛选、单一市场选择等）。
 *
 * 设计要点：
 * 1. **数据解耦**：仅依赖 `options: CountryMarketOptionDef[]` 入参，不耦合任何具体业务，
 *    调用方自行从数据源（如 `useLiveCalendarCountries`）获取后传入即可。
 * 2. **单选 / 多选切换**：`multiple` 控制是否多选，默认 `false`（单选）。
 *    复用底层 HrsSelect 的 `selectionMode`，对外 `value` / `onChange` 始终统一为
 *    `string[]`（单选时为 0 或 1 个元素），降低调用方的心智负担。
 * 3. **分组与排序**：通过 `groupBy` 控制选项展示形态（默认 `'A-Z'`）。
 *    - `'A-Z'`：按国名拼音首字母 A~Z 分组（组内按全拼排序），取不到拼音首字母的国家归入
 *      `#` 组并排在最后，便于海量国家时快速定位。
 *    - `'flattening'`：完全平铺，不分组、不渲染组标题，所有选项按全拼排序后连续展示。
 * 4. **空的语义 = 全部 / 未选**：`value` 为 `string[]`；空数组代表「全部国家 / 地区」
 *    （多选，不筛选）或「未选择」（单选，显示 placeholder）；多选直接映射为国家 ID 列表上抛。
 * 5. **国旗渲染**：选项统一渲染「国旗 + 国名」；无国旗的国家不渲染占位块，避免空白。
 * 6. **弹层限高**：默认弹层限高 400px 并自行滚动（含 `!important` 压制 react-aria
 *    注入的 inline max-height），保证国家数量大时仍可滚动查看。
 *
 * 数据契约（输入 / 输出格式）：
 * - 输入 `options`：国家字典数组 `CountryMarketOptionDef[]`，单项形如：
 *   ```ts
 *   {
 *     countryMarketId:    'cn',                       // 唯一键：同时作为选项 key 与回传 ID
 *     countryMarketName:  '中国',                      // 选项显示文案，按拼音分组排序
 *     currency:     'CNY',
 *     currencyName: '人民币',
 *     flagUri:      'https://.../flags/cn.svg',  // 国旗地址，可空（空时不渲染国旗占位）
 *   }
 *   ```
 * - 输入 `value`：已选国家 ID 数组 `string[]`（元素即各 `countryMarketId`）。
 *   - 多选：可含多个 ID；传 `[]` 表示「全部 / 不筛选」。
 *   - 单选（`multiple=false`）：长度恒为 0 或 1，取首个元素作为当前选中项；`[]` 表示未选择。
 * - 输出 `onChange(next)`：用户每次增删选择后回传 `string[]`（元素为 `countryMarketId`）。
 *   - 多选：回传当前全部选中 ID；清空时回传 `[]`（= 全部）。
 *   - 单选：回传 0 或 1 个元素；取消选中时回传 `[]`（= 未选择）。
 *
 * @author Lensgcx (GaoCangxiong)
 */

import { memo, useMemo } from 'react';
import { pinyin } from 'pinyin-pro';
import { HrsSelect, type HrsSelectDataSourceDef, type HrsSelectOptionDef, type HrsSelectSize } from '../../basic/HrsSelect';

/** 国家字典数据契约：国家下拉控件的输入项，同时是 `value` / `onChange` 的 ID 来源。
 *  字段为后端 snake_case 经 api 层归一化后的 camelCase。 */
export interface CountryMarketOptionDef {
    /** 国家唯一标识（如 'cn' / 'us'），同时作为下拉选项 key 与回传的选中 ID */
    countryMarketId: string;
    /** 国家 / 地区中文名称（如 '中国' / '美国'），作为选项显示文案并用于拼音分组排序 */
    countryMarketName: string;
    /** 货币 ISO 代码（如 'CNY' / 'USD'），可选展示信息 */
    currency: string;
    /** 货币中文名称（如 '人民币' / '美元'），与 `currency` 配套展示 */
    currencyName: string;
    /** 国旗图片地址（可为空）：非空时选项左侧渲染 `<img>` 国旗；为空则不渲染占位块，仅贴左显示国名 */
    flagUri: string;
}

/** 拼音首字母取不到（非中文名）的国家归入该分组，排在 A-Z 之后 */
const OTHER_COUNTRY_GROUP = '#';

/**
 * 取国名拼音首字母（A~Z）用于下拉分组；非中文名取不到首字母时归入 `#` 组。
 * @param name 国家名称（如「中国」「United States」）
 * @returns 首字母大写；取不到时返回 `#`
 */
function pinyinInitialOf(name: string): string {
    const [initial = ''] = pinyin(name, { pattern: 'first', toneType: 'none', type: 'array' });
    const letter = initial.charAt(0).toUpperCase();
    return /[A-Z]/.test(letter) ? letter : OTHER_COUNTRY_GROUP;
}

/** CountryMarketSelect 组件属性 */
export interface CountryMarketSelectProps {
    /**
     * 国家字典（输入）：来自数据源，如 `useLiveCalendarCountries`。
     * 类型 `CountryMarketOptionDef[]`；必填。
     * 其中 `countryMarketId` 是唯一键（同时作为下拉选项的 key 与回传 ID），
     * `countryMarketName` 为选项文案并按拼音首字母分组，`flagUri` 可空（空时不渲染国旗）。
     */
    options: CountryMarketOptionDef[];
    /**
     * 已选国家 ID 列表（输入，受控）：`string[]`，元素为各 `countryMarketId`。
     * - 多选：可含多个 ID；`[]` = 全部 / 不筛选。
     * - 单选（`multiple=false`）：长度恒为 0 或 1，取首个元素作为当前选中；`[]` = 未选择。
     */
    value: string[];
    /**
     * 选中值变更回调（输出）：用户每次增删选择后触发。
     * 回传 `string[]`（元素为 `countryMarketId`）：
     * - 多选：当前全部选中 ID；清空时 `[]`（= 全部，与输入 `[]` 对称）。
     * - 单选：0 或 1 个元素；取消选中时 `[]`（= 未选择）。
     */
    onChange: (next: string[]) => void;
    /**
     * 是否多选：默认 `false`（单选）。
     * - `false`：单选，触发器展示单一选中项，再次点击可取消。
     * - `true`：多选，触发器以「首个 + N」折叠标签展示，空选即「全部」。
     */
    multiple?: boolean;
    /**
     * 选项展示形态，控制是否按拼音分组：
     * - `'A-Z'`（默认）：按国名拼音首字母 A~Z 分组，无首字母的归入 `#` 组置后。
     * - `'flattening'`：完全平铺，不分组、不渲染组标题，所有选项按全拼排序后连续展示。
     */
    groupBy?: 'A-Z' | 'flattening';
    /** 未选时的占位文案，默认「全部国家/地区」 */
    placeholder?: string;
    /** 尺寸档位（透传 HrsSelect），默认 'sm' */
    size?: HrsSelectSize;
    /** 下拉弹层追加的 className；默认限高 400px 并由弹层自身滚动 */
    popoverClassName?: string;
    /** 根节点追加的 className */
    className?: string;
}

/**
 * 国家 / 市场下拉：将国家字典分组渲染为「国旗 + 国名」的单选 / 多选列表。
 * 详见文件头设计要点与数据契约；典型用法见 {@link CountryMarketSelectProps}。
 */
export const CountryMarketSelect = memo(
    ({
        options,
        value,
        onChange,
        multiple = false,
        groupBy = 'A-Z',
        placeholder = '全部国家/地区',
        size = 'sm',
        popoverClassName = 'countrySelectPopover max-h-[400px]! overflow-y-auto',
        className,
    }: CountryMarketSelectProps) => {
        // 国家 ID → 国旗 URI 映射，供选项渲染时按 key 快速取用，避免逐项遍历 options
        const flagUriByCountryMarketId = useMemo(() => {
            const map = new Map<string, string>();
            for (const country of options) {
                if (country.flagUri) map.set(country.countryMarketId, country.flagUri);
            }
            return map;
        }, [options]);

        // 选项构建：先算出「按全拼排序后的扁平选项」，再按 groupBy 决定分组或平铺，
        // 得到 HrsSelect 数据源 `countryGroups`，直接透传给底层 HrsSelect 的 options。
        // 注：空选即代表「全部 / 未选」，故无需单列「全部」选项。
        const countryGroups = useMemo<HrsSelectDataSourceDef>(() => {
            const ordered = [...options].map((country) => ({
                country,
                initial: pinyinInitialOf(country.countryMarketName),
                full: pinyin(country.countryMarketName, { toneType: 'none' }),
            }));
            ordered.sort((a, b) =>
                a.initial === b.initial
                    ? a.full.localeCompare(b.full)
                    : a.initial.localeCompare(b.initial),
            );

            // 排序后的扁平选项，两种展示模式共用
            const flatOptions: HrsSelectOptionDef[] = ordered.map((item) => ({
                key: item.country.countryMarketId,
                label: item.country.countryMarketName,
            }));

            // 扁平平铺：单一分组、不渲染组标题；作为首元素不插入分隔线
            if (groupBy === 'flattening') {
                return [{ key: 'country-all-flat', options: flatOptions }];
            }

            // 默认 A-Z 分组：按首字母聚合为分组，每组下挂该字母对应的国家选项
            const groups = new Map<string, HrsSelectOptionDef[]>();
            for (const item of ordered) {
                const opts = groups.get(item.initial);
                if (opts) {
                    opts.push({ key: item.country.countryMarketId, label: item.country.countryMarketName });
                } else {
                    groups.set(item.initial, [
                        { key: item.country.countryMarketId, label: item.country.countryMarketName },
                    ]);
                }
            }

            // 分组排序：A-Z 升序，# 组永远置后，使非中文国家落在列表末尾
            return [...groups.entries()]
                .sort(([a], [b]) =>
                    a === OTHER_COUNTRY_GROUP ? 1 : b === OTHER_COUNTRY_GROUP ? -1 : a.localeCompare(b),
                )
                .map(([initial, opts]) => ({
                    key: `country-group-${initial}`,
                    title: initial,
                    options: opts,
                }));
        }, [options, groupBy]);

        // 单选项渲染：国旗 + 国名；无国旗不渲染占位块，直接贴左显示国名，避免空白
        const renderCountryOption = (option: HrsSelectOptionDef) => {
            const flagUri = flagUriByCountryMarketId.get(String(option.key));
            return (
                <span className="flex min-w-0 items-center gap-1.5">
                    {flagUri ? (
                        <img className="h-3 w-4 shrink-0 object-cover" src={flagUri} alt="countryFlag" aria-hidden />
                    ) : null}
                    <span className="truncate text-xs">{option.label}</span>
                </span>
            );
        };

        return (
            <HrsSelect
                size={size}
                // 单选 / 多选切换：直接复用底层 HrsSelect 的 selectionMode
                selectionMode={multiple ? 'multiple' : 'single'}
                options={countryGroups}
                placeholder={placeholder}
                // 对外 value 统一为 string[]；单选时取首个元素（无则 null）透传给底层
                value={multiple ? value : (value[0] ?? null)}
                onChange={(next) => {
                    if (multiple) {
                        // 多选：底层回传 Key[]，归一化为 string[]
                        const nextArr = Array.isArray(next)
                            ? (next as Array<string | number>)
                            : [];
                        // 空数组 = 全部（不筛选）；多选直接映射为国家 ID 列表
                        onChange(nextArr.map(String));
                    } else {
                        // 单选：底层回传单个 Key 或 null，包成 0/1 长度的 string[]
                        onChange(next == null ? [] : [String(next)]);
                    }
                }}
                renderItem={renderCountryOption}
                className={className}
                // 滚动容器是弹层本身（.select__popover 自带 overflow-y-auto），list-box 不可滚动，
                // 故仅限高弹层到 ~400px，列表超出时由弹层滚动；末尾 ! 是 Tailwind v4 的
                // !important 修饰符，压制 react-aria Popover 注入的 inline max-height
                // （按视口自动算的高度），保证 400px 真的生效
                popoverClassName={popoverClassName}
            />
        );
    },
);
CountryMarketSelect.displayName = 'CountryMarketSelect';
