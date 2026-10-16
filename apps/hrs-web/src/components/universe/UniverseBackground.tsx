/**
 * @file UniverseBackground.tsx
 * @description 星系/银河/太阳系尺度梯子背景组件（vendor 自「BEYOND THE WANDERING EARTH」，
 * MIT © 2026 玛卡巴卡）：Three.js 三层场景 + 后期辉光 + 剧情/自由相机 + 原版 HUD。
 * 用法：作为页面/区块背景挂载即可；VOYAGE / ORBITS / 缩放 / 自转速率既可经 props/ref
 * 编程控制，也可直接用组件内原版控件（滑条、seg3、标尺、热点、DESTINATIONS）。
 *
 * 生命周期约定：
 *   - 引擎在挂载时创建一次（canvas 动态创建并挂到根节点下），卸载时完整 dispose；
 *   - mode/anchor/distance/entry/flyIn 仅首次挂载生效，运行中换视角用 ref.zoomTo/focus；
 *   - 页面不可见或组件滚出视口时自动暂停渲染；interactive=false 时容器 pointer-events:none
 *     且不劫持页面滚轮/键盘，可作纯装饰背景；
 *   - 同一页面建议只挂一个实例（WebGL context 上限约 16，且 HUD 为 id 级 DOM）。
 *
 * 使用示例：
 *   <UniverseBackground tier="medium" rotationSpeed={0.5} />
 *   <UniverseBackground ref={apiRef} interactive={false} onReady={api => api.zoomTo('solar')} />
 *
 * @author gaocangxiong <Lensgcx@163.com>
 */

import { useEffect, useImperativeHandle, useMemo, useRef } from 'react'
import clsx from 'clsx'
import { createUniverse } from './engine/beyond/main.js'
import BeyondShell from './ui/BeyondShell'
import './ui/beyond.css'
import type {
  UniverseBackgroundProps,
  UniverseEngineHandle,
  UniverseEngineInit,
  UniverseImperativeApi,
} from './types'

// engine 为 vendored .js（allowJs，无 .d.ts）：入参/句柄类型在 types.ts 显式声明
const createEngine = createUniverse as unknown as (opts: UniverseEngineInit) => UniverseEngineHandle

// 原版 beyond.html 引入的 Google Fonts（Orbitron/Rajdhani/JetBrains Mono），多实例共享注入
const FONT_HREFS = [
  'https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap',
]
let fontRefs = 0
const injectFonts = () => {
  if (fontRefs++ > 0) return
  for (const href of FONT_HREFS) {
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = href
    link.dataset.universeFont = '1'
    document.head.appendChild(link)
  }
}
const releaseFonts = () => {
  if (--fontRefs > 0) return
  document.head.querySelectorAll('link[data-universe-font]').forEach(n => n.remove())
}

const DEFAULT_ASSETS_BASE = `${import.meta.env.BASE_URL}universe/`

