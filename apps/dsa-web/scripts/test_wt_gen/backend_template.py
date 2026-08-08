# -*- coding: utf-8 -*-
"""
__ROUTE__ 后端集成测试（模板骨架，由 scaffold_wt.sh 生成）
===========================================================

用法：由 test_wt.sh 在仓库根目录调用，真实调用 FastAPI 接口并校验返回结构契约。
输出 [RESULT]/[SUMMARY]/[FAIL] 供主脚本解析；退出码 0/1/2。

生成后请按以下步骤补全：
  1. 在 api/v1/endpoints/ 找到本模块对应的 router，列出全部端点
  2. 在下方 main() 中为每个端点写一个 try 块：
       - client.get(f"{base}/xxx", params={...})
       - r.status_code == 200
       - data = r.json()，校验关键字段类型与必填项
  3. 多周期 / 多参数组合用 for 循环覆盖
"""

import os
import sys
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from fastapi.testclient import TestClient
    from server import create_app
except Exception as e:  # noqa: BLE001
    print(f"[RESULT] SKIP")
    print(f"[SUMMARY] 依赖缺失：{e}")
    print(f"[FAIL] 无法 import fastapi/TestClient/server：{e}")
    sys.exit(2)


_RESULTS = []


def record(name, passed, detail=""):
    _RESULTS.append((name, passed, detail))
    tag = "PASS" if passed else "FAIL"
    print(f"[{tag}] {name} {detail}".strip())


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def main():
    try:
        app = create_app()
    except Exception as e:  # noqa: BLE001
        print(f"[RESULT] SKIP")
        print(f"[SUMMARY] 构建 app 失败：{e}")
        print(f"[FAIL] create_app() 失败：{e}")
        traceback.print_exc()
        sys.exit(2)

    client = TestClient(app)
    base = "/api/v1/__ROUTE__"  # TODO: 替换为真实路由前缀，如 /api/v1/sector

    # ---- TODO: 在此按真实端点逐个补充 ----
    # 示例（删去并替换为实际接口）：
    # try:
    #     r = client.get(f"{base}/list")
    #     passed = r.status_code == 200
    #     detail = f"status={r.status_code}"
    #     if passed:
    #         data = r.json()
    #         if not isinstance(data.get("items"), list):
    #             passed = False
    #             detail = "items 非数组"
    #     record("GET /list", passed, detail)
    # except Exception as e:  # noqa: BLE001
    #     record("GET /list", False, f"异常：{e}")

    if not _RESULTS:
        print("[RESULT] SKIP")
        print("[SUMMARY] 未配置任何接口用例（骨架未补全）")
        print("[FAIL] 请在 main() 中补充本模块的真实接口用例")
        sys.exit(2)

    total = len(_RESULTS)
    passed_n = sum(1 for _, p, _ in _RESULTS if p)
    failed_n = total - passed_n
    print(f"[SUMMARY] 通过 {passed_n} / 失败 {failed_n} / 共 {total}")
    if failed_n > 0:
        print("[RESULT] FAIL")
        for name, p, detail in _RESULTS:
            if not p:
                print(f"[FAIL] {name} {detail}".strip())
        sys.exit(1)
    else:
        print("[RESULT] PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
