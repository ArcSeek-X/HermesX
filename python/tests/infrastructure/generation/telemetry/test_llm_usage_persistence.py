"""Tests for llm usage persistence."""

from tests.infrastructure.generation.telemetry._llm_usage_support import (
    Connection,
    DatabaseManager,
    LLMUsage,
    OperationalError,
    Path,
    SimpleNamespace,
    _LLM_USAGE_TELEMETRY_COLUMN_SQL,
    _TestLLMUsageMigrationFixture,
    _TestPersistUsageHelperFixture,
    _TestRecordLLMUsageFixture,
    attach_message_hmacs,
    filter_prompt_cache_telemetry,
    json,
    normalize_litellm_usage,
    os,
    patch,
    persist_llm_usage,
    sqlite3,
    tempfile,
    unittest,
)


class TestRecordLLMUsage(_TestRecordLLMUsageFixture, unittest.TestCase):
    def test_record_single_row(self):
        self.db.record_llm_usage(
            call_type="analysis",
            model="gemini/gemini-2.5-flash",
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            stock_code="600519",
        )
        with self.db.session_scope() as session:
            rows = session.query(LLMUsage).all()
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row.call_type, "analysis")
            self.assertEqual(row.model, "gemini/gemini-2.5-flash")
            self.assertEqual(row.stock_code, "600519")
            self.assertEqual(row.prompt_tokens, 100)
            self.assertEqual(row.completion_tokens, 200)
            self.assertEqual(row.total_tokens, 300)

    def test_record_without_stock_code(self):
        self.db.record_llm_usage(
            call_type="market_review",
            model="openai/gpt-4o",
            prompt_tokens=50,
            completion_tokens=150,
            total_tokens=200,
        )
        with self.db.session_scope() as session:
            rows = session.query(LLMUsage).all()
            self.assertEqual(len(rows), 1)
            self.assertIsNone(rows[0].stock_code)

    def test_record_multiple_rows(self):
        for i in range(5):
            self.db.record_llm_usage(
                call_type="agent",
                model="gemini/gemini-2.5-flash",
                prompt_tokens=10 * i,
                completion_tokens=20 * i,
                total_tokens=30 * i,
            )
        with self.db.session_scope() as session:
            count = session.query(LLMUsage).count()
            self.assertEqual(count, 5)


