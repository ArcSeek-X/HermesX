/**
 * @file types.ts
 * @description UniverseBackground 组件与 engine（createUniverse）之间的类型契约。
 * engine 为 vendored .js（allowJs 编译，无 .d.ts），此处显式声明初始化入参、
 * 命令式句柄与组件 props，避免 any 泄漏到调用方。
 * @author gaocangxiong <Lensgcx@163.com>
 */

import type { CSSProperties, Ref } from 'react'

/** 画质分级（engine TIERS：只改成本，不改观感） */
export type UniverseTier = 'low' | 'medium' | 'high' | 'ultra';

/** 入口模式：free = 自由相机（默认银心视角），film = 剧情电影 */
export type UniverseMode = 'free' | 'film';

/** galaxy = 跳过标题屏直接进入场景（默认）；title = 保留原版标题屏 */
export type UniverseEntry = 'galaxy' | 'title';

/** zoomTo 的语义化缩放目标（跨越尺度梯子：星系 → 银河 → 太阳系 → 地球） */
export type UniverseZoomTarget = 'galaxy' | 'milkyway' | 'sol' | 'acen' | 'orrery' | 'sun' | 'earth';

/** ORBITS 时间倍率预设（与原版 seg3 按钮一致） */
export type UniverseOrbitSpeed = 0 | 0.04 | 0.35 | 3;

/** createUniverse 的初始化入参（engine/beyond/main.js 的 JSDoc 契约镜像） */
export interface UniverseEngineInit {
  canvas: HTMLCanvasElement;
  root: HTMLElement;
  tier?: UniverseTier;
  mode?: UniverseMode;
  anchor?: string;
  distance?: number;
  voyage?: number;
  orbitSpeed?: number;
  rotationSpeed?: number;
  interactive?: boolean;
  audio?: boolean;
  flyIn?: boolean;
  entry?: UniverseEntry;
  assetsBase?: string;
  onProgress?: (progress: number, label: string) => void;
  onReady?: () => void;
  onError?: (error: unknown) => void;
}

/** 引擎命令式句柄（createUniverse 返回值；加载完成前调用多为安全空操作） */
export interface UniverseEngineHandle {
  resize(width: number, height: number): void;
  setVoyage(seconds: number): void;
  setOrbitSpeed(speed: number): void;
  setRotationSpeed(multiplier: number): void;
  setPaused(paused: boolean): void;
  zoomTo(target: string): void;
  zoomBy(factor: number): void;
  focus(key: string): void;
  seek(seconds: number): void;
  /** 运行时切换画质（不重建场景；undefined = 保持当前，引擎内空操作） */
  setTier(tier?: UniverseTier): void;
  dispose(): void;
}

/** 组件 ref 暴露的 API = 引擎句柄 + 原始引擎对象 */
export interface UniverseImperativeApi extends UniverseEngineHandle {
  /** 原始引擎 API（engine/beyond/main.js 返回值），高级用法，随上游 vendor 版本演进 */
  raw: unknown;
}

export interface UniverseBackgroundProps {
  /** 容器类名 */
  className?: string;
  /** 容器样式（默认 absolute inset 0，可作为任意区块的背景） */
  style?: CSSProperties;
  /** 画质分级，默认按设备（桌面 high / 移动 low） */
  tier?: UniverseTier;
  /** 入口模式，默认 'free'（仅首次挂载生效） */
  mode?: UniverseMode;
  /** 自由相机锚点 key，默认 'gc'（银心；仅首次挂载生效） */
  anchor?: string;
  /** 自由相机距离（art-AU），默认 90000 ly（仅首次挂载生效） */
  distance?: number;
  /** 入口形式，默认 'galaxy'（跳过标题屏） */
  entry?: UniverseEntry;
  /** 是否以飞行动画进入入口视角，默认 true */
  flyIn?: boolean;
  /** 剧情时间（秒），运行中变更等价于拖动 VOYAGE 滑条 */
  voyage?: number;
  /** ORBITS 时间倍率，默认 0（实时） */
  orbitSpeed?: UniverseOrbitSpeed | number;
  /** 星系自转倍率，默认 1（原速 0.012 rad/s） */
  rotationSpeed?: number;
  /** 是否启用交互（滚轮 / 拖拽 / 键盘 / HUD 点击），默认 true；纯装饰背景传 false */
  interactive?: boolean;
  /** 是否开启声音（需用户手势，默认 false） */
  audio?: boolean;
  /** 手动暂停（页面隐藏 / 滚出视口时组件会自动暂停，无需手动） */
  paused?: boolean;
  /** 静态资源基址，默认 `${import.meta.env.BASE_URL}universe/` */
  assetsBase?: string;
  /** 场景就绪（资源加载完成、开始渲染） */
  onReady?: (api: UniverseImperativeApi) => void;
  /** 加载进度 0–1 与阶段文案 */
  onProgress?: (progress: number, label: string) => void;
  /** 启动失败（如无 WebGL） */
  onError?: (error: unknown) => void;
  /** React 19 ref prop：拿到底层命令式 API */
  ref?: Ref<UniverseImperativeApi>;
}
