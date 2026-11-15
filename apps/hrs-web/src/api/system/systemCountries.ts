/**
 * 系统数据字典 API：国家字典读取。
 *
 * 对应后端 `/api/v1/system/countries`（见 documents/product/行情资讯/system_countries.md）：
 * - GET /system/countries  国家字典（DB-first，落库后不再回源）
 *
 * 约定：后端返回 snake_case，本层统一 normalize 为 camelCase，避免字段风格泄漏到业务层。
 */

import apiClient from '@/api';
import type { CountryMarketOptionDef } from '@components';

/** 后端返回的原始国家字典条目（snake_case） */
interface RawSystemCountry {
  country_id: string;
  country_name: string;
  currency?: string;
  currency_name?: string;
  flag_uri?: string;
}

function normalizeSystemCountry(raw: RawSystemCountry): CountryMarketOptionDef {
  return {
    countryMarketId: raw.country_id,
    countryMarketName: raw.country_name,
    currency: raw.currency ?? '',
    currencyName: raw.currency_name ?? '',
    flagUri: raw.flag_uri ?? '',
  };
}

/** 查询系统国家字典（DB-first，落库后不再每次回源） */
export async function getSystemCountries(): Promise<{
  items: CountryMarketOptionDef[];
  degraded: boolean;
}> {
  const response = await apiClient.get<{
    items?: RawSystemCountry[];
    degraded?: boolean;
  }>('/api/v1/system/countries');
  const data = response.data ?? {};
  return {
    items: (data.items ?? []).map(normalizeSystemCountry),
    degraded: Boolean(data.degraded),
  };
}
