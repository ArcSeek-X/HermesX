/**
 * @file index.ts
 * @description components 组件库总出口 barrel：聚合 basic 目录的公共组件实例与类型；
 * 其余子目录（report/settings/...）由页面层按具体路径直接导入。
 * @author Lensgcx (GaoCangxiong)
 */
export * from './basic/Index';
export * from './common/Index';