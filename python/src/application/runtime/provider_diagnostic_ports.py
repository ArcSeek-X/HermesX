"""数据源诊断的窄回调端口；不保存 trace、连接或业务诊断数据。"""

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class ProviderDiagnosticCallbacks:
    """一对同批发布的记录函数；具体上下文由实现读取。"""

    started: Callable[..., None]
    finished: Callable[..., None]


_callbacks: Optional[ProviderDiagnosticCallbacks] = None


def bind_provider_diagnostic_callbacks(
    *, started: Callable[..., None], finished: Callable[..., None]
) -> None:
    """在 trace 激活前绑定记录实现；不捕获某个请求的上下文。"""
    global _callbacks
    _callbacks = ProviderDiagnosticCallbacks(started=started, finished=finished)


def provider_diagnostic_callbacks() -> Optional[ProviderDiagnosticCallbacks]:
    """未激活过诊断时返回 None；普通取数无需诊断装配。"""
    return _callbacks
