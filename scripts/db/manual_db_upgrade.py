#!/usr/bin/env python3
r"""手动初始化或升级 Java 服务的 SQLite 数据库（Python 3.9+，只依赖标准库）。

一、通用性与使用方式
====================
后续 Java 服务只要按下面的文件、命名、版本与 SQL 约定编写，就可以复用此工具，
不需要为新服务或新增版本修改 Python 的版本列表，更不需要在 Java 中添加升级逻辑。
“通用”指复用同一套检查和执行流程，不表示任意 SQL、任意旧库都可以直接拿来升级。
本工具不会启动 Java、不读取 .env、不扫描执行目录中的所有 SQL，目前不支持 MySQL。

命令示例（路径由执行者确认，写入前先停止目标服务的业务写入）：
    python3 scripts/db/manual_db_upgrade.py --service hrs-system-service \
        --database /absolute/path/hrs_system.db --plan
    python3 scripts/db/manual_db_upgrade.py --service hrs-system-service \
        --database /absolute/path/hrs_system.db --apply --create
    python3 scripts/db/manual_db_upgrade.py --service hrs-system-service \
        --database /absolute/path/hrs_system.db --apply --backup-dir /absolute/path/backups
    python3 scripts/db/manual_db_upgrade.py --service hrs-system-service \
        --database /absolute/path/hrs_system.db --adopt-baseline --backup-dir /absolute/path/backups

--plan：在内存副本模拟，检查语法、结构、历史与业务断言，不写业务数据或执行历史，
        不创建目标库、不做备份。WAL 库可能需要 SQLite 引擎建立 -wal/-shm 辅助文件，
        因此不承诺数据库所在目录的文件列表完全不变，也不会用 immutable 忽略 WAL。
--apply --create：明确允许新建数据库；父目录必须预先存在，不覆盖或清空已有库。
--apply：升级已有库；有待办时必须提供 --backup-dir，先一致性备份再执行 SQL。
        无待办则不重放 SQL、不重复登记、不做备份，也不强制提供备份目录。
--adopt-baseline：仅适用于完整匹配初始基线、却没有执行历史的已有库；先备份，
                 只登记已有基线，不重建表，不执行后续升级段。其他未知旧库拒绝接管。
以上三种主操作 plan/apply/adopt-baseline 互斥；create 只与 apply 配合。
数据库和备份目录都传绝对路径。每个服务只操作自己的库，不指向 Python 分析库。

二、文件位置、服务名与对象命名
==============================
1. 服务名采用 hrs-<名称>-service，名称为小写字母/数字及用连字符分隔的单词，
   首字符必须是字母；例如 hrs-system-service、hrs-order-center-service。
   服务名不能包含目录、斜杠、点号或下划线。
2. 工具只读取 <服务名>/sql/<服务名>.sql，例如：
       hrs-system-service/sql/hrs-system-service.sql
   不因 sql/ 目录里有多个文件就全部执行。auth/analysis 当前的空占位 SQL 不会被执行。
3. 文件头必须各出现一次，内容与命令选择的服务完全匹配：
       -- @service hrs-system-service
       -- @dialect sqlite
4. 业务表/视图及所引用的业务表必须属于本服务前缀：
       hrs-system-service       -> hrs_system_...
       hrs-order-center-service -> hrs_order_center_...
   索引、触发器也只能作用于本服务的表；索引名等遵循 database_rules.md 的约定。
   工具不是数据库建模规范检查器：它不会自动补齐所有业务字段或审计字段。
   本项目业务表仍须包含 id、delete_flag、enterprise_id、organization_id 与审计列，
   类型、默认值、可空策略、唯一性和软删除规则以 documents/DB/database_rules.md 为准。
5. <前缀>schema_history 是工具技术表，例如 hrs_system_schema_history。
   正式 SQL 和业务验证都不能自行创建、读取、修改或删除它，由工具统一维护。

三、版本段必须怎样编写
======================
1. 每段使用配对标记，标记各占一行，不嵌套、不重号：
       -- BEGIN BASELINE_EXAMPLE
       ...本段元信息与 SQL...
       -- END BASELINE_EXAMPLE
   编号以大写英文字母开头，后续只能是大写字母、数字、下划线；不写日期点号或连字符。
2. 首段是基线，必须创建本服务的业务表。其 @upgrade JSON 中：
       kind 为 "baseline"，requires 为 []。
   后续段的 kind 为 "migration"，requires 必须恰好包含紧邻前一段的编号。
   这是一条按文件顺序追加的升级链，不支持同时存在的多个版本分支。
3. 每段恰好一行 -- @upgrade JSON；JSON 必须保持在一行，不能写成多行或带尾逗号。
   允许的字段只有：
       description：必填，非空说明，最多 256 字符。
       kind：必填，baseline 或 migration，遵循上面的首段/后续段规则。
       requires：必填，编号字符串数组，遵循上面的依赖规则。
       verify：可选，只读 SQL 字符串数组，默认 []，详见第五节。
4. 可执行 SQL 全部放在版本段内，每条正文语句用分号结束。
   字符串、注释和触发器内部可以有分号，工具使用 SQLite 的完整语句边界识别它们。
   文件头/尾只放普通注释和允许的文件级元信息，不放裸 CREATE/INSERT 等语句。
5. 整个文件必须能从空 SQLite 库顺序重放：前面的段定义后面要用到的对象，
   所有升级所需的函数、语法和对象都必须可用。不能依赖开发机临时手建的表、
   未加载的扩展或外部数据库。数据转换可以引用已有业务行，但结构不能依赖偶然的数据。
   verify 在执行对应段的真实数据/预检副本上校验，不在空的规范库里推断业务数据。
6. 一旦某段执行并登记，其 SQL、元信息、段内注释和空白都不要再修改，
   因为它们都参与 SHA-256。统一换行后计算摘要，新增段不会改变旧段摘要。
   后续变化向文件末尾追加新段；合并分支时核对编号唯一及相邻依赖，不删除历史段。
   文件级 @final-check 不属于某个旧段的摘要，可随当前终态契约调整。

四、哪些 SQL 可以写，哪些不能写
===============================
可以使用（还须满足运行工具的 Python 内置 SQLite 版本及前述服务边界）：
- 普通 CREATE TABLE、CREATE INDEX、CREATE VIEW、CREATE TRIGGER。
- SQLite 支持的 ALTER TABLE，例如新增/重命名/删除列；不等于支持所有 MySQL 改表语法。
- INSERT、UPDATE、DELETE、INSERT ... SELECT 等数据初始化和转换语句。
- 本服务内必要的 DROP、表重建和数据复制，但必须明确保留字段、约束、索引与数据，
  不能仅因建表方便就丢弃实际业务数据。工具的事务/备份不能代替迁移设计。
- SELECT/WITH 查询及只读业务断言；视图和触发器的查询/写入同样不能跨服务。

工具明确禁止，不能放入正式 SQL 正文或断言：
- BEGIN、COMMIT、END TRANSACTION、ROLLBACK、SAVEPOINT、RELEASE 等事务控制；
  它们由工具统一管理，否则无法保证业务变更和历史记录一起回滚。
- PRAGMA；foreign_keys、journal_mode 等不能在版本文件中自行切换。
- ATTACH、DETACH、跨服务表操作、TEMP/TEMPORARY 对象、CREATE/DROP VIRTUAL TABLE。
- 操作工具历史表，或通过 load_extension/readfile/writefile/eval 装载扩展、读写文件。

当前流程也不支持：
- MySQL/MariaDB 专有语法，如 ENGINE、AUTO_INCREMENT、存储过程、DELIMITER 等。
- VACUUM 这类不能在当前受控事务内执行的维护操作；应另行安排，不混入升级段。
- Python/Shell/Java 代码、命令行客户端的 .read/.bail 等元命令。
- 不能在内存规范库重放，或依赖本工具未装配的自定义函数/扩展的 SQL。
Java SQLite 驱动支持某种语法，不代表运行本工具的 Python 内置 SQLite 也支持它。

项目写法约定（这些不是每一项都由工具自动拦截，仍需要开发者审查）：
- 不用 INSERT OR REPLACE 随意覆盖用户配置或改变记录 ID，不以 OR IGNORE 掩盖错误。
- 初始化数据使用明确的稳定业务键，不能按展示名称猜记录，不插入默认密码或真实密钥。
- CREATE TABLE/INDEX IF NOT EXISTS 不会修正已有对象定义，不能拿它代替字段升级。
- 不要求每条 ALTER 自身能裸执行两次；重复运行由执行历史决定跳过哪些完整版本段。
- 只读断言、事务和结构比对不证明数据转换的业务含义正确；仍须验证保留的数据。

五、如何验证，以及工具何时会拒绝执行
====================================
工具在内存从空库重放全部版本，得到各历史位置应有的表、索引、视图和触发器定义。
实际库必须与其已登记历史所对应的规范结构一致；同名对象定义不同、缺字段、
额外未知表、历史编号缺失/乱序或已执行段摘要变化都会报错，不自动删表、补列或清库。
比较忽略 SQL 注释、空白和未引用标识符大小写，保留字符串常量；并非任意语义等价的
DDL 都能被认定相同。没有执行历史的非空库默认拒绝，准确匹配初始基线才可显式接管。

verify：每个字符串是一条只读 SELECT/WITH，必须返回一行一列的成功值 1；
        建议写比较表达式，例如 SELECT COUNT(*) = 0 FROM ... WHERE ...。
        对应段执行后验证，不在后续版本上重复检查可能已失效的旧断言。
@final-check：每条单独一行，位于版本段外，例如：
       -- @final-check SELECT COUNT(*) = 0 FROM hrs_example_item WHERE display_name IS NULL
        用于当前完整版本的数据条件；即使无待办、仅重复运行，也会检查。
断言不能写 UPDATE/DELETE，不能读取升级历史，不能期待查询结果是列表或展示文本。
结构验证已经覆盖正式 DDL，业务断言应重点检查数据转换、空值、数量和关联不变量。

以下是另一个服务的完整格式示例，仅供参考，不会被本脚本自动执行。
若用于新服务，请同时调整目录、服务声明、表前缀、变更编号和实际业务字段：

    -- @service hrs-example-service
    -- @dialect sqlite
    -- BEGIN BASELINE_EXAMPLE
    -- @upgrade {"description":"创建示例表","kind":"baseline","requires":[],"verify":[]}
    CREATE TABLE hrs_example_item (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(64) NOT NULL CHECK(length(name) BETWEEN 1 AND 64),
        enterprise_id BIGINT CHECK(enterprise_id IS NULL OR enterprise_id > 0),
        organization_id BIGINT CHECK(organization_id IS NULL OR organization_id > 0),
        delete_flag INTEGER NOT NULL DEFAULT 0 CHECK(delete_flag IN (0, 1)),
        create_by VARCHAR(64) NOT NULL,
        update_by VARCHAR(64) NOT NULL,
        create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    -- END BASELINE_EXAMPLE

    -- BEGIN EXAMPLE_001
    -- @upgrade {"description":"补充展示名","kind":"migration","requires":["BASELINE_EXAMPLE"],"verify":["SELECT COUNT(*) = 0 FROM hrs_example_item WHERE display_name IS NULL"]}
    ALTER TABLE hrs_example_item ADD COLUMN display_name VARCHAR(64);
    UPDATE hrs_example_item SET display_name = name;
    -- END EXAMPLE_001
    -- @final-check SELECT COUNT(*) = 0 FROM hrs_example_item WHERE display_name IS NULL

六、日常变更顺序与失败恢复
==========================
先审查 SQL、追加新版本并运行临时库测试，再 plan；停止目标服务写入后 apply。
apply 会取得写锁后重新检查历史和结构，再通过另一连接一致性备份，最后执行待办。
全部受支持的变更及其历史在同一事务提交，失败整批回滚，已有成功备份予以保留。
新库初始化失败可能留下空文件，工具会报告，不会擅自删除或覆盖已有数据库。
成功提交后若需退回旧版本，保持停写，按方案恢复备份并配套回退代码；工具不自动降级。
完整的备份恢复和后续 MySQL 方案见 documents/DB/sql_management_and_execution_plan.md。

阅读代码顺序：main → run → inspect_database / execute_pending。
"""