export default function UniverseBackground({
  className,
  style,
  tier,
  mode = 'free',
  anchor = 'gc',
  distance,
  entry = 'galaxy',
  flyIn = true,
  voyage = 0,
  orbitSpeed = 0,
  rotationSpeed = 1,
  interactive = true,
  audio = false,
  paused = false,
  assetsBase = DEFAULT_ASSETS_BASE,
  onReady,
  onProgress,
  onError,
  ref,
}: UniverseBackgroundProps) {
  const shellRef = useRef<HTMLDivElement>(null)
  const engineRef = useRef<UniverseEngineHandle | null>(null)
  const inViewRef = useRef(true)

  // 最新 props 镜像：经 effect 写入（render 期间不触碰 ref），供建引擎 effect 与引擎回调读取
  const live = useRef({
    tier, mode, anchor, distance, entry, flyIn, voyage, orbitSpeed, rotationSpeed,
    interactive, audio, paused, assetsBase, onReady, onProgress, onError,
  })

  // 稳定的命令式门面：转发到当前引擎实例（卸载后为空操作）
  const facade = useMemo<UniverseImperativeApi>(() => {
    const e = () => engineRef.current
    return {
      resize: (w, h) => e()?.resize(w, h),
      setVoyage: t => e()?.setVoyage(t),
      setOrbitSpeed: v => e()?.setOrbitSpeed(v),
      setRotationSpeed: k => e()?.setRotationSpeed(k),
      setPaused: p => e()?.setPaused(p),
      zoomTo: t => e()?.zoomTo(t),
      zoomBy: f => e()?.zoomBy(f),
      focus: key => e()?.focus(key),
      seek: t => e()?.seek(t),
      setTier: t => e()?.setTier(t),
      dispose: () => e()?.dispose(),
      get raw() { return e() },
    }
  }, [])
  useImperativeHandle(ref, () => facade, [facade])

  /* ------------------------------------------------ props 镜像同步（先于建引擎 effect 执行） */
  useEffect(() => {
    live.current = {
      tier, mode, anchor, distance, entry, flyIn, voyage, orbitSpeed, rotationSpeed,
      interactive, audio, paused, assetsBase, onReady, onProgress, onError,
    }
  })

  /* ------------------------------------------------ 创建 / 销毁引擎（仅一次） */
  useEffect(() => {
    const shell = shellRef.current
    if (!shell) return
    let engine: UniverseEngineHandle | null = null
    let canvas: HTMLCanvasElement | null = null
    let ro: ResizeObserver | null = null
    let io: IntersectionObserver | null = null

    const syncPaused = () => engine?.setPaused(!inViewRef.current || document.hidden || live.current.paused)

    try {
      canvas = document.createElement('canvas')
      canvas.tabIndex = 0
      canvas.setAttribute('aria-label', 'Cinematic 3D journey from Earth’s planetary engines to the Milky Way')
      shell.appendChild(canvas)
      engine = createEngine({
        canvas,
        root: shell,
        tier: live.current.tier,
        mode: live.current.mode,
        anchor: live.current.anchor,
        distance: live.current.distance,
        entry: live.current.entry,
        flyIn: live.current.flyIn,
        voyage: live.current.voyage,
        orbitSpeed: live.current.orbitSpeed,
        rotationSpeed: live.current.rotationSpeed,
        interactive: live.current.interactive,
        audio: live.current.audio,
        assetsBase: live.current.assetsBase,
        onProgress: (p, label) => live.current.onProgress?.(p, label),
        onReady: () => {
          // 加载期间 props 可能已变更：就绪后补一次下发，再通知宿主
          const L = live.current
          engineRef.current?.setTier(L.tier)
          engineRef.current?.setVoyage(L.voyage)
          engineRef.current?.setOrbitSpeed(L.orbitSpeed)
          engineRef.current?.setRotationSpeed(L.rotationSpeed)
          engineRef.current?.setPaused(L.paused)
          L.onReady?.(facade)
        },
        // 引擎的 onError 为异步回调（加载失败时触发）：只透传给宿主，不在 effect 内同步 setState
        onError: err => { live.current.onError?.(err) },
      })
    } catch (err) {
      // 同步构造失败（典型：无 WebGL）：loader 内直接显示故障文案，并透传错误
      canvas?.remove()
      const st = shell.querySelector('#ld-status')
      if (st) st.textContent = 'SYSTEM FAULT · WEBGL UNAVAILABLE'
      live.current.onError?.(err)
      return
    }
    engineRef.current = engine

    const resize = () => engine?.resize(shell.clientWidth, shell.clientHeight)
    resize()
    ro = new ResizeObserver(resize)
    ro.observe(shell)
    io = new IntersectionObserver(
      entries => { inViewRef.current = entries[entries.length - 1]?.isIntersecting ?? true; syncPaused() },
      { threshold: 0 },
    )
    io.observe(shell)
    document.addEventListener('visibilitychange', syncPaused)

    return () => {
      document.removeEventListener('visibilitychange', syncPaused)
      ro?.disconnect()
      io?.disconnect()
      engine?.dispose()
      canvas?.remove()
      engineRef.current = null
    }
  }, [facade])

  /* ------------------------------------------------ props → 引擎同步（不重建引擎） */
  useEffect(() => { engineRef.current?.setVoyage(voyage) }, [voyage])
  useEffect(() => { engineRef.current?.setOrbitSpeed(orbitSpeed) }, [orbitSpeed])
  useEffect(() => { engineRef.current?.setRotationSpeed(rotationSpeed) }, [rotationSpeed])
  useEffect(() => { engineRef.current?.setTier(tier) }, [tier])
  useEffect(() => { engineRef.current?.setPaused(paused) }, [paused])

  /* ------------------------------------------------ 字体注入（多实例共享） */
  useEffect(() => {
    injectFonts()
    return releaseFonts
  }, [])

  return (
    <div
      ref={shellRef}
      className={clsx('universe-bg', className)}
      style={{
        position: 'absolute',
        inset: 0,
        overflow: 'hidden',
        // 纯装饰背景下不接收指针事件；引擎内的滚轮/键盘监听同样被 interactive 关闭
        pointerEvents: interactive ? 'auto' : 'none',
        ...style,
      }}
    >
      <BeyondShell />
    </div>
  )
}
