# -*- coding: utf-8 -*-
"""运行时补丁集合（monkeypatch）。

目前仅含 ``eastmoney_patch``：在请求入口为东财接口注入随机 User-Agent 与
NID 授权 Cookie，并随机休眠以降低被封风险。仅在需要时导入并调用 ``eastmoney_patch()``。
"""
