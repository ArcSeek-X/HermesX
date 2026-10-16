/**
 * @file index.ts
 * @description universe 组件目录出口（叶子导出，不走 @components 裸桶——桶仅聚合 basic/common）。
 * 引用方式：`import UniverseBackground from '@components/universe/UniverseBackground'`
 * 或 `import { UniverseBackground } from '@components/universe'`。
 * @author gaocangxiong <Lensgcx@163.com>
 */

export { default as UniverseBackground } from './UniverseBackground'
export type {
  UniverseBackgroundProps,
  UniverseImperativeApi,
  UniverseTier,
  UniverseMode,
  UniverseEntry,
  UniverseZoomTarget,
  UniverseOrbitSpeed,
} from './types'
