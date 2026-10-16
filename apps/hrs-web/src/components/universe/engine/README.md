# engine/ — vendored「BEYOND THE WANDERING EARTH」

本目录是 [vibe-template/earth-migration](../../../../../../vibe-template/earth-migration)（本地模板，**未被 git 跟踪**，见根 `.gitignore`）的 vendor 拷贝，MIT License © 2026 玛卡巴卡（见 `LICENSE`）。

## 目录映射

| 本目录 | 上游 | 说明 |
| --- | --- | --- |
| `beyond/main.js` | `js/beyond/main.js` | 总控；已包装为 `createUniverse(opts)` 工厂 |
| `beyond/{galaxy,solar,earth,story,post,util,dash,audio,craft}.js` | `js/beyond/*` | 原样拷贝，仅 `dash.js`/`story.js` 有少量接缝补丁 |
| `fx/*` | `js/fx/*` | 原样拷贝，仅 `models.js` 有 Draco 基址补丁 |
| `LICENSE` | 仓库根 `LICENSE` | MIT 许可副本 |

## 与上游的差异（全部为「React wrapper」接缝，视觉/行为不变）

1. `main.js`：import 即执行的单页入口 → `export function createUniverse(opts)`；
   `window.__beyond` → 返回值；`$()` 限定在 `opts.root` 内；`innerWidth/innerHeight` → 容器尺寸；
   `window.__WALLPAPER` → `opts.wallpaper`；`window.__emStarted/__emReady` 删除；
   资源 URL 经 `THREE.DefaultLoadingManager.setURLModifier` 加 `opts.assetsBase` 前缀；
   音频默认静音（`opts.audio` 开启）；循环支持 `app.paused`/`document.hidden` 暂停；
   新增 `dispose()` 与命令式 API（`setVoyage/setOrbitSpeed/setRotationSpeed/setPaused/zoomTo/zoomBy/resize`）；
   星系自转速率支持 `S.galRotK` 倍率（free 相机与 story 两处）。
2. `dash.js`：`createDash` 增加 `ctx.root`，HUD 挂载与 `dash-on` 类切换到容器内。
3. `story.js`：`S.galRot` 计算乘 `(S.galRotK ?? 1)`。
4. `fx/models.js`：Draco decoder 路径改为 `setAssetBase()` 注入（`<assetsBase>draco/gltf/`）。

## 重新同步上游

上游不在 git 内，同步方式为人工比对：

```bash
diff -u vibe-template/earth-migration/js/beyond/main.js \
        apps/hrs-web/src/components/universe/engine/beyond/main.js
```

合并时保留上述接缝；`main.js` 的工厂包装（文件头注释 + `host integration` 段 + 尾部 `api` 块）不要丢。

## 静态资源

不在本目录：`apps/hrs-web/public/universe/`（`assets/` 31M + `draco/gltf/` 752K），
由 `createUniverse` 的 `assetsBase`（默认 `${BASE_URL}universe/`）寻址。