from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
from typing import Callable
import uuid

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICE_RE = re.compile(r"hrs-([a-z][a-z0-9]*(?:-[a-z0-9]+)*)-service")
BOUNDARY_RE = re.compile(r"-- (BEGIN|END) ([A-Z][A-Z0-9_]*)")
# 词法归一化只忽略注释、空白及未引用标识符的大小写，不改字符串常量。
# 因此 Java 执行器是否保留 SQL 注释，不会造成基线接管时的结构误判。
TOKEN_RE = re.compile(
    r"--[^\n]*(?:\n|$)|/\*[\s\S]*?\*/|'(?:''|[^'])*'|"
    r'"(?:""|[^"])*"|`(?:``|[^`])*`|\[[^\]]*\]|[A-Za-z_][A-Za-z_0-9]*|[^\s]'
)
Schema = tuple[tuple[str, str, str, tuple[str, ...]], ...]


class UpgradeError(Exception):
    """可直接给操作者看的错误；命令行不打印堆栈或业务数据。"""


def allow_internal_sql(*_args) -> int:
    """恢复工具自身 SQL 的权限。

    Python 3.9 的标准库尚不支持 set_authorizer(None) 解除回调；使用显式允许的
    回调同样能恢复权限，并让工具只依赖 Python 3.9+ 的标准库。
    """
    return sqlite3.SQLITE_OK


