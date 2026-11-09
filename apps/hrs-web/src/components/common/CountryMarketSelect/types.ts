/**
 * CountryMarketSelect/types.ts
 * 国家 / 市场字典数据契约：CountryMarketSelect 的输入项，也是其 `value` / `onChange` 回传的 ID 来源。
 * 字段为后端 snake_case 经 api 层归一化后的 camelCase。
 */

export interface CountryMarketOptionDef {
  /** 国家 / 市场唯一标识（如 'cn' / 'us'），同时作为选项 key 与回传的选中 ID */
  countryMarketId: string;
  /** 国家 / 地区名称（如 '中国' / '美国'），作为选项文案并用于拼音分组排序 */
  countryMarketName: string;
  /** 货币 ISO 代码（如 'CNY' / 'USD'），可选展示信息 */
  currency: string;
  /** 货币名称（如 '人民币' / '美元'），与 currency 配套展示 */
  currencyName: string;
  /** 国旗图片地址（可空）：非空时选项左侧渲染国旗；为空仅显示名称，不渲染占位块 */
  flagUri: string;
}