class TestPersistUsageHelper(_TestPersistUsageHelperFixture, unittest.TestCase):
    def test_persist_usage_writes_row(self):
        persist_llm_usage(
            {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            "gemini/gemini-2.5-flash",
            call_type="analysis",
            stock_code="000001",
        )
        with self.db.session_scope() as session:
            rows = session.query(LLMUsage).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].total_tokens, 30)

    def test_persist_usage_handles_empty_usage(self):
        # Should not raise even with an empty dict
        persist_llm_usage({}, "unknown", call_type="agent")
        with self.db.session_scope() as session:
            rows = session.query(LLMUsage).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].total_tokens, 0)
            self.assertEqual(rows[0].cache_capability, "unknown")
            self.assertEqual(rows[0].cache_eligibility, "unknown")
            self.assertEqual(rows[0].cache_observation, "no_usage")

    def test_persist_usage_coerces_invalid_token_counts_to_safe_summary_values(self):
        persist_llm_usage(
            {
                "prompt_tokens": -5,
                "completion_tokens": True,
                "total_tokens": "3.5",
                "normalized_prompt_tokens": -5,
                "normalized_completion_tokens": True,
                "normalized_total_tokens": "3.5",
                "cache_observation": "invalid_provider_usage",
            },
            "openai/gpt-4o",
            call_type="analysis",
        )

        with self.db.session_scope() as session:
            row = session.query(LLMUsage).one()
            self.assertEqual(row.prompt_tokens, 0)
            self.assertEqual(row.completion_tokens, 0)
            self.assertEqual(row.total_tokens, 0)
            self.assertEqual(row.normalized_prompt_tokens, 0)
            self.assertEqual(row.normalized_completion_tokens, 0)
            self.assertEqual(row.normalized_total_tokens, 0)
            self.assertEqual(row.cache_observation, "invalid_provider_usage")

    def test_persist_usage_writes_new_telemetry_fields(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 2000,
                "completion_tokens": 100,
                "total_tokens": 2100,
                "prompt_tokens_details": {"cached_tokens": 500},
            },
            model="openai/gpt-4o",
        )
        with patch.dict(
            os.environ,
            {
                "LLM_USAGE_HMAC_SECRET": "persist-secret",
                "LLM_USAGE_HMAC_KEY_VERSION": "persist-v1",
            },
            clear=False,
        ):
            usage = attach_message_hmacs(
                usage,
                [
                    {"role": "system", "content": "system prompt"},
                    {"role": "user", "content": "user prompt"},
                ],
            )

        persist_llm_usage(
            usage,
            "openai/gpt-4o",
            call_type="analysis",
            stock_code="000001",
        )

        with self.db.session_scope() as session:
            row = session.query(LLMUsage).one()
            self.assertEqual(row.prompt_tokens, 2000)
            self.assertEqual(row.normalized_prompt_tokens, 2000)
            self.assertEqual(row.normalized_cache_read_tokens, 500)
            self.assertEqual(row.cache_capability, "supported")
            self.assertEqual(row.cache_eligibility, "eligible")
            self.assertEqual(row.cache_observation, "partial_hit")
            self.assertEqual(row.hmac_key_version, "persist-v1")
            self.assertEqual(len(row.messages_hmac), 64)
            self.assertNotIn("system prompt", row.provider_usage_json)
            self.assertNotIn("user prompt", row.provider_usage_json)

    def test_prompt_cache_telemetry_disabled_does_not_synthesize_cache_columns(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 2000,
                "completion_tokens": 100,
                "total_tokens": 2100,
                "prompt_tokens_details": {"cached_tokens": 500},
            },
            model="openai/gpt-4o",
        )
        filtered = filter_prompt_cache_telemetry(
            usage,
            SimpleNamespace(llm_prompt_cache_telemetry_enabled=False),
        )

        persist_llm_usage(
            filtered,
            "openai/gpt-4o",
            call_type="analysis",
            stock_code="000001",
        )

        with self.db.session_scope() as session:
            row = session.query(LLMUsage).one()
            self.assertEqual(row.prompt_tokens, 2000)
            self.assertEqual(row.normalized_prompt_tokens, 2000)
            self.assertIsNone(row.provider_usage_json)
            self.assertIsNone(row.normalized_cache_read_tokens)
            self.assertIsNone(row.cache_capability)
            self.assertIsNone(row.cache_eligibility)
            self.assertIsNone(row.cache_observation)

    def test_prompt_cache_telemetry_disabled_no_usage_does_not_synthesize_cache_columns(self):
        filtered = filter_prompt_cache_telemetry(
            {},
            SimpleNamespace(llm_prompt_cache_telemetry_enabled=False),
        )

        persist_llm_usage(
            filtered,
            "openai/gpt-4o",
            call_type="analysis",
            stock_code="000001",
        )

        with self.db.session_scope() as session:
            row = session.query(LLMUsage).one()
            self.assertEqual(row.prompt_tokens, 0)
            self.assertEqual(row.normalized_prompt_tokens, 0)
            self.assertIsNone(row.provider_usage_json)
            self.assertIsNone(row.normalized_cache_read_tokens)
            self.assertIsNone(row.cache_capability)
            self.assertIsNone(row.cache_eligibility)
            self.assertIsNone(row.cache_observation)

    def test_persist_usage_does_not_store_unmodeled_prompt_payload_fields(self):
        usage = normalize_litellm_usage(
            {
                "prompt_tokens": 3,
                "completion_tokens": 2,
                "total_tokens": 5,
                "prompt": "SECRET_PROMPT",
                "messages": [{"role": "user", "content": "SECRET_MESSAGE"}],
                "content": "SECRET_CONTENT",
            },
            model="gateway/custom-model",
            provider="gateway",
        )

        persist_llm_usage(
            usage,
            "gateway/custom-model",
            call_type="analysis",
            stock_code="000001",
        )

        with self.db.session_scope() as session:
            row = session.query(LLMUsage).one()
            self.assertNotIn("SECRET_PROMPT", row.provider_usage_json)
            self.assertNotIn("SECRET_MESSAGE", row.provider_usage_json)
            self.assertNotIn("SECRET_CONTENT", row.provider_usage_json)
            parsed = json.loads(row.provider_usage_json)
            self.assertEqual(parsed, {"completion_tokens": 2, "prompt_tokens": 3, "total_tokens": 5})

    def test_persist_usage_does_not_store_tokenizer_free_text_columns(self):
        persist_llm_usage(
            {
                "prompt_tokens": 1,
                "completion_tokens": 2,
                "total_tokens": 3,
                "tokenizer_name": "cl100k_base prompt fragment",
                "tokenizer_version": "Authorization: Bearer sk-header",
            },
            "gateway/custom-model",
            call_type="analysis",
        )

        with self.db.session_scope() as session:
            row = session.query(LLMUsage).one()
            self.assertIsNone(row.tokenizer_name)
            self.assertIsNone(row.tokenizer_version)

    def test_persist_usage_never_raises(self):
        # Pass a deliberately bad db state by resetting the singleton
        DatabaseManager.reset_instance()
        # Should silently swallow the error, not raise
        try:
            persist_llm_usage({"total_tokens": 5}, "m", call_type="analysis")
        except Exception as exc:
            self.fail(f"persist_llm_usage raised unexpectedly: {exc}")