@dataclass(frozen=True)
class Change:
    """一个不可拆开的变更段；checksum 包含 SQL、说明、依赖与校验声明。"""

    name: str
    description: str
    kind: str
    checks: tuple[str, ...]
    statements: tuple[str, ...]
    checksum: str


@dataclass(frozen=True)
class Bundle:
    """从一个正式 SQL 文件构建的执行契约，没有在 Python 中写死版本编号。"""

    service: str
    prefix: str
    history_table: str
    path: Path
    changes: tuple[Change, ...]
    schemas: tuple[Schema, ...]  # 第 0 项为空库，第 n 项为执行前 n 段后的规范结构。
    final_checks: tuple[str, ...]


def tokens(sql: str) -> tuple[str, ...]:
    """将 SQL 结构定义归一化；保留常量和引用标识符的原意。"""
    return tuple(
        item.lower() if item[0].isalpha() or item[0] == "_" else item
        for item in TOKEN_RE.findall(sql)
        if not item.startswith(("--", "/*"))
    )


def split_statements(sql: str) -> tuple[str, ...]:
    """使用 SQLite 判断语句边界，不能直接按分号 split。

    字符串、注释和触发器内部都可能出现分号。complete_statement 只判断边界，
    真正语法验证由稍后的内存执行完成。要求最后一条语句也有分号，避免半段 SQL。
    """
    statements = []
    start = 0
    for end, character in enumerate(sql):
        if character == ";" and sqlite3.complete_statement(sql[start:end + 1]):
            statement = sql[start:end + 1]
            if tokens(statement):
                statements.append(statement)
            start = end + 1
    if tokens(sql[start:]):
        raise UpgradeError("SQL 语句未完整结束，请检查引号、注释及末尾分号")
    return tuple(statements)


