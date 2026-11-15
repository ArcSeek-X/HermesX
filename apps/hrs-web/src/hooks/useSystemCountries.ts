/**
 * @file useSystemCountries.ts
 * @description 系统数据字典 Hook：拉取国家字典（/api/v1/system/countries）。
 *   国家信息低频静态，落库后由 system 字典服务统一供给，与 live-calendar 解耦；
 *   供国家选择器、行情/日历筛选等需要国家元数据的场景复用同一数据源。
 * @author Lensgcx (GaoCangxiong)
 */

import { useCallback, useEffect, useState } from 'react';
import { getSystemCountries } from '../api/systemCountries';
import type { CountryMarketOptionDef } from '@components';

interface SystemCountriesState {
  /** 国家字典列表：国旗、名称、货币(ISO 代码)等，供国家选择器 / 事件卡片展示 */
  countryOptions: CountryMarketOptionDef[];
  /** 降级标记：后端字典缺失或上游失败时置 true */
  countriesDegraded: boolean;
  /** 首次加载中（数据未就绪） */
  isFetchingCountries: boolean;
  /** 加载失败信息；null 表示成功 */
  countriesError: string | null;
}

export function useSystemCountries(): SystemCountriesState {
  const [countryOptions, setCountryOptions] = useState<CountryMarketOptionDef[]>([]);
  const [countriesDegraded, setCountriesDegraded] = useState(false);
  const [isFetchingCountries, setIsFetchingCountries] = useState(true);
  const [countriesError, setCountriesError] = useState<string | null>(null);

  const fetchCountryDictionary = useCallback(async () => {
    setIsFetchingCountries(true);
    try {
      const result = await getSystemCountries();
      setCountryOptions(result.items);
      setCountriesDegraded(result.degraded);
      setCountriesError(null);
    } catch {
      setCountriesError('国家字典加载失败');
    } finally {
      setIsFetchingCountries(false);
    }
  }, []);

  useEffect(() => {
    void fetchCountryDictionary();
  }, [fetchCountryDictionary]);

  return { countryOptions, countriesDegraded, isFetchingCountries, countriesError };
}
