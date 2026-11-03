"""配置文件的原子读写管理器。

负责 `.env` 文件的读取、更新与原子落盘（写临时文件 + rename，挂载不支持时回退原地写），
不解析运行时配置语义；运行值语义由 ``settings`` 模块负责。
"""

from __future__ import annotations

import errno
import hashlib
import logging
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Optional, Set, Tuple

from dotenv import dotenv_values

_ASSIGNMENT_PATTERN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
_FALLBACK_REWRITE_ERRNOS = {errno.EBUSY, errno.EXDEV}
_COMPOSE_ESCAPED_ENV_VALUE_KEYS = frozenset({"CUSTOM_WEBHOOK_BODY_TEMPLATE"})
_APPLICATION_TEMPLATE_PLACEHOLDER_PATTERN = re.compile(
    r"(?<!\$)\$(?:"
    r"\{(content_json|title_json|content|title)\}"
    r"|(content_json|title_json|content|title)\b"
    r")"
)
_ESCAPED_APPLICATION_TEMPLATE_PLACEHOLDER_PATTERN = re.compile(
    r"\$\$(?:"
    r"\{(content_json|title_json|content|title)\}"
    r"|(content_json|title_json|content|title)\b"
    r")"
)

logger = logging.getLogger(__name__)


def escape_compose_sensitive_env_value(key: str, value: str) -> str:
    """转义会被 Docker Compose 插值的应用模板占位符（如 $content -> $$content）。"""
    if key.upper() not in _COMPOSE_ESCAPED_ENV_VALUE_KEYS:
        return value

    def _replace(match: re.Match[str]) -> str:
        braced_name = match.group(1)
        plain_name = match.group(2)
        if braced_name is not None:
            return f"$${{{braced_name}}}"
        return f"$${plain_name}"

    return _APPLICATION_TEMPLATE_PLACEHOLDER_PATTERN.sub(_replace, value)


def unescape_compose_sensitive_env_value(key: str, value: str) -> str:
    """还原为 Docker Compose 存储而转义的应用模板占位符（$$content -> $content）。"""
    if key.upper() not in _COMPOSE_ESCAPED_ENV_VALUE_KEYS:
        return value

    def _replace(match: re.Match[str]) -> str:
        braced_name = match.group(1)
        plain_name = match.group(2)
        if braced_name is not None:
            return f"${{{braced_name}}}"
        return f"${plain_name}"

    return _ESCAPED_APPLICATION_TEMPLATE_PLACEHOLDER_PATTERN.sub(_replace, value)


@dataclass
class ConfigLineEntry:
    """单行 `.env` 的结构化表示。

    区分赋值行 / 注释行 / 空行 / 无法识别的原始行，记录 key、value 与是否已更新，
    供 ``ConfigManager`` 在保留注释与格式的前提下原地改写指定键。
    """

    kind: Literal["assignment", "comment", "blank", "raw"]
    raw_line: str
    key: Optional[str] = None
    value: str = ""
    updated: bool = False

    @classmethod
    def parse(cls, raw_line: str) -> "ConfigLineEntry":
        """将一行原始文本解析为对应类型的 ``ConfigLineEntry``。"""
        stripped = raw_line.strip()
        if not stripped:
            return cls(kind="blank", raw_line=raw_line)
        if stripped.startswith("#"):
            return cls(kind="comment", raw_line=raw_line)

        matched = _ASSIGNMENT_PATTERN.match(raw_line)
        if matched:
            return cls(
                kind="assignment",
                raw_line=raw_line,
                key=matched.group(1),
                value=matched.group(2),
            )

        return cls(kind="raw", raw_line=raw_line)

    @classmethod
    def assignment(cls, key: str, value: str) -> "ConfigLineEntry":
        """构造一个已标记的赋值行条目（updated=True）。"""
        return cls(
            kind="assignment",
            raw_line=f"{key}={value}",
            key=key,
            value=value,
            updated=True,
        )

    def render(self) -> str:
        """渲染为字符串：已更新的赋值行输出 ``key=value``，其余保留原始行。"""
        if self.kind == "assignment" and self.updated and self.key is not None:
            return f"{self.key}={self.value}"
        return self.raw_line