def history_sql(table: str) -> str:
    """历史表是工具元数据，不是业务表，不添加租户字段或逻辑删除字段。"""
    return f"""CREATE TABLE {table} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_name TEXT NOT NULL,
        change_id TEXT NOT NULL UNIQUE,
        checksum TEXT NOT NULL,
        description TEXT NOT NULL,
        completion_kind TEXT NOT NULL CHECK(completion_kind IN ('applied','adopted')),
        completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )"""


def schema_snapshot(db: sqlite3.Connection, excluded: str = "") -> Schema:
    """比较表、显式索引、触发器和视图的定义，不比较用户数据或自增计数。

    内部 autoindex 的约束已经包含在 CREATE TABLE 中，sqlite_sequence 是 SQLite
    自身元数据。额外业务对象仍会被检测到，不能用此工具“顺带”改另一服务的库。
    """
    return tuple(
        (kind, name, table, tokens(sql))
        for kind, name, table, sql in db.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' AND name <> ? ORDER BY type,name", (excluded,)
        )
    )


def authorizer(bundle: Bundle, readonly: bool = False) -> Callable:
    """限制业务 SQL 的作用范围，并保护工具自己的事务与历史表。

    这是防止误操作的护栏，不把版本文件视为可运行任意 Python/Shell 的程序。
    不允许 SQL 自己提交事务、ATTACH 其他库、改 PRAGMA 或装载扩展。
    """
    forbidden = {sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH,
                 sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT, sqlite3.SQLITE_PRAGMA,
                 sqlite3.SQLITE_CREATE_VTABLE, sqlite3.SQLITE_DROP_VTABLE}
    writes = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE}
    creates = {sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_DROP_TABLE,
               sqlite3.SQLITE_CREATE_VIEW, sqlite3.SQLITE_DROP_VIEW}
    related = {sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_DROP_INDEX,
               sqlite3.SQLITE_CREATE_TRIGGER, sqlite3.SQLITE_DROP_TRIGGER}
    temporary = {sqlite3.SQLITE_CREATE_TEMP_TABLE, sqlite3.SQLITE_DROP_TEMP_TABLE,
                 sqlite3.SQLITE_CREATE_TEMP_INDEX, sqlite3.SQLITE_DROP_TEMP_INDEX,
                 sqlite3.SQLITE_CREATE_TEMP_VIEW, sqlite3.SQLITE_DROP_TEMP_VIEW,
                 sqlite3.SQLITE_CREATE_TEMP_TRIGGER, sqlite3.SQLITE_DROP_TEMP_TRIGGER}

    def check(action, first, second, database, trigger):
        if action in forbidden or action in temporary:
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_FUNCTION and (second or "").lower() in {
            "load_extension", "readfile", "writefile", "eval"
        }:
            return sqlite3.SQLITE_DENY
        table = None
        if action in writes or action == sqlite3.SQLITE_READ or action in creates:
            table = first
        elif action in related or action == sqlite3.SQLITE_ALTER_TABLE:
            table = second
        if table == bundle.history_table:
            return sqlite3.SQLITE_DENY
        # SQLite重命名表时会读取并更新临时schema目录，即使没有临时业务表。
        # 只放行目录的READ/UPDATE；临时表创建、其他库与事务仍由上面的规则拦截。
        if database == "temp" and table in {"sqlite_temp_master", "sqlite_temp_schema"}:
            return sqlite3.SQLITE_OK if action == sqlite3.SQLITE_READ or (not readonly and action == sqlite3.SQLITE_UPDATE) else sqlite3.SQLITE_DENY
        if table and table not in {"sqlite_master", "sqlite_schema", "sqlite_sequence"}:
            if not table.startswith(bundle.prefix) or database not in (None, "main"):
                return sqlite3.SQLITE_DENY
        if readonly and (action in writes or action in creates or action in related
                         or action == sqlite3.SQLITE_ALTER_TABLE):
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    return check