class TestLLMUsageMigration(_TestLLMUsageMigrationFixture, unittest.TestCase):
    def test_existing_sqlite_table_gets_missing_columns_idempotently(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "legacy.sqlite"
            self._create_legacy_usage_db(db_path)

            DatabaseManager.reset_instance()
            db = DatabaseManager(db_url=f"sqlite:///{db_path}")
            db._ensure_llm_usage_telemetry_columns()

            self._assert_all_telemetry_columns(db_path)

    def test_existing_sqlite_table_gets_partial_missing_columns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "legacy.sqlite"
            self._create_legacy_usage_db(
                db_path,
                telemetry_columns=(
                    "provider_usage_json",
                    "normalized_prompt_tokens",
                    "messages_hmac",
                ),
            )

            DatabaseManager.reset_instance()
            DatabaseManager(db_url=f"sqlite:///{db_path}")

            self._assert_all_telemetry_columns(db_path)

    def test_existing_sqlite_table_with_all_telemetry_columns_is_noop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "legacy.sqlite"
            self._create_legacy_usage_db(
                db_path,
                telemetry_columns=tuple(_LLM_USAGE_TELEMETRY_COLUMN_SQL),
            )

            DatabaseManager.reset_instance()
            DatabaseManager(db_url=f"sqlite:///{db_path}")

            self._assert_all_telemetry_columns(db_path)

    def test_existing_sqlite_table_ignores_concurrent_duplicate_column(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "legacy.sqlite"
            self._create_legacy_usage_db(db_path)

            original_exec_driver_sql = Connection.exec_driver_sql
            race_fired = {"value": False}

            def flaky_exec_driver_sql(connection, statement, *args, **kwargs):
                if (
                    not race_fired["value"]
                    and self._is_add_column_statement(statement, "provider_usage_json")
                ):
                    race_fired["value"] = True
                    with sqlite3.connect(db_path) as conn:
                        conn.execute(
                            "ALTER TABLE llm_usage ADD COLUMN provider_usage_json TEXT"
                        )
                        conn.commit()
                    raise OperationalError(
                        statement,
                        {},
                        sqlite3.OperationalError(
                            "duplicate column name: provider_usage_json"
                        ),
                    )
                return original_exec_driver_sql(
                    connection,
                    statement,
                    *args,
                    **kwargs,
                )

            DatabaseManager.reset_instance()
            with patch.object(
                Connection,
                "exec_driver_sql",
                new=flaky_exec_driver_sql,
            ):
                DatabaseManager(db_url=f"sqlite:///{db_path}")

            self.assertTrue(race_fired["value"])
            self._assert_all_telemetry_columns(db_path)

    def test_existing_sqlite_table_retries_locked_column_backfill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "legacy.sqlite"
            self._create_legacy_usage_db(db_path)

            original_exec_driver_sql = Connection.exec_driver_sql
            lock_fired = {"value": False}

            def flaky_exec_driver_sql(connection, statement, *args, **kwargs):
                if (
                    not lock_fired["value"]
                    and self._is_add_column_statement(statement, "provider_usage_json")
                ):
                    lock_fired["value"] = True
                    raise OperationalError(
                        statement,
                        {},
                        sqlite3.OperationalError("database is locked"),
                    )
                return original_exec_driver_sql(
                    connection,
                    statement,
                    *args,
                    **kwargs,
                )

            DatabaseManager.reset_instance()
            with patch.object(
                Connection,
                "exec_driver_sql",
                new=flaky_exec_driver_sql,
            ), patch("src.infrastructure.persistence.session.time.sleep") as sleep_mock:
                DatabaseManager(db_url=f"sqlite:///{db_path}")

            self.assertTrue(lock_fired["value"])
            storage_retry_sleeps = [
                call_args
                for call_args in sleep_mock.call_args_list
                if call_args.args == (0.1,)
            ]
            self.assertEqual(len(storage_retry_sleeps), 1)
            self._assert_all_telemetry_columns(db_path)
