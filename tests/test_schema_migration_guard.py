# -*- coding: utf-8 -*-
"""W6.1 schema 迁移装配守卫。

`src/infrastructure/persistence/schema_compat.py` 里的 ``ensure_*`` / ``backfill_*``
全部是幂等增量迁移，只有被 :func:`apply_startup_migrations` 串起来才会在启动时
执行。历史上多次出现「新迁移写好但忘记接入启动链」的漂移（函数存在、老库却永远
补不到列），这里用 AST 静态分析锁定三条契约：

1. 模块内每个 ``ensure_*`` / ``backfill_*`` 都必须从 ``apply_startup_migrations``
   可达（直接调用或被其它已接入迁移调用）；
2. 有依赖顺序的迁移必须保持先后：补列早于依赖该列的量纲迁移，基线标记早于
   依赖基线的索引迁移；
3. 所有迁移函数都接收 ``db_session`` 作为第一个参数，禁止悄悄引入全局状态。
"""

from __future__ import annotations

import ast
from pathlib import Path

import src.infrastructure.persistence.schema_compat as schema_compat


def _module_tree() -> ast.Module:
    return ast.parse(Path(schema_compat.__file__).read_text(encoding="utf-8"))


def _functions(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    return {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}


def _called_names(node: ast.AST) -> set[str]:
    return {
        call.func.id
        for call in ast.walk(node)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
    }


def _reachable_from(entry: str, functions: dict[str, ast.FunctionDef]) -> set[str]:
    seen: set[str] = set()
    pending = [entry]
    while pending:
        name = pending.pop()
        if name in seen or name not in functions:
            continue
        seen.add(name)
        pending.extend(_called_names(functions[name]))
    return seen


def test_every_migration_is_wired_into_startup_chain():
    functions = _functions(_module_tree())
    migrations = {
        name for name in functions if name.startswith(("ensure_", "backfill_"))
    }
    reachable = _reachable_from("apply_startup_migrations", functions)

    orphans = sorted(migrations - reachable)
    assert orphans == [], (
        "以下迁移函数没有接入 apply_startup_migrations，老库永远不会执行："
        f"{orphans}"
    )


def test_apply_startup_migrations_keeps_documented_order():
    functions = _functions(_module_tree())
    body = functions["apply_startup_migrations"]

    ordered_calls: list[str] = []
    for node in ast.walk(body):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            ordered_calls.append(node.func.id)

    def position(name: str) -> int:
        assert name in ordered_calls, f"{name} 未出现在 apply_startup_migrations"
        return ordered_calls.index(name)

    # importance 补列必须早于依赖该列的量纲迁移
    assert position("ensure_intelligence_item_importance_column") < position(
        "ensure_live_news_importance_rescaled"
    )
    # 结构补列 -> 基线标记 -> 依赖基线的索引迁移
    assert position("ensure_llm_usage_telemetry_columns") < position(
        "ensure_schema_migration_record"
    )
    assert position("ensure_decision_signal_profile_schema") < position(
        "ensure_schema_migration_record"
    )
    assert position("ensure_schema_migration_record") < position(
        "ensure_intelligence_items_unique_index"
    )


def test_migration_functions_take_db_session_first():
    functions = _functions(_module_tree())
    offenders: list[str] = []
    for name, node in functions.items():
        if not name.startswith(("ensure_", "backfill_")):
            continue
        args = [arg.arg for arg in node.args.args]
        if not args or args[0] != "db_session":
            offenders.append(name)
    assert offenders == [], f"迁移函数第一个参数必须是 db_session: {offenders}"


def test_baseline_record_uses_current_version_constant():
    source = Path(schema_compat.__file__).read_text(encoding="utf-8")
    # 基线版本必须引用常量，禁止在函数里写死历史日期字符串
    assert '"version": CURRENT_SCHEMA_VERSION' in source
    assert schema_compat.CURRENT_SCHEMA_VERSION