def execute_change(db: sqlite3.Connection, bundle: Bundle, change: Change) -> None:
    """逐条 execute，不使用可能隐式提交外层事务的 executescript。"""
    db.set_authorizer(authorizer(bundle))
    try:
        for number, statement in enumerate(change.statements, 1):
            try:
                db.execute(statement).close()
            except sqlite3.Error as exc:
                raise UpgradeError(f"变更 {change.name} 的第 {number} 条 SQL 失败：{exc}") from exc
    finally:
        db.set_authorizer(allow_internal_sql)


def verify_queries(db: sqlite3.Connection, bundle: Bundle, checks: tuple[str, ...], label: str) -> None:
    """业务断言必须是单条只读 SELECT/WITH，并返回一行一列的整数 1。"""
    db.set_authorizer(authorizer(bundle, readonly=True))
    try:
        for number, query in enumerate(checks, 1):
            if not tokens(query) or tokens(query)[0] not in ("select", "with"):
                raise UpgradeError(f"{label} 的第 {number} 条验证必须是只读 SELECT/WITH")
            result = db.execute(query).fetchmany(2)
            if result != [(1,)]:
                raise UpgradeError(f"{label} 的第 {number} 条验证未通过")
    except sqlite3.Error as exc:
        raise UpgradeError(f"{label} 的只读验证执行失败：{exc}") from exc
    finally:
        db.set_authorizer(allow_internal_sql)


def load_bundle(service: str, root: Path = REPO_ROOT) -> Bundle:
    """只读取选定服务的固定文件；解析严格边界和少量注释元信息。"""
    match = SERVICE_RE.fullmatch(service)
    if not match:
        raise UpgradeError("服务名必须为 hrs-<名称>-service，不能包含目录或路径")
    prefix = "hrs_" + match.group(1).replace("-", "_") + "_"
    path = root / service / "sql" / f"{service}.sql"
    if not path.is_file() or path.resolve().parent != (root / service / "sql").resolve():
        raise UpgradeError(f"找不到本服务的正式 SQL：{path}")
    text = path.read_text(encoding="utf-8-sig")
    current = None
    blocks = []
    outside = []
    for line in text.splitlines():
        boundary = BOUNDARY_RE.fullmatch(line.strip())
        if boundary:
            operation, name = boundary.groups()
            if operation == "BEGIN":
                if current is not None or any(name == block[0] for block in blocks):
                    raise UpgradeError(f"SQL 段嵌套或编号重复：{name}")
                current = (name, [line])
            else:
                if current is None or name != current[0]:
                    raise UpgradeError(f"SQL 段结束标记不匹配：{name}")
                current[1].append(line)
                blocks.append((name, current[1]))
                current = None
        elif current is not None:
            current[1].append(line)
        else:
            outside.append(line)
    if current is not None:
        raise UpgradeError(f"SQL 段未结束：{current[0]}")
    if not blocks:
        raise UpgradeError("此服务尚未启用数据库变更，SQL 仅为占位；不会创建数据库")
    if tokens("\n".join(outside)):
        raise UpgradeError("可执行 SQL 必须位于 BEGIN/END 段内")
    headers = {"service": [], "dialect": [], "final-check": []}
    for line in outside:
        if line.strip().startswith("-- @"):
            key, _, value = line.strip()[4:].partition(" ")
            if key not in headers or not value.strip():
                raise UpgradeError(f"未知或空的文件元信息：{key}")
            headers[key].append(value.strip())
    if headers["service"] != [service] or headers["dialect"] != ["sqlite"]:
        raise UpgradeError("SQL 必须唯一声明匹配的 @service 和 @dialect sqlite")
    changes = []
    for name, lines in blocks:
        metadata = [line.strip()[12:] for line in lines if line.strip().startswith("-- @upgrade ")]
        if len(metadata) != 1:
            raise UpgradeError(f"{name} 必须有一行 -- @upgrade JSON 元信息")
        info = json.loads(metadata[0])
        if not isinstance(info, dict) or set(info) - {"description", "kind", "requires", "verify"}:
            raise UpgradeError(f"{name} 的元信息字段不正确")
        description = info.get("description")
        kind = "baseline" if not changes else "migration"
        required = [] if not changes else [changes[-1].name]
        checks = info.get("verify", [])
        if (not isinstance(description, str) or not description.strip() or len(description) > 256
                or info.get("kind") != kind or info.get("requires") != required
                or not isinstance(checks, list) or any(not isinstance(c, str) or not c.strip() for c in checks)):
            raise UpgradeError(f"{name} 的说明、kind、依赖或 verify 不正确；后续段必须依赖紧邻前一段")
        for line in lines:
            if line.strip().startswith("-- @") and not line.strip().startswith("-- @upgrade "):
                raise UpgradeError(f"{name} 包含未知元信息")
        statements = split_statements("\n".join(lines[1:-1]))
        if not statements:
            raise UpgradeError(f"{name} 不能是空变更")
        checksum = hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()
        changes.append(Change(name, description, kind, tuple(checks), statements, checksum))
    bundle = Bundle(service, prefix, prefix + "schema_history", path, tuple(changes), (), tuple(headers["final-check"]))
    # 在内存重放全部变更，提前发现语法错误并生成每个历史位置应有的结构。
    # 此处不运行依赖真实历史数据的业务断言，也不生成业务账号或连接实际库。
    with closing(sqlite3.connect(":memory:", isolation_level=None)) as reference:
        reference.execute("PRAGMA foreign_keys=ON")
        reference.execute("BEGIN IMMEDIATE")
        schemas = [schema_snapshot(reference)]
        for change in bundle.changes:
            execute_change(reference, bundle, change)
            schemas.append(schema_snapshot(reference))
        reference.rollback()
    if not any(entry[0] == "table" for entry in schemas[1]):
        raise UpgradeError("初始基线必须定义本服务的业务表，不能只登记空版本")
    return Bundle(service, prefix, bundle.history_table, path, bundle.changes, tuple(schemas), bundle.final_checks)


