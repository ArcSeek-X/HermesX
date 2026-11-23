"""手动升级工具的真实 SQLite 测试；所有数据库、SQL 副本和备份均在临时目录。

运行：python3 -m unittest discover -s scripts/db/tests -v
不启动分析后端，不使用 data/hrs_system.db，不需要安装 pytest。
"""
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'manual_db_upgrade.py'
SPEC = importlib.util.spec_from_file_location('manual_db_upgrade', SCRIPT)
upgrade = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = upgrade
SPEC.loader.exec_module(upgrade)
SERVICE = 'hrs-system-service'
BASELINE = 'BASELINE_TEST'
BASE_SQL = 'CREATE TABLE IF NOT EXISTS hrs_system_item (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE);'


def section(name, sql, previous=None, verify=None):
    """构造真实版本段；测试不在执行器里 mock SQL 或跳过数据库层。"""
    metadata = {'description': name, 'kind': 'baseline' if previous is None else 'migration',
                'requires': [] if previous is None else [previous], 'verify': verify or []}
    return f'-- BEGIN {name}\n-- @upgrade {json.dumps(metadata)}\n{sql}\n-- END {name}\n'


class ManualDatabaseUpgradeTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='hermesx-upgrade-test-')
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name).resolve()
        self.root = self.work / 'repo'
        self.sql_file = self.root / SERVICE / 'sql' / f'{SERVICE}.sql'
        self.sql_file.parent.mkdir(parents=True)
        self.database = self.work / 'hrs_system.db'
        self.backups = self.work / 'backups'
        self.baseline = section(BASELINE, BASE_SQL)
        self.write_sql()

    def write_sql(self, *extra, baseline=None, final_check=None):
        text = f'-- @service {SERVICE}\n-- @dialect sqlite\n' + (baseline or self.baseline) + ''.join(extra)
        if final_check:
            text += f'-- @final-check {final_check}\n'
        self.sql_file.write_text(text, encoding='utf-8')

    def invoke(self, *options, emit=None):
        args = upgrade.parser().parse_args(['--service', SERVICE, '--database', str(self.database), *options])
        messages = []
        upgrade.run(args, root=self.root, emit=emit or messages.append)
        return messages

    def create(self):
        self.invoke('--apply', '--create')

    def query(self, sql, *values):
        with closing(sqlite3.connect(self.database)) as db:
            return db.execute(sql, values).fetchall()

    def mutate(self, sql, *values):
        with closing(sqlite3.connect(self.database)) as db:
            db.execute(sql, values)
            db.commit()

    def snapshot(self):
        return (self.query('SELECT type,name,sql FROM sqlite_master ORDER BY type,name'),
                self.query('SELECT * FROM hrs_system_item ORDER BY id'),
                self.query('SELECT * FROM hrs_system_schema_history ORDER BY id'))

    def test_plan_does_not_create_database_or_its_parent(self):
        self.database = self.work / 'missing-parent' / 'hrs_system.db'
        self.invoke('--plan')
        self.assertFalse(self.database.parent.exists())
        self.assertFalse(self.backups.exists())

    def test_new_database_requires_explicit_create(self):
        with self.assertRaisesRegex(upgrade.UpgradeError, 'create'):
            self.invoke('--apply')
        self.assertFalse(self.database.exists())

    def test_create_and_repeat_preserve_data_and_history_without_backup(self):
        self.create()
        self.mutate("INSERT INTO hrs_system_item(name) VALUES ('existing')")
        before = self.snapshot()
        self.invoke('--apply')
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.query('SELECT completion_kind FROM hrs_system_schema_history'), [('applied',)])
        self.assertFalse(self.backups.exists())

    def test_incremental_column_change_is_backed_up_and_executed_once(self):
        self.create()
        self.mutate("INSERT INTO hrs_system_item(name) VALUES ('keep')")
        before = self.snapshot()
        self.write_sql(section('ADD_COLUMN', 'ALTER TABLE hrs_system_item ADD COLUMN note TEXT;', BASELINE))
        self.invoke('--plan')
        self.assertEqual(before, self.snapshot())
        self.invoke('--apply', '--backup-dir', str(self.backups))
        self.assertEqual(self.query('SELECT name,note FROM hrs_system_item'), [('keep', None)])
        backup_files = list(self.backups.glob('*.db'))
        self.assertEqual(len(backup_files), 1)
        with closing(sqlite3.connect(backup_files[0])) as backup:
            self.assertNotIn('note', [row[1] for row in backup.execute('PRAGMA table_info(hrs_system_item)')])
        self.invoke('--apply', '--backup-dir', str(self.backups))
        self.assertEqual(len(list(self.backups.glob('*.db'))), 1)
        self.assertEqual(self.query('SELECT COUNT(*) FROM hrs_system_schema_history'), [(2,)])

    def test_existing_database_requires_backup_for_pending_change(self):
        self.create()
        self.write_sql(section('ADD_COLUMN', 'ALTER TABLE hrs_system_item ADD COLUMN note TEXT;', BASELINE))
        before = self.snapshot()
        with self.assertRaisesRegex(upgrade.UpgradeError, 'backup-dir'):
            self.invoke('--apply')
        self.assertEqual(before, self.snapshot())

    def test_changed_executed_sql_or_metadata_is_rejected(self):
        self.create()
        before = self.snapshot()
        self.write_sql(baseline=self.baseline.replace('"description": "BASELINE_TEST"', '"description": "changed"'))
        with self.assertRaisesRegex(upgrade.UpgradeError, '摘要'):
            self.invoke('--apply', '--backup-dir', str(self.backups))
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.backups.exists())

    def test_same_named_table_with_different_columns_is_rejected(self):
        self.create()
        self.mutate('ALTER TABLE hrs_system_item ADD COLUMN unexpected TEXT')
        before = self.snapshot()
        with self.assertRaisesRegex(upgrade.UpgradeError, '结构'):
            self.invoke('--apply')
        self.assertEqual(before, self.snapshot())

    def test_index_definition_drift_is_rejected(self):
        self.baseline = section(BASELINE, BASE_SQL + '\nCREATE INDEX idx_item ON hrs_system_item(name);')
        self.write_sql()
        self.create()
        self.mutate('DROP INDEX idx_item')
        self.mutate('CREATE INDEX idx_item ON hrs_system_item(id)')
        with self.assertRaisesRegex(upgrade.UpgradeError, '定义差异'):
            self.invoke('--plan')

    def test_unknown_history_or_another_service_identity_is_rejected(self):
        for field, value in [('change_id', 'UNKNOWN_VERSION'), ('service_name', 'hrs-auth-service')]:
            with self.subTest(field=field):
                if self.database.exists():
                    self.database.unlink()
                self.create()
                self.mutate(f'UPDATE hrs_system_schema_history SET {field}=?', value)
                with self.assertRaises(upgrade.UpgradeError):
                    self.invoke('--plan')

    def test_no_history_database_needs_explicit_adoption_and_later_migrations_are_not_applied(self):
        with closing(sqlite3.connect(self.database)) as db:
            db.execute(BASE_SQL)
            db.execute("INSERT INTO hrs_system_item(name) VALUES ('kept')")
            db.commit()
        self.write_sql(section('ADD_COLUMN', 'ALTER TABLE hrs_system_item ADD COLUMN note TEXT;', BASELINE))
        with self.assertRaisesRegex(upgrade.UpgradeError, 'adopt-baseline'):
            self.invoke('--plan')
        self.invoke('--adopt-baseline', '--backup-dir', str(self.backups))
        self.assertNotIn('note', [r[1] for r in self.query('PRAGMA table_info(hrs_system_item)')])
        self.assertEqual(self.query('SELECT completion_kind FROM hrs_system_schema_history'), [('adopted',)])
        self.invoke('--apply', '--backup-dir', str(self.backups))
        self.assertEqual(self.query('SELECT name,note FROM hrs_system_item'), [('kept', None)])

    def test_adoption_rejects_same_columns_but_different_constraints(self):
        with closing(sqlite3.connect(self.database)) as db:
            db.execute(BASE_SQL.replace(' NOT NULL UNIQUE', ''))
        with self.assertRaisesRegex(upgrade.UpgradeError, '不完全匹配'):
            self.invoke('--adopt-baseline', '--backup-dir', str(self.backups))
        self.assertFalse(self.backups.exists())

    def test_pending_syntax_error_is_detected_before_any_real_write(self):
        self.create()
        before = self.snapshot()
        self.write_sql(section('BAD_SQL', 'ALTER TABLE hrs_system_item ADD COLUMN;', BASELINE))
        with self.assertRaisesRegex(upgrade.UpgradeError, 'BAD_SQL'):
            self.invoke('--apply', '--backup-dir', str(self.backups))
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.backups.exists())

    def test_data_assertion_failure_during_preview_does_not_write_or_backup(self):
        self.create()
        self.mutate("INSERT INTO hrs_system_item(name) VALUES ('bad')")
        before = self.snapshot()
        self.write_sql(section('ADD_COLUMN', 'ALTER TABLE hrs_system_item ADD COLUMN note TEXT;', BASELINE,
                               ["SELECT COUNT(*) = 0 FROM hrs_system_item WHERE name='bad'"]))
        with self.assertRaisesRegex(upgrade.UpgradeError, '验证未通过'):
            self.invoke('--apply', '--backup-dir', str(self.backups))
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.backups.exists())

    def test_live_failure_rolls_back_all_changes_and_history_after_preflight_race(self):
        self.create()
        before_schema = self.query('SELECT type,name,sql FROM sqlite_master ORDER BY type,name')
        self.write_sql(section('ADD_COLUMN', 'ALTER TABLE hrs_system_item ADD COLUMN note TEXT;', BASELINE),
                       section('INSERT_ROW', "INSERT INTO hrs_system_item(name) VALUES ('conflict');", 'ADD_COLUMN'))
        inserted = False

        def external_write_after_preview(message):
            nonlocal inserted
            if '待执行' in message and not inserted:
                self.mutate("INSERT INTO hrs_system_item(name) VALUES ('conflict')")
                inserted = True

        with self.assertRaisesRegex(upgrade.UpgradeError, 'INSERT_ROW'):
            self.invoke('--apply', '--backup-dir', str(self.backups), emit=external_write_after_preview)
        self.assertEqual(before_schema, self.query('SELECT type,name,sql FROM sqlite_master ORDER BY type,name'))
        self.assertEqual(self.query('SELECT change_id FROM hrs_system_schema_history'), [(BASELINE,)])
        self.assertEqual(self.query('SELECT name FROM hrs_system_item'), [('conflict',)])
        self.assertEqual(len(list(self.backups.glob('*.db'))), 1)

    def test_backup_error_prevents_schema_or_history_changes(self):
        self.create()
        before = self.snapshot()
        self.write_sql(section('ADD_COLUMN', 'ALTER TABLE hrs_system_item ADD COLUMN note TEXT;', BASELINE))
        self.backups.write_text('not a directory')
        with self.assertRaises(OSError):
            self.invoke('--apply', '--backup-dir', str(self.backups))
        self.assertEqual(before, self.snapshot())

    def test_wal_backup_contains_committed_rows_not_yet_checkpointed(self):
        self.create()
        with closing(sqlite3.connect(self.database)) as writer:
            writer.execute('PRAGMA journal_mode=WAL')
            writer.execute('PRAGMA wal_autocheckpoint=0')
            writer.execute("INSERT INTO hrs_system_item(name) VALUES ('wal-row')")
            writer.commit()
            self.assertTrue(Path(str(self.database) + '-wal').exists())
            self.write_sql(section('ADD_COLUMN', 'ALTER TABLE hrs_system_item ADD COLUMN note TEXT;', BASELINE))
            self.invoke('--apply', '--backup-dir', str(self.backups))
            with closing(sqlite3.connect(next(self.backups.glob('*.db')))) as backup:
                self.assertEqual(backup.execute('SELECT name FROM hrs_system_item').fetchall(), [('wal-row',)])

    def test_plan_handles_cleanly_closed_wal_database_without_sidecar_files(self):
        self.create()
        with closing(sqlite3.connect(self.database)) as db:
            db.execute('PRAGMA journal_mode=WAL').fetchall()
        before = self.snapshot()
        self.invoke('--plan')
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.backups.exists())

    def test_writer_lock_has_bounded_timeout_and_no_partial_upgrade(self):
        self.create()
        self.write_sql(section('ADD_COLUMN', 'ALTER TABLE hrs_system_item ADD COLUMN note TEXT;', BASELINE))
        before = self.snapshot()
        with closing(sqlite3.connect(self.database, isolation_level=None)) as writer:
            writer.execute('BEGIN IMMEDIATE')
            with self.assertRaises(sqlite3.OperationalError):
                self.invoke('--apply', '--backup-dir', str(self.backups), '--timeout', '0.05')
            writer.rollback()
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.backups.exists())

    def test_backup_read_connection_does_not_release_the_writer_lock(self):
        self.create()
        bundle = upgrade.load_bundle(SERVICE, self.root)
        with closing(upgrade.connect_file(self.database, 'rw', 1)) as writer:
            writer.execute('BEGIN IMMEDIATE')
            upgrade.make_backup(self.database, self.backups, bundle, 1)
            # 从另一个进程申请写锁，直接证明备份连接的打开/关闭没有释放已有写锁。
            code = """import sqlite3,sys
db=sqlite3.connect(sys.argv[1],timeout=0.05,isolation_level=None)
try:
    db.execute('BEGIN IMMEDIATE')
    print('unexpectedly-acquired')
except sqlite3.OperationalError as error:
    print('locked' if 'locked' in str(error) else 'unexpected-error')
finally:
    db.rollback()
    db.close()
"""
            process = subprocess.run([sys.executable, '-c', code, str(self.database)],
                                     capture_output=True, text=True, timeout=5)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(process.stdout.strip(), 'locked')
            writer.rollback()

    def test_two_processes_recheck_history_after_acquiring_write_lock(self):
        self.create()
        self.write_sql(section('SEED', "INSERT INTO hrs_system_item(name) VALUES ('one-time');", BASELINE))
        code = """import importlib.util,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('upgrade',sys.argv[1])
u=importlib.util.module_from_spec(spec);sys.modules[spec.name]=u;spec.loader.exec_module(u)
a=u.parser().parse_args(['--service','hrs-system-service','--database',sys.argv[3],'--apply','--backup-dir',sys.argv[4]])
u.run(a,root=Path(sys.argv[2]))
"""
        command = [sys.executable, '-c', code, str(SCRIPT), str(self.root), str(self.database), str(self.backups)]
        processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
        outputs = []
        for process in processes:
            out, err = process.communicate(timeout=20)
            outputs.append(out + err)
            self.assertEqual(process.returncode, 0, out + err)
        self.assertEqual(self.query('SELECT name FROM hrs_system_item'), [('one-time',)])
        self.assertEqual(self.query('SELECT COUNT(*) FROM hrs_system_schema_history'), [(2,)])
        self.assertEqual(len(list(self.backups.glob('*.db'))), 1, "\n".join(outputs))

    def test_strings_comments_and_trigger_bodies_do_not_split_at_inner_semicolons(self):
        self.baseline = section(BASELINE, BASE_SQL + """
CREATE TRIGGER hrs_system_append AFTER INSERT ON hrs_system_item BEGIN
    UPDATE hrs_system_item SET name=name || ';done' WHERE id=NEW.id;
END;
INSERT INTO hrs_system_item(name) VALUES ('literal;--text;/*text*/');
-- trailing comment with ;
""")
        self.write_sql()
        self.create()
        self.assertEqual(self.query('SELECT name FROM hrs_system_item'), [('literal;--text;/*text*/;done',)])

    def test_sql_cannot_override_transactions_attach_or_modify_history(self):
        for bad_sql in ['BEGIN;', "ATTACH ':memory:' AS other;", 'PRAGMA journal_mode=OFF;',
                        'CREATE VIRTUAL TABLE hrs_system_search USING fts5(name);',
                        'CREATE TABLE hrs_auth_wrong (id INTEGER);',
                        'CREATE TABLE hrs_system_schema_history (id INTEGER);']:
            with self.subTest(sql=bad_sql):
                self.write_sql(baseline=section(BASELINE, BASE_SQL + '\n' + bad_sql))
                with self.assertRaises(upgrade.UpgradeError):
                    self.invoke('--apply', '--create')
                self.assertFalse(self.database.exists())

    def test_empty_baseline_is_rejected_and_timeout_must_be_positive_and_finite(self):
        self.write_sql(baseline=section(BASELINE, 'SELECT 1;'))
        with self.assertRaisesRegex(upgrade.UpgradeError, '业务表'):
            self.invoke('--apply', '--create')
        self.write_sql()
        for timeout in ['0', '-1', 'nan', 'inf']:
            with self.subTest(timeout=timeout):
                with self.assertRaisesRegex(upgrade.UpgradeError, '有限正数'):
                    self.invoke('--apply', '--create', '--timeout', timeout)
                self.assertFalse(self.database.exists())

    def test_verify_and_final_checks_are_readonly_and_checked_on_noop(self):
        self.write_sql(final_check="SELECT COUNT(*) = 0 FROM hrs_system_item WHERE name='bad'")
        self.create()
        self.mutate("INSERT INTO hrs_system_item(name) VALUES ('bad')")
        with self.assertRaisesRegex(upgrade.UpgradeError, '验证未通过'):
            self.invoke('--apply')
        self.write_sql(final_check="WITH data AS (SELECT 1) DELETE FROM hrs_system_item RETURNING 1")
        with self.assertRaises(upgrade.UpgradeError):
            self.invoke('--apply')
        self.assertEqual(self.query('SELECT name FROM hrs_system_item'), [('bad',)])

    def test_invalid_boundaries_dependencies_or_metadata_are_rejected_without_creation(self):
        for text in [self.baseline + self.baseline,
                     self.baseline.replace('-- END BASELINE_TEST', '-- END WRONG'),
                     self.baseline.replace('-- END BASELINE_TEST', ''),
                     self.baseline + section('NEXT', 'SELECT 1;', 'WRONG'),
                     self.baseline.replace('"kind": "baseline"', '"kind": "migration"'),
                     self.baseline.replace('-- @upgrade ', '-- @unknown '),
                     self.baseline + '\nSELECT 1;']:
            with self.subTest(text=text):
                self.write_sql(baseline=text)
                with self.assertRaises((upgrade.UpgradeError, ValueError)):
                    self.invoke('--apply', '--create')
                self.assertFalse(self.database.exists())

    def test_relative_symlink_and_other_service_paths_are_rejected(self):
        for target in ['relative.db', str(self.work / 'stock_analysis.db'), str(self.work / 'hrs_auth.db')]:
            with self.subTest(target=target):
                args = upgrade.parser().parse_args(['--service', SERVICE, '--database', target, '--plan'])
                with self.assertRaises(upgrade.UpgradeError):
                    upgrade.run(args, root=self.root, emit=lambda _: None)
        self.create()
        alias = self.work / 'alias.db'
        alias.symlink_to(self.database)
        args = upgrade.parser().parse_args(['--service', SERVICE, '--database', str(alias), '--plan'])
        with self.assertRaises(upgrade.UpgradeError):
            upgrade.run(args, root=self.root, emit=lambda _: None)

    def test_cli_works_from_another_directory_with_official_service_sql(self):
        result = subprocess.run([sys.executable, str(SCRIPT), '--service', SERVICE, '--database', str(self.database),
                                 '--apply', '--create'], cwd=self.work, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual({r[0] for r in self.query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")},
                         {'hrs_system_user', 'hrs_system_organization', 'hrs_system_menu', 'hrs_system_schema_history'})
        self.assertEqual(self.query('SELECT COUNT(*) FROM hrs_system_user'), [(0,)])
        self.assertEqual(self.query('SELECT COUNT(*) FROM hrs_system_menu'), [(0,)])
        self.assertEqual(len(self.query('SELECT checksum FROM hrs_system_schema_history')[0][0]), 64)

    def test_placeholder_service_and_invalid_cli_return_nonzero_without_creating_database(self):
        for options in [['--service', 'hrs-auth-service', '--database', str(self.database), '--apply', '--create'],
                        ['--service', '../hrs-system-service', '--database', str(self.database), '--plan'],
                        ['--service', SERVICE, '--database', str(self.database)],
                        ['--service', SERVICE, '--database', str(self.database), '--plan', '--create']]:
            with self.subTest(options=options):
                result = subprocess.run([sys.executable, str(SCRIPT), *options], cwd=self.work,
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Traceback', result.stderr)
                self.assertFalse(self.database.exists())

    def test_database_uri_encodes_spaces_question_marks_and_unicode(self):
        self.database = self.work / '测试 space?query&name.db'
        self.create()
        self.invoke('--plan')
        self.assertTrue(self.database.is_file())
        self.assertEqual(self.query('SELECT COUNT(*) FROM hrs_system_schema_history'), [(1,)])


if __name__ == '__main__':
    unittest.main()
