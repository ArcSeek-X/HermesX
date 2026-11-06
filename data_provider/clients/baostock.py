"""baostock 共享协议、连接和配额；无能力选源/回退或第二份资源。"""

from __future__ import annotations

from data_provider.common.errors import DataFetchError
from src.domain.market.stock_codes import normalize_stock_code
import re

from dataclasses import dataclass
from typing import Callable
from typing import Generator


@dataclass(frozen=True)
class BaostockClientAccess:
    """窄资源访问契约；状态写回原所有者，兼容旧资源扩展点。"""

    use_get_baostock: Callable
    read_bs_module: Callable
    write_bs_module: Callable
    read_global_DataFetchError: Callable
    read_global_logger: Callable

    def _get_baostock(self):
        """
        延迟加载 baostock 模块

        只在首次使用时导入，避免未安装时报错
        """
        if self.read_bs_module() is None:
            import baostock as bs

            self.write_bs_module(bs)
        return self.read_bs_module()

    def _baostock_session(self) -> Generator:
        """
        Baostock 连接上下文管理器

        确保：
        1. 进入上下文时自动登录
        2. 退出上下文时自动登出
        3. 异常时也能正确登出

        使用示例：
            with self._baostock_session():
                # 在这里执行数据查询
        """
        bs = self.use_get_baostock()
        login_result = None
        try:
            login_result = bs.login()
            if login_result.error_code != "0":
                raise self.read_global_DataFetchError()(
                    f"Baostock 登录失败: {login_result.error_msg}"
                )
            self.read_global_logger().debug("Baostock 登录成功")
            yield bs
        finally:
            try:
                logout_result = bs.logout()
                if logout_result.error_code == "0":
                    self.read_global_logger().debug("Baostock 登出成功")
                else:
                    self.read_global_logger().warning(
                        f"Baostock 登出异常: {logout_result.error_msg}"
                    )
            except Exception as e:
                self.read_global_logger().warning(f"Baostock 登出时发生错误: {e}")


def convert_stock_code(stock_code: str, *, is_hk, logger) -> str:
    """
    转换股票代码为 Baostock 格式

    Baostock 要求的格式：
    - 沪市：sh.600519
    - 深市：sz.000001

    Args:
        stock_code: 原始代码，如 '600519', '000001'

    Returns:
        Baostock 格式代码，如 'sh.600519', 'sz.000001'
    """
    raw_code = stock_code.strip()
    upper = raw_code.upper()

    # HK stocks are not supported by Baostock
    if is_hk(raw_code):
        raise DataFetchError(f"BaostockFetcher 不支持港股 {raw_code}，请使用 AkshareFetcher")

    # 保留既有小写 baostock 格式输入的内部容错，但用户配置仍推荐 6 位裸代码。
    if raw_code.startswith(('sh.', 'sz.')):
        return raw_code.lower()

    exchange_hint = None
    if upper.startswith(('SH', 'SS')) or upper.endswith(('.SH', '.SS')):
        exchange_hint = 'sh'
    elif upper.startswith('SZ') or upper.endswith('.SZ'):
        exchange_hint = 'sz'

    code = normalize_stock_code(raw_code)

    if exchange_hint in ('sh', 'sz') and code.isdigit() and len(code) == 6:
        return f"{exchange_hint}.{code}"

    # ETF: Shanghai ETF (51xx, 52xx, 56xx, 58xx) -> sh; Shenzhen ETF (15xx, 16xx, 18xx) -> sz
    if len(code) == 6:
        if code.startswith(('51', '52', '56', '58')):
            return f"sh.{code}"
        if code.startswith(('15', '16', '18')):
            return f"sz.{code}"

    # 根据代码前缀判断市场
    if code.startswith(('600', '601', '603', '605', '688')):
        return f"sh.{code}"
    elif code.startswith(('000', '001', '002', '003', '300', '301')):
        return f"sz.{code}"
    else:
        logger.warning(f"无法确定股票 {code} 的市场，默认使用深市")
        return f"sz.{code}"


def _is_us_code(stock_code: str) -> bool:
    """
    判断代码是否为美股
    
    美股代码规则：
    - 1-5个大写字母，如 'AAPL', 'TSLA'
    - 可能包含 '.'，如 'BRK.B'
    """
    code = stock_code.strip().upper()
    return bool(re.match(r'^[A-Z]{1,5}(\.[A-Z])?$', code))