def check_integrity(db: sqlite3.Connection) -> None:
    """integrity_check 不包含外键检查，因此两项必须分别执行。"""
    if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise UpgradeError("数据库完整性检查失败，请先排查或恢复数据库")
    if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise UpgradeError("数据库存在外键不一致，请先排查数据")


def inspect_database(db: sqlite3.Connection, bundle: Bundle, adopt: bool = False) -> int:
    """返回已完成段数；任何历史、摘要或规范结构冲突都明确拒绝。

    实际结构应等于已登记历史前缀对应的结构。这样加字段无需写 Python 版本分支，
    已有字段缺失、同名索引定义错误、额外表及手工改列也不会被悄悄忽略。
    """
    check_integrity(db)
    actual = schema_snapshot(db, bundle.history_table)
    row = db.execute("SELECT sql FROM sqlite_master WHERE name=?", (bundle.history_table,)).fetchone()
    if row is None:
        if adopt:
            if actual != bundle.schemas[1]:
                raise UpgradeError("无历史库不完全匹配初始基线，不能接管；不会重建或清空旧表")
            return 0
        if actual:
            raise UpgradeError("发现无执行历史的非空库；匹配基线的库需显式 --adopt-baseline，其他旧库须专门迁移")
        return 0
    if adopt:
        raise UpgradeError("此库已有执行历史，不需要再次接管基线")
    if tokens(row[0]) != tokens(history_sql(bundle.history_table)):
        raise UpgradeError("执行历史表结构不符合工具协议")
    history = db.execute(
        f"SELECT service_name,change_id,checksum,description,completion_kind FROM {bundle.history_table} ORDER BY id"
    ).fetchall()
    if not history or len(history) > len(bundle.changes):
        raise UpgradeError("执行历史为空或包含本 SQL 文件未知的版本，拒绝操作")
    for recorded, change in zip(history, bundle.changes):
        if recorded[:4] != (bundle.service, change.name, change.checksum, change.description):
            raise UpgradeError(f"执行历史或已执行 SQL 摘要不匹配：{change.name}")
        if recorded[4] not in ("applied", "adopted") or (recorded[4] == "adopted" and change.kind != "baseline"):
            raise UpgradeError("执行历史完成类型不正确")
    expected = bundle.schemas[len(history)]
    if actual != expected:
        names = sorted({entry[1] for entry in actual} ^ {entry[1] for entry in expected})
        detail = "，对象名差异：" + ", ".join(names[:8]) if names else "，存在同名对象定义差异"
        raise UpgradeError("实际结构与已登记版本不一致" + detail)
    return len(history)


def record_change(db: sqlite3.Connection, bundle: Bundle, change: Change, kind: str) -> None:
    """只能在变更成功且验证通过后登记，并与业务 SQL 一起提交。"""
    db.execute(f"INSERT INTO {bundle.history_table} "
               "(service_name,change_id,checksum,description,completion_kind) VALUES (?,?,?,?,?)",
               (bundle.service, change.name, change.checksum, change.description, kind))


