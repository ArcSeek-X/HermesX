/**
 * @file BeyondShell.tsx
 * @description 「BEYOND THE WANDERING EARTH」星空体验的 UI 外壳：loader、标题屏、HUD
 * （NAVIGATION TELEMETRY / DESTINATIONS / 章节时间轴 / VOYAGE 时间轴 / ORBITS 时间倍率 /
 * 尺度标尺 / 热点标记）与片尾屏。vendor 自 vibe-template/earth-migration/beyond.html，
 * 元素 id 与原页一一对应——engine（engine/beyond/main.js）按 id 查询并直接操作这些节点。
 * ⚠️ 增删元素或改 id 前先确认 engine 中的 `$('...')` 调用点；canvas 不在此处渲染，
 * 由 UniverseBackground 动态创建并挂载到根节点下（见 ui/beyond.css 的 `> canvas` 规则）。
 * @author gaocangxiong <Lensgcx@163.com>
 */

export default function BeyondShell() {
  return (
    <>
      <div className="bars" aria-hidden="true" />

      <div id="loader" role="status" aria-live="polite">
        <div className="ld-inner">
          <div className="ld-kicker">UNITED EARTH GOVERNMENT · NAVIGATION PLATFORM</div>
          <div className="ld-title">BEYOND THE WANDERING EARTH</div>
          <div className="ld-bar"><i id="ld-fill" /></div>
          <div className="ld-status" id="ld-status">ESTABLISHING UPLINK…</div>
        </div>
      </div>

      <div id="start" className="screen">
        <div className="sc-inner">
          <div className="sc-kicker">Part II of The Earth Migration Project</div>
          <h1 className="sc-title">BEYOND THE<br />WANDERING EARTH</h1>
          <div className="sc-sub">Humanity’s Journey from a Dying Sun to the Galactic Sea</div>
          <div className="sc-actions">
            <button className="cta" id="b-begin" type="button"><span className="cta-ico">▶</span><span>Begin the voyage<small>Cinematic autoplay · 2½ minutes · sound on</small></span></button>
            <button className="cta ghost" id="b-explore" type="button"><span>Free camera<small>Fly from the engines to the galaxy</small></span></button>
          </div>
          <div className="sc-hints"><span><kbd>Scroll</kbd> travel through time</span><span><kbd>Drag</kbd> look around</span><span><kbd>Click</kbd> a marker to focus</span><span><kbd>F</kbd> free camera</span></div>
        </div>
        <div className="sc-frame" aria-hidden="true"><i /><i /><i /><i /></div>
        <div className="sc-tele" aria-hidden="true"><span><b className="dot" />UEG NAVIGATION PLATFORM</span><span>SOL-3 · 1.000 AU</span><span>YEAR 2078</span><span>ENGINES <b>0 / 10,000</b></span><span className="sc-wait">STATUS · AWAITING IGNITION</span></div>
      </div>

      <div id="card" aria-live="polite"><div className="cd-n" id="cd-n" /><div className="cd-t" id="cd-t" /><div className="cd-k" id="cd-k" /></div>
      <div id="caption" aria-live="polite" />
      <div id="count" aria-hidden="true"><svg className="ct-ring" viewBox="0 0 200 200"><circle className="ct-track" cx="100" cy="100" r="92" /><circle className="ct-arc" cx="100" cy="100" r="92" /></svg><div className="ct-k">GLOBAL IGNITION SEQUENCE</div><div className="ct-n" id="ct-n" /><div className="ct-s">10,000 ENGINES · TRAILING HEMISPHERE · THRUST 150 BILLION TONNES</div></div>
      <div id="hint" />

      <div id="hud">
        <div id="brand"><div className="br-t">BEYOND THE WANDERING EARTH</div><div className="br-s">Humanity’s Journey from a Dying Sun to the Galactic Sea</div></div>
        <div id="data" className="glass">
          <div className="g-head"><span className="dot" />NAVIGATION TELEMETRY</div>
          <div className="g-row"><span>ENGINE STATUS</span><b id="d-engine">—</b></div>
          <div className="g-meter"><i id="d-engine-bar" /></div>
          <div className="g-row"><span>VELOCITY</span><b id="d-speed">—</b></div>
          <div className="g-row"><span>DISTANCE FROM SOL</span><b id="d-dist">—</b></div>
          <div className="g-row"><span>REGION</span><b id="d-region">—</b></div>
          <div className="g-row"><span>GALACTIC COORD.</span><b id="d-coord">—</b></div>
          <div className="g-row"><span>MISSION YEAR</span><b id="d-year">—</b></div>
          <div className="g-row"><span>FIELD OF VIEW</span><b id="d-fov">—</b></div>
        </div>
        <div id="hotspots" />
        <div id="info" className="glass" />
        <div id="modes" className="glass" role="toolbar" aria-label="Mode">
          <button className="mb on" id="m-film" type="button" title="Cinematic film (Space to play)"><i>▶</i>FILM</button>
          <button className="mb" id="m-explore" type="button" title="Explore with a free camera (F)"><i>✥</i>EXPLORE</button>
          <span className="sep" />
          <button className="ib" id="b-sound" type="button" title="Sound (M)">♪</button>
          <button className="ib" id="b-hud" type="button" title="Hide dashboards (H)">◐</button>
          <button className="ib" id="b-fs" type="button" title="Full screen">⛶</button>
        </div>
        <aside id="dest" className="glass" aria-label="Destinations">
          <div className="g-head"><span className="dot" />DESTINATIONS</div>
          <div id="dest-list" />
        </aside>
        <div id="ladder" aria-hidden="true"><div className="ld-track" /><div id="ld-marks" /><div id="ld-cursor"><b id="ld-val">—</b></div></div>
        <div id="dock" className="glass">
          <button className="db" id="b-play" type="button" title="Play / pause (Space)">▶</button>
          <div id="segs" />
          <span id="time">0:00</span>
        </div>
        <div id="xdock" className="glass">
          <div className="x-row"><span className="x-l">VOYAGE</span><input id="voyage" type="range" min="0" max="146" step="0.1" defaultValue={0} aria-label="Voyage time" /><b id="voyage-y">2078</b></div>
          <div className="x-row x-orb"><span className="x-l">ORBITS</span><span className="seg3"><button type="button" data-v="0" className="on">REAL TIME</button><button type="button" data-v="0.04">1 YR / 25 s</button><button type="button" data-v="0.35">1 YR / 3 s</button><button type="button" data-v="3">TIME-LAPSE</button></span></div>
          <div id="ruler" title="Click to zoom to that scale"><div className="r-track" /><div id="r-marks" /><div id="r-cursor" /></div>
          <div className="x-hint">Drag to orbit · scroll to zoom from 100 km to 100,000 light-years · click a marker or a destination to fly there</div>
        </div>
      </div>

      <div id="end" className="screen">
        <div className="sc-inner">
          <div className="sc-kicker">Transmission ends · The journey continues</div>
          <h1 className="sc-title">BEYOND THE<br />WANDERING EARTH</h1>
          <div className="sc-sub">Humanity’s Journey from a Dying Sun to the Galactic Sea</div>
          <div className="sc-actions">
            <button className="cta" id="b-again" type="button"><span className="cta-ico">↺</span><span>Watch again</span></button>
            <button className="cta ghost" id="b-free2" type="button"><span>Explore the galaxy<small>Free camera</small></span></button>
          </div>
        </div>
      </div>
    </>
  );
}
