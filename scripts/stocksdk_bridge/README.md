# StockSDK Bridge

这个目录是 HermesX 的 `StockSDK` Node bridge，小范围职责如下：

- 承载 `stock-sdk` 的 Node 依赖
- 提供 Python 后端调用的 bridge 入口 `bridge.mjs`
- 作为 `data_provider/stocksdk_bridge.py` 的配套运行单元

## 目录结构

- `bridge.mjs`：Node bridge 入口
- `package.json`：bridge 专属依赖与脚本

## 安装

```bash
cd /Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/scripts/stocksdk_bridge
npm install
```

## 调试运行

```bash
cd /Users/gaocangxiong/Work/DevProject/ArcSeek-X/HermesX/scripts/stocksdk_bridge
echo '{"action":"ping","payload":{},"sdkOptions":{}}' | npm run bridge
```

## 与后端的关系

Python 后端不会直接加载 `stock-sdk`，而是通过：

- `data_provider/stocksdk_bridge.py`

来启动：

- `scripts/stocksdk_bridge/bridge.mjs`

因此，`stock-sdk` 依赖应保留在当前目录，不应放进：

- `apps/hrs-web/package.json`
- `scripts/` 根目录

这样可以保持职责边界清晰：

- 前端依赖归前端
- 后端桥接依赖归 bridge
- `data_provider` 继续作为统一数据源收口层
