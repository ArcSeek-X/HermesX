/**
 * @file UniverseBackground.test.tsx
 * @description UniverseBackground 的 jsdom 冒烟测试：jsdom 无 WebGL，验证
 * 1) UI 外壳（loader / VOYAGE / ORBITS / 标尺）正常渲染；
 * 2) 引擎构造失败时组件不崩溃、loader 显示故障文案、onError 透传；
 * 3) 卸载流程干净（无残留 canvas、无异常）。
 * 真实渲染效果需在浏览器中人工验证（WebGL 无法在 jsdom 复现）。
 * @author gaocangxiong <Lensgcx@163.com>
 */

import { render, cleanup } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import UniverseBackground from '../UniverseBackground'

afterEach(cleanup)

describe('UniverseBackground', () => {
  it('renders the vendored UI shell (loader, VOYAGE, ORBITS, scale ruler)', () => {
    render(<UniverseBackground />)
    expect(document.getElementById('loader')).toBeInTheDocument()
    expect(document.getElementById('ld-status')).toBeInTheDocument()
    // VOYAGE 时间轴 / ORBITS 时间倍率 / 尺度标尺：原版控件随外壳一起挂载
    expect(document.getElementById('voyage')).toBeInTheDocument()
    expect(document.querySelector('.seg3')).toBeInTheDocument()
    expect(document.getElementById('ruler')).toBeInTheDocument()
    // DESTINATIONS / 章节时间轴容器存在（由引擎填充）
    expect(document.getElementById('dest-list')).toBeInTheDocument()
    expect(document.getElementById('segs')).toBeInTheDocument()
  })

  it('degrades gracefully when WebGL is unavailable (jsdom)', () => {
    const onError = vi.fn()
    render(<UniverseBackground onError={onError} />)
    // 引擎构造同步失败 → loader 显示故障文案，不抛未捕获异常
    expect(document.getElementById('ld-status')?.textContent).toContain('SYSTEM FAULT')
    expect(onError).toHaveBeenCalledTimes(1)
    // 失败后不残留 canvas
    expect(document.querySelector('canvas')).toBeNull()
  })

  it('cleans up on unmount without leaking canvases', () => {
    const { unmount } = render(<UniverseBackground />)
    unmount()
    expect(document.querySelector('canvas')).toBeNull()
    expect(document.getElementById('loader')).toBeNull()
  })
})