class ConfigManager:
    """`.env` 读写管理器，带乐观版本号与原子更新。

    提供读取键值映射、计算文件版本、原子应用更新（临时文件 + rename，失败时回退原地写）。
    线程安全（内部可重入锁）；不负责环境变量装载与配置语义解析。
    """

    def __init__(self, env_path: Optional[Path] = None):
        self._env_path = env_path or self._resolve_env_path()
        self._lock = threading.RLock()

    @property
    def env_path(self) -> Path:
        """返回当前生效的 `.env` 文件路径。"""
        return self._env_path

    def read_config_map(self) -> Dict[str, str]:
        """读取 `.env` 键值映射（会还原 Docker Compose 转义的特殊值）。"""
        return self._read_config_map(normalize_values=True)

    def _read_config_map(self, *, normalize_values: bool) -> Dict[str, str]:
        """读取 `.env` 键值映射的内部实现；``normalize_values`` 控制是否还原 Compose 转义。"""
        if not self._env_path.exists():
            return {}

        raw_values = dotenv_values(self._env_path, interpolate=False)
        if normalize_values:
            values = dotenv_values(self._env_path)
            for raw_key, raw_value in raw_values.items():
                if (
                    raw_key is not None
                    and str(raw_key).upper() in _COMPOSE_ESCAPED_ENV_VALUE_KEYS
                ):
                    values[raw_key] = raw_value
        else:
            values = raw_values
        config_map: Dict[str, str] = {}
        for key, value in values.items():
            if key is None:
                continue
            normalized_key = str(key)
            normalized_value = "" if value is None else str(value)
            if normalize_values:
                normalized_value = unescape_compose_sensitive_env_value(
                    normalized_key,
                    normalized_value,
                )
            config_map[normalized_key] = normalized_value
        return config_map

    def get_config_version(self) -> str:
        """返回基于文件状态（mtime + 内容 sha256）的确定性版本串，用于前端乐观更新。"""
        if not self._env_path.exists():
            return "missing:0"

        content = self._env_path.read_bytes()
        file_stat = self._env_path.stat()
        content_hash = hashlib.sha256(content).hexdigest()
        return f"{file_stat.st_mtime_ns}:{content_hash}"

    def get_updated_at(self) -> Optional[str]:
        """返回 `.env` 最近修改时间（ISO8601 UTC），文件不存在时返回 None。"""
        if not self._env_path.exists():
            return None

        file_stat = self._env_path.stat()
        updated_at = datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc)
        return updated_at.isoformat()

    def apply_updates(
        self,
        updates: Iterable[Tuple[str, str]],
        sensitive_keys: Set[str],
        mask_token: str,
    ) -> Tuple[List[str], List[str], str]:
        """原子（尽可能）应用更新到 `.env` 文件。

        返回（已变更键列表, 因遮罩令牌被跳过的敏感键列表, 新版本串）；
        敏感键收到遮罩令牌且与当前值非空时跳过，其余变更经原子写落盘。
        """
        with self._lock:
            current_values = self.read_config_map()
            stored_values = self._read_config_map(normalize_values=False)
            mutable_updates: Dict[str, str] = {}
            skipped_masked: List[str] = []

            for key, value in updates:
                key_upper = key.upper()
                current_value = current_values.get(key_upper)

                if key_upper in sensitive_keys and value == mask_token:
                    if current_value not in (None, ""):
                        skipped_masked.append(key_upper)
                    continue

                stored_value = stored_values.get(key_upper)
                canonical_stored_value = escape_compose_sensitive_env_value(
                    key_upper,
                    value.replace("\n", ""),
                )
                if current_value == value and (
                    key_upper not in _COMPOSE_ESCAPED_ENV_VALUE_KEYS
                    or stored_value == canonical_stored_value
                ):
                    continue

                mutable_updates[key_upper] = value

            if mutable_updates:
                self._atomic_upsert(mutable_updates)

            return list(mutable_updates.keys()), skipped_masked, self.get_config_version()

    def _atomic_upsert(self, updates: Dict[str, str]) -> None:
        """原子更新：写临时文件后 rename 替换；挂载不支持 rename 时回退原地写。"""
        entries = self._read_entries()
        key_to_index = self._find_last_key_indexes(entries)

        for key, value in updates.items():
            line_value = value.replace("\n", "")
            line_value = escape_compose_sensitive_env_value(key, line_value)
            if key in key_to_index:
                entries[key_to_index[key]] = ConfigLineEntry.assignment(key, line_value)
            else:
                entries.append(ConfigLineEntry.assignment(key, line_value))

        if not self._env_path.parent.exists():
            self._env_path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = self._env_path.with_suffix(self._env_path.suffix + ".tmp")
        content = "\n".join(entry.render() for entry in entries)
        if content and not content.endswith("\n"):
            content += "\n"

        with temp_path.open("w", encoding="utf-8", newline="\n") as file_obj:
            file_obj.write(content)
            file_obj.flush()
            os.fsync(file_obj.fileno())

        try:
            os.replace(temp_path, self._env_path)
        except OSError as exc:
            if exc.errno not in _FALLBACK_REWRITE_ERRNOS:
                raise

            logger.warning(
                "Atomic replace for .env failed with errno=%s, falling back to in-place rewrite",
                exc.errno,
            )
            self._rewrite_in_place(content)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def _rewrite_in_place(self, content: str) -> None:
        """当挂载类型不支持 rename 时，直接原地覆盖写入 `.env` 内容（先 fsync 保持久化）。"""
        with self._env_path.open("w", encoding="utf-8", newline="\n") as file_obj:
            file_obj.write(content)
            file_obj.flush()
            os.fsync(file_obj.fileno())

    def _read_entries(self) -> List[ConfigLineEntry]:
        """把 `.env` 按行解析为 ``ConfigLineEntry`` 列表，保留注释与原始格式。"""
        if not self._env_path.exists():
            return []
        return [
            ConfigLineEntry.parse(raw_line)
            for raw_line in self._env_path.read_text(encoding="utf-8").splitlines()
        ]

    @staticmethod
    def _find_last_key_indexes(entries: List[ConfigLineEntry]) -> Dict[str, int]:
        """返回每个键最后一次出现位置的索引（用于原地更新时定位目标行）。"""
        key_to_index: Dict[str, int] = {}
        for index, entry in enumerate(entries):
            if entry.kind != "assignment" or entry.key is None:
                continue
            key_to_index[entry.key.upper()] = index

        return key_to_index

    @staticmethod
    def _resolve_env_path() -> Path:
        """解析默认 `.env` 路径：优先 ``ENV_FILE`` 环境变量，否则取仓库根目录 ``.env``。"""
        env_file = os.getenv("ENV_FILE")
        if env_file:
            return Path(env_file).resolve()

        return (Path(__file__).resolve().parent.parent.parent / ".env").resolve()