def execute_pending(db: sqlite3.Connection, bundle: Bundle, completed: int, adopt: bool) -> int:
    """由调用者提供事务；本函数绝不自行 commit，也不吞掉失败继续下一段。"""
    if completed == 0:
        db.execute(history_sql(bundle.history_table))
    if adopt:
        verify_queries(db, bundle, bundle.changes[0].checks, bundle.changes[0].name)
        record_change(db, bundle, bundle.changes[0], "adopted")
        # 接管只登记已有基线，不顺带执行后来追加的升级段。
        return 1
    for index, change in enumerate(bundle.changes[completed:], completed + 1):
        execute_change(db, bundle, change)
        verify_queries(db, bundle, change.checks, change.name)
        if schema_snapshot(db, bundle.history_table) != bundle.schemas[index]:
            raise UpgradeError(f"{change.name} 执行后的结构与规范结构不一致")
        record_change(db, bundle, change, "applied")
    verify_queries(db, bundle, bundle.final_checks, "最终业务断言")
    check_integrity(db)
    return len(bundle.changes) - completed


def connect_file(path: Path, mode: str, timeout: float) -> sqlite3.Connection:
    """URI 正确编码路径；ro/rw 都不创建不存在的数据库。

    SQLite 的 WAL 库在干净关闭后可能没有 -wal/-shm；本机 SQLite 此时不能以
    mode=ro 重新建立日志辅助文件。先由 SQLite 探测读取；仅当报告无法打开且
    辅助文件缺失时，改用 rw 加 query_only，仍禁止业务写入。不使用 immutable。

    不能用普通 open/read/close 检查数据库文件头：POSIX close 可能释放本进程
    另一 SQLite 连接持有的文件锁。所有数据库文件访问都必须经过同一 SQLite 库，
    由其 VFS 统一管理描述符和锁，备份时也不能绕开这一点。
    """
    requested_readonly = mode == "ro"

    def connect(open_mode: str) -> sqlite3.Connection:
        db = sqlite3.connect(path.as_uri() + f"?mode={open_mode}", uri=True,
                             isolation_level=None, timeout=timeout)
        try:
            db.execute("PRAGMA foreign_keys=ON")
            if requested_readonly:
                db.execute("PRAGMA query_only=ON")
                # connect 和以上 PRAGMA 不一定真正读取库，此查询用于尽早识别 WAL 打开问题。
                db.execute("SELECT name FROM sqlite_master LIMIT 0").close()
            return db
        except BaseException:
            db.close()
            raise

    try:
        return connect(mode)
    except sqlite3.OperationalError as exc:
        code = getattr(exc, "sqlite_errorcode", None)
        # Python 3.9 尚无 sqlite_errorcode，只对 SQLite 的明确 CANTOPEN 文案使用同一处理。
        cannot_open = ((code is not None and code & 0xff == sqlite3.SQLITE_CANTOPEN)
                       or (code is None and str(exc) == "unable to open database file"))
        missing_auxiliary = not all(Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm"))
        if not requested_readonly or not cannot_open or not missing_auxiliary:
            raise
        return connect("rw")


def copy_database(source: sqlite3.Connection, destination: sqlite3.Connection, timeout: float) -> None:
    """一致性备份，并为锁竞争设置总等待上限，避免备份一直挂住。"""
    deadline = time.monotonic() + timeout

    def progress(status, remaining, total):
        if status != sqlite3.SQLITE_DONE and time.monotonic() >= deadline:
            raise UpgradeError("备份超时，请确认目标服务已停写后重试")

    source.backup(destination, pages=128, progress=progress, sleep=min(timeout, 0.05))


def make_backup(path: Path, directory: Path, bundle: Bundle, timeout: float) -> Path:
    """调用前已由另一连接取得写锁，备份只读连接看到的稳定提交快照。

    不能对持有写事务的同一连接调用 backup，那可能一直等待自己释放锁。
    不用文件复制，所以 WAL 中尚未 checkpoint 的已提交记录也在快照内。
    """
    directory.mkdir(parents=True, exist_ok=True)
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = directory / f"{bundle.service}_{name}_{uuid.uuid4().hex[:8]}.db"
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        with closing(connect_file(path, "ro", timeout)) as source:
            with closing(connect_file(target, "rw", timeout)) as destination:
                copy_database(source, destination, timeout)
                check_integrity(destination)
    except BaseException:
        target.unlink(missing_ok=True)  # 只移除本函数独占创建的未完成备份。
        raise
    return target


def absolute_path(value: str, label: str) -> Path:
    """拒绝相对路径、文件级软链接和非普通文件，减少指错数据库的机会。"""
    path = Path(value).expanduser()
    if not path.is_absolute() or path.is_symlink():
        raise UpgradeError(f"{label}必须是明确的绝对路径，不能是文件软链接")
    return path.resolve()


def run(args: argparse.Namespace, root: Path = REPO_ROOT, emit: Callable[[str], None] = print) -> None:
    """先在内存副本预检，再取得真实写锁、复查和备份，最后在同一事务升级。"""
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        raise UpgradeError("timeout 必须是有限正数")
    bundle = load_bundle(args.service, root)
    database = absolute_path(args.database, "数据库路径")
    expected_name = bundle.prefix.rstrip("_") + ".db"
    if database.name == "stock_analysis.db" or (
        re.fullmatch(r"hrs_(system|auth|analysis)\.db", database.name) and database.name != expected_name
    ):
        raise UpgradeError("数据库文件名属于另一服务，拒绝操作")
    if database.exists() and not database.is_file():
        raise UpgradeError("数据库路径不是普通文件")
    if args.create and not args.apply:
        raise UpgradeError("--create 只能和 --apply 一起使用")
    backup_dir = absolute_path(args.backup_dir, "备份目录") if args.backup_dir else None
    emit(f"服务：{bundle.service}\n数据库：{database}\nSQL：{bundle.path}")
    # plan 及 apply 的预检都仅在内存副本运行。SQL 或数据断言失败时真实库尚未写入。
    with closing(sqlite3.connect(":memory:", isolation_level=None)) as preview:
        preview.execute("PRAGMA foreign_keys=ON")
        if database.exists():
            with closing(connect_file(database, "ro", args.timeout)) as source:
                copy_database(source, preview, args.timeout)
        elif args.adopt_baseline or (args.apply and not args.create):
            raise UpgradeError("目标库不存在；新建须显式 --apply --create")
        completed = inspect_database(preview, bundle, args.adopt_baseline)
        preview.execute("BEGIN IMMEDIATE")
        try:
            count = execute_pending(preview, bundle, completed, args.adopt_baseline)
        finally:
            preview.rollback()
    for index, change in enumerate(bundle.changes):
        status = "已完成，跳过" if index < completed else "待执行"
        if args.adopt_baseline:
            status = "仅登记基线" if index == 0 else "本次不执行"
        emit(f"  {status}：{change.name} — {change.description}")
    if args.plan:
        emit(f"预览通过：{count} 项待办；没有写入目标数据库。")
        return
    existed = database.exists()
    if existed and count and backup_dir is None:
        raise UpgradeError("已有库变更必须提供 --backup-dir；请先停止该服务写入")
    if not existed:
        if not database.parent.is_dir():
            raise UpgradeError("数据库父目录不存在，请由执行者先创建")
        # O_EXCL 防止检查后另一个进程恰好创建了同一路径；不覆盖已有文件。
        descriptor = os.open(database, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
    try:
        with closing(connect_file(database, "rw", args.timeout)) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                completed = inspect_database(db, bundle, args.adopt_baseline)
                pending = 1 if args.adopt_baseline else len(bundle.changes) - completed
                if existed and pending:
                    if backup_dir is None:
                        raise UpgradeError("复查发现新的待办，必须提供 --backup-dir")
                    backup = make_backup(database, backup_dir, bundle, args.timeout)
                    emit(f"升级前一致性备份：{backup}")
                count = execute_pending(db, bundle, completed, args.adopt_baseline)
                db.commit()
            except BaseException:
                db.rollback()
                raise
    except BaseException:
        if not existed:
            emit("新库初始化失败；本次事务已回滚，目标路径可能留下空库文件，请核对后再处理。")
        raise
    emit(f"完成：新增登记 {count} 项，已完成跳过 {completed} 项。")


def parser() -> argparse.ArgumentParser:
    """不提供默认写模式，必须显式选择一个操作；所有数据库地址由参数传入。"""
    command = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    command.add_argument("--service", required=True, help="服务名，例如 hrs-system-service")
    command.add_argument("--database", required=True, help="SQLite 文件绝对路径，不是 JDBC URL")
    mode = command.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true", help="只读预览，在内存副本模拟，不创建目标库")
    mode.add_argument("--apply", action="store_true", help="手动执行，已有库变更前必须备份")
    mode.add_argument("--adopt-baseline", action="store_true", help="仅接管完全匹配基线但无执行历史的已有库")
    command.add_argument("--create", action="store_true", help="与 apply 配合，明确允许创建新数据库")
    command.add_argument("--backup-dir", help="已有库变更前的备份目录，须为绝对路径")
    command.add_argument("--timeout", type=float, default=5.0, help="SQLite 等锁和备份等待上限秒数，默认 5")
    return command


def main(argv: list[str] | None = None) -> int:
    """成功返回 0；失败返回 1；中断返回 130。没有交互式确认或隐式降级。"""
    try:
        run(parser().parse_args(argv))
        return 0
    except (UpgradeError, sqlite3.Error, OSError, ValueError) as exc:
        print(f"升级失败：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("已中断，尚未提交的事务已回滚。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
