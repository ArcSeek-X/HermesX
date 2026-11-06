"""pytdx 共享协议、连接和配额；无能力选源/回退或第二份资源。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple
import os
import re
import logging
from src.domain.market.stock_codes import normalize_stock_code

logger = logging.getLogger("data_provider.pytdx_fetcher")
from typing import Generator


@dataclass(frozen=True)
class PytdxClientAccess:
    """窄资源访问契约；状态写回原所有者，兼容旧资源扩展点。"""

    use_get_pytdx: Callable
    use_is_in_connection_cooldown: Callable
    use_mark_connection_cooldown: Callable
    read_current_host_idx: Callable
    read_hosts: Callable
    read_last_unavailable_reason: Callable
    read_unavailable_until: Callable
    write_current_host_idx: Callable
    write_last_unavailable_reason: Callable
    write_unavailable_until: Callable
    read_global_DataFetchError: Callable
    read_global_DataSourceUnavailableError: Callable
    read_global_PYTDX_CONNECTION_COOLDOWN_SECONDS: Callable
    read_global_logger: Callable
    read_global_time: Callable

    def _is_in_connection_cooldown(self) -> bool:
        """判断是否处于连接冷却期。"""
        return self.read_global_time().time() < self.read_unavailable_until()

    def _mark_connection_cooldown(self, reason: str) -> None:
        """标记连接冷却期。"""
        self.write_unavailable_until(
            self.read_global_time().time()
            + self.read_global_PYTDX_CONNECTION_COOLDOWN_SECONDS()
        )
        self.write_last_unavailable_reason(str(reason or "").strip())
        self.read_global_logger().info(
            "Pytdx 连接失败，进入冷却 %.0fs: %s",
            self.read_global_PYTDX_CONNECTION_COOLDOWN_SECONDS(),
            self.read_last_unavailable_reason() or "unknown",
        )

    def is_available_for_request(self, capability: str = "") -> bool:
        """判断当前是否可发起请求。"""
        return not self.use_is_in_connection_cooldown()

    def _get_pytdx(self):
        """
        延迟加载 pytdx 模块

        只在首次使用时导入，避免未安装时报错
        """
        try:
            from pytdx.hq import TdxHq_API

            return TdxHq_API
        except ImportError:
            self.read_global_logger().warning("pytdx 未安装，请运行: pip install pytdx")
            return None

    def _pytdx_session(self) -> Generator:
        """
        Pytdx 连接上下文管理器

        确保：
        1. 进入上下文时自动连接
        2. 退出上下文时自动断开
        3. 异常时也能正确断开

        使用示例：
            with self._pytdx_session() as api:
                # 在这里执行数据查询
        """
        if self.use_is_in_connection_cooldown():
            raise self.read_global_DataSourceUnavailableError()(
                f"Pytdx temporarily unavailable: {self.read_last_unavailable_reason() or 'connection cooldown'}"
            )
        TdxHq_API = self.use_get_pytdx()
        if TdxHq_API is None:
            raise self.read_global_DataFetchError()("pytdx 库未安装")
        api = TdxHq_API()
        connected = False
        try:
            for i in range(len(self.read_hosts())):
                host_idx = (self.read_current_host_idx() + i) % len(self.read_hosts())
                host, port = self.read_hosts()[host_idx]
                try:
                    if api.connect(host, port, time_out=5):
                        connected = True
                        self.write_current_host_idx(host_idx)
                        self.read_global_logger().debug(
                            f"Pytdx 连接成功: {host}:{port}"
                        )
                        break
                except Exception as e:
                    self.read_global_logger().debug(
                        f"Pytdx 连接 {host}:{port} 失败: {e}"
                    )
                    continue
            if not connected:
                self.use_mark_connection_cooldown("Pytdx 无法连接任何服务器")
                raise self.read_global_DataFetchError()("Pytdx 无法连接任何服务器")
            yield api
        finally:
            try:
                api.disconnect()
                self.read_global_logger().debug("Pytdx 连接已断开")
            except Exception as e:
                self.read_global_logger().warning(f"Pytdx 断开连接时出错: {e}")


def _parse_hosts_from_env() -> Optional[List[Tuple[str, int]]]:
    """
    从环境变量构建通达信服务器列表。

    优先级：
    1. PYTDX_SERVERS：逗号分隔 "ip:port,ip:port"（如 "192.168.1.1:7709,10.0.0.1:7709"）
    2. PYTDX_HOST + PYTDX_PORT：单个服务器
    3. 均未配置时返回 None（调用方使用 DEFAULT_HOSTS）
    """
    servers = os.getenv("PYTDX_SERVERS", "").strip()
    if servers:
        result = []
        for part in servers.split(","):
            part = part.strip()
            if ":" in part:
                host, port_str = part.rsplit(":", 1)
                host, port_str = host.strip(), port_str.strip()
                if host and port_str:
                    try:
                        result.append((host, int(port_str)))
                    except ValueError:
                        logger.warning(f"Invalid PYTDX_SERVERS entry: {part}")
            else:
                logger.warning(f"Invalid PYTDX_SERVERS entry (missing port): {part}")
        if result:
            return result

    host = os.getenv("PYTDX_HOST", "").strip()
    port_str = os.getenv("PYTDX_PORT", "").strip()
    if host and port_str:
        try:
            return [(host, int(port_str))]
        except ValueError:
            logger.warning(f"Invalid PYTDX_HOST/PYTDX_PORT: {host}:{port_str}")

    return None


def _is_us_code(stock_code: str) -> bool:
    """
    判断代码是否为美股
    
    美股代码规则：
    - 1-5个大写字母，如 'AAPL', 'TSLA'
    - 可能包含 '.'，如 'BRK.B'
    """
    code = stock_code.strip().upper()
    return bool(re.match(r'^[A-Z]{1,5}(\.[A-Z])?$', code))


def get_market_code(stock_code: str) -> Tuple[int, str]:
    """
    根据股票代码判断市场

    Pytdx 市场代码：
    - 0: 深圳
    - 1: 上海

    Args:
        stock_code: 股票代码

    Returns:
        (market, code) 元组
    """
    raw_code = stock_code.strip()
    upper = raw_code.upper()
    prefix, separator, suffix = raw_code.partition(".")
    if separator and prefix:
        prefix_upper = prefix.strip().upper()
        if prefix_upper in ('SH', 'SS'):
            normalized = normalize_stock_code(suffix.strip())
            if normalized.isdigit() and len(normalized) == 6:
                return 1, normalized
        if prefix_upper == 'SZ':
            normalized = normalize_stock_code(suffix.strip())
            if normalized.isdigit() and len(normalized) == 6:
                return 0, normalized

    code = normalize_stock_code(raw_code)

    if upper.startswith(('SH', 'SS')) or upper.endswith(('.SH', '.SS')):
        return 1, code
    if upper.startswith('SZ') or upper.endswith('.SZ'):
        return 0, code

    # 根据代码前缀判断市场
    # 上海：60xxxx, 68xxxx（科创板）
    # 深圳：00xxxx, 30xxxx（创业板）, 002xxx（中小板）
    if code.startswith(('60', '68')):
        return 1, code  # 上海
    else:
        return 0, code  # 深圳
