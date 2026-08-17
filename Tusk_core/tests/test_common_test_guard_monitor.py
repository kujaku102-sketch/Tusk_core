# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import io
import json
import os
import queue
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import call, patch


CORE_ROOT = Path(__file__).resolve().parents[1]
MONITOR = CORE_ROOT / "tools" / "test_guard_monitor.py"
ERROR_CODES = CORE_ROOT / "ERROR_CODES.md"
SPEC = spec_from_file_location("test_guard_monitor", MONITOR)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TestCommonTestGuardMonitor(unittest.TestCase):
    def write_json(self, path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def make_run(self, root: Path, *, total: int = 100, processes: list[dict] | None = None, require_counts: bool = False, require_ids: bool = False) -> dict[str, Path | dict | list[str]]:
        workspace = root.resolve()
        (workspace / "ERROR_CODES.md").write_text(ERROR_CODES.read_text(encoding="utf-8"), encoding="utf-8")
        run = workspace / "out" / "unit"
        run.mkdir(parents=True)
        artifact = workspace / "artifact.txt"
        evidence = workspace / "evidence.json"
        log = workspace / "target.log"
        artifact.write_text("artifact", encoding="utf-8")
        evidence.write_text("{}", encoding="utf-8")
        log.write_text("", encoding="utf-8")
        started = datetime.now(timezone.utc) - timedelta(seconds=60)
        contract = {
            "schema_version": 1,
            "run_id": "unit",
            "started_at_utc": started.isoformat().replace("+00:00", "Z"),
            "required_check_ids": ["exit_code"],
            "expected_exit_codes": [0],
            "minor_total_units": total,
            "required_artifacts": [str(artifact)],
            "require_counts": require_counts,
            "require_id_set_sha256": require_ids,
        }
        contract_path = run / "test_contract.json"
        self.write_json(contract_path, contract)
        registry_path = run / "process_registry.json"
        self.write_json(registry_path, {"schema_version": 1, "run_id": "unit", "processes": processes or []})
        done = run / "done.json"
        output = run / "guard"
        args = [
            "--run-id", "unit",
            "--workspace", str(workspace),
            "--log-path", str(log),
            "--allowed-output-root", str(workspace / "out"),
            "--output-dir", str(output),
            "--done-file", str(done),
            "--test-contract", str(contract_path),
            "--process-registry", str(registry_path),
            "--error-registry", str(workspace / "ERROR_CODES.md"),
            "--pid-policy", "observe",
            "--no-interactive-commands",
            "--no-notify-codex-cli",
            "--no-stop-on-force",
            "--poll-seconds", "1",
        ]
        return {
            "workspace": workspace,
            "run": run,
            "artifact": artifact,
            "evidence": evidence,
            "log": log,
            "contract": contract,
            "contract_path": contract_path,
            "registry_path": registry_path,
            "done": done,
            "output": output,
            "args": args,
        }

    def write_good_done(self, case: dict[str, Path | dict | list[str]], *, extra_checks: list[dict] | None = None) -> dict:
        artifact = case["artifact"]
        evidence = case["evidence"]
        contract_path = case["contract_path"]
        done = {
            "schema_version": 1,
            "run_id": "unit",
            "status": "validated",
            "validated_at_utc": MODULE.utc_now(),
            "contract_sha256": MODULE.sha256_file(contract_path),
            "target_exit_codes": [0],
            "success_conditions": {"passed": True},
            "checks": [{"id": "exit_code", "passed": True, "actual": 0, "evidence": str(evidence)}] + (extra_checks or []),
            "artifacts": [{"path": str(artifact), "sha256": MODULE.sha256_file(artifact), "updated_at_utc": MODULE.utc_now()}],
        }
        self.write_json(case["done"], done)
        return done

    def append_on_second_snapshot(self, case: dict[str, Path | dict | list[str]], text: str):
        original = MODULE.snapshot_logs
        count = {"value": 0}

        def snapshot(paths, excluded, workspace=None):
            count["value"] += 1
            if count["value"] == 2:
                case["log"].write_text(text, encoding="utf-8")
            return original(paths, excluded, workspace)

        return snapshot

    def enable_luna(self, case: dict[str, Path | dict | list[str]]) -> None:
        task = case["run"] / "luna_task.json"
        self.write_json(task, {
            "schema_version": 1,
            "run_id": "unit",
            "task_id": "luna-id",
            "policy": "new_task",
            "evidence": "provider-created",
            "created_at_utc": MODULE.utc_now(),
        })
        args = case["args"]
        args.remove("--no-notify-codex-cli")
        args.extend(["--notify-codex-cli", "--luna-task-file", str(task), "--luna-thread-id", "luna-id"])

    def test_run_id_validation_rejects_traversal(self):
        self.assertFalse(bool(MODULE.RUN_ID_RE.fullmatch("../bad")))

    def test_registry_and_compatibility_are_loaded_from_canonical_markdown(self):
        registry = MODULE.parse_error_registry(ERROR_CODES)
        self.assertIn("F182", registry["force"])
        self.assertEqual(registry["legacy"]["CACHE_CONFLICT"], "M141")

    def test_normalizes_registered_legacy_codes(self):
        self.assertEqual(MODULE.normalize_code("PIPELINE_FATAL"), "F026")
        self.assertEqual(MODULE.normalize_code("TRANSLATION_SKIP"), "M080")

    def test_parses_legacy_event_without_structured_marker(self):
        registry = MODULE.parse_error_registry(ERROR_CODES)
        marker = MODULE.parse_event("worker PIPELINE_FATAL stopped", "unit", registry)
        self.assertEqual((marker["kind"], marker["code"]), ("FORCE_STOP", "F026"))

    def test_rejects_unregistered_severity_mismatch_and_missing_target(self):
        self.assertEqual(MODULE.validate_issue({"kind": "FORCE_STOP", "code": "M020"})[1], "unregistered_code_or_severity_mismatch")
        self.assertEqual(MODULE.validate_issue({"kind": "MINOR_ISSUE", "code": "M999"})[1], "unregistered_code_or_severity_mismatch")
        marker = {"kind": "MINOR_ISSUE", "code": "M020", "component": "c", "step": "s", "detail": "d"}
        self.assertEqual(MODULE.validate_issue(marker)[1], "minor_marker_required_field_missing")

    def test_foreign_run_marker_is_ignored(self):
        self.assertIsNone(MODULE.parse_marker("[TUSK_FORCE_STOP] code=F026 run_id=other component=c step=s reason=x", "unit"))
        registry = MODULE.parse_error_registry(ERROR_CODES)
        line = "[TUSK_FORCE_STOP] code=F026 run_id=other component=c step=s reason=PIPELINE_FATAL"
        self.assertIsNone(MODULE.parse_event(line, "unit", registry))

    def test_progress_marker_requires_all_fields(self):
        marker = MODULE.parse_marker("[TUSK_PROGRESS] run_id=unit component=a step=b current=1 total=2", "unit")
        self.assertTrue(MODULE.validate_progress(marker))
        marker.pop("total")
        self.assertFalse(MODULE.validate_progress(marker))

    def test_accepts_idtask_marker_as_compatibility_input(self):
        marker = MODULE.parse_marker("[IDTASK_PROGRESS] run_id=unit component=a step=b current=1 total=2", "unit")
        self.assertTrue(MODULE.validate_progress(marker))

    def test_log_offset_excludes_initial_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test.log"
            path.write_text("old\n", encoding="utf-8")
            cursor = MODULE.snapshot_logs([path], [])[path]
            with path.open("a", encoding="utf-8") as stream:
                stream.write("new\n")
            self.assertEqual(MODULE.read_new_lines(path, cursor)[0], ["new"])

    def test_partial_line_is_buffered_until_newline(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test.log"
            path.write_text("", encoding="utf-8")
            cursor = MODULE.snapshot_logs([path], [])[path]
            path.write_bytes(b"part")
            lines, cursor, _ = MODULE.read_new_lines(path, cursor)
            self.assertEqual(lines, [])
            with path.open("ab") as stream:
                stream.write(b"ial\n")
            lines, _, _ = MODULE.read_new_lines(path, cursor)
            self.assertEqual(lines, ["partial"])

    def test_rotate_reads_from_zero_and_discards_partial_buffer(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test.log"
            path.write_text("long old line\n", encoding="utf-8")
            cursor = MODULE.snapshot_logs([path], [])[path]
            cursor["buffer"] = b"discard"
            path.write_text("new\n", encoding="utf-8")
            lines, _, rotated = MODULE.read_new_lines(path, cursor)
            self.assertTrue(rotated)
            self.assertEqual(lines, ["new"])

    def test_snapshot_excludes_output_descendants(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            included = root / "a.log"
            excluded = root / "guard" / "events.log"
            included.write_text("x", encoding="utf-8")
            excluded.parent.mkdir()
            excluded.write_text("y", encoding="utf-8")
            snapshot = MODULE.snapshot_logs([root], [excluded.parent])
            self.assertIn(included, snapshot)
            self.assertNotIn(excluded, snapshot)

    def test_walk_rejects_nested_reparse_and_workspace_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            safe = root / "safe.log"
            blocked = root / "linked" / "blocked.log"
            safe.write_text("x", encoding="utf-8")
            blocked.parent.mkdir()
            blocked.write_text("y", encoding="utf-8")
            original_within = MODULE.resolved_within

            def within(path, parent):
                if path == safe:
                    return False
                return original_within(path, parent)

            with patch.object(MODULE, "path_is_reparse", side_effect=lambda path: path == blocked.parent), patch.object(MODULE, "resolved_within", side_effect=within):
                snapshot = MODULE.snapshot_logs([root], [], root)
            self.assertNotIn(safe, snapshot)
            self.assertNotIn(blocked, snapshot)

    def test_timestamp_only_changes_normalize_but_counts_do_not(self):
        first = MODULE.normalize_repetition_text("2026-08-10T01:02:03Z count=1")
        second = MODULE.normalize_repetition_text("2026-08-10T01:02:04Z count=1")
        third = MODULE.normalize_repetition_text("2026-08-10T01:02:04Z count=2")
        self.assertEqual(first, second)
        self.assertNotEqual(second, third)

    def test_minor_unique_and_event_boundaries(self):
        self.assertFalse(MODULE.minor_threshold_reached(19, 49, 100))
        self.assertTrue(MODULE.minor_threshold_reached(20, 49, 100))
        self.assertTrue(MODULE.minor_threshold_reached(1, 50, 100))

    def test_contract_requires_conditional_flags_and_nonempty_lists(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary))
            contract = dict(case["contract"])
            contract.pop("require_counts")
            self.write_json(case["contract_path"], contract)
            with self.assertRaises(ValueError):
                MODULE.validate_contract(case["contract_path"], "unit")

    def test_path_validation_rejects_reparse_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary))
            args = MODULE.parse_args(case["args"])
            original = MODULE.path_has_reparse

            def reparse(path, boundary):
                return path == args.test_contract or original(path, boundary)

            with patch.object(MODULE, "path_has_reparse", side_effect=reparse):
                with self.assertRaises(ValueError):
                    MODULE.validate_paths(args)

    def test_main_invalid_external_output_writes_only_stderr(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as external:
            case = self.make_run(Path(temporary))
            outside = Path(external) / "forbidden" / "guard"
            args = list(case["args"])
            args[args.index("--output-dir") + 1] = str(outside)
            stderr = io.StringIO()
            with patch.object(MODULE.sys, "stderr", stderr):
                self.assertEqual(MODULE.main(args), 1)
            self.assertFalse(outside.exists())
            self.assertFalse((case["workspace"] / "work" / "guard_fallback" / "unit").exists())
            self.assertIn('"status": "monitor_error"', stderr.getvalue())

    def test_done_requires_fixed_contract_sha(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary))
            self.write_good_done(case)
            contract = MODULE.validate_contract(case["contract_path"], "unit")
            raw = json.loads(case["contract_path"].read_text(encoding="utf-8"))
            raw["minor_total_units"] = 99
            self.write_json(case["contract_path"], raw)
            self.assertEqual(MODULE.validate_done(case["done"], case["contract_path"], contract, contract["_started_epoch"], contract["_sha256"])[0], "F124")

    def test_done_rejects_empty_partial_foreign_and_nonzero_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary))
            contract = MODULE.validate_contract(case["contract_path"], "unit")
            case["done"].write_text("", encoding="utf-8")
            self.assertEqual(MODULE.validate_done(case["done"], case["contract_path"], contract, contract["_started_epoch"])[0], "F122")
            done = self.write_good_done(case)
            done["run_id"] = "foreign"
            self.write_json(case["done"], done)
            self.assertEqual(MODULE.validate_done(case["done"], case["contract_path"], contract, contract["_started_epoch"])[0], "F122")
            done["run_id"] = "unit"
            done["target_exit_codes"] = [1]
            self.write_json(case["done"], done)
            self.assertEqual(MODULE.validate_done(case["done"], case["contract_path"], contract, contract["_started_epoch"])[0], "F122")

    def test_done_requires_count_id_and_evidence_contracts(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary), require_counts=True, require_ids=True)
            done = self.write_good_done(case)
            contract = MODULE.validate_contract(case["contract_path"], "unit")
            done["checks"].extend([
                {"id": "counts", "passed": True, "expected": 4, "actual": 4, "evidence": str(case["evidence"])},
                {"id": "id_set_sha256", "passed": True, "value": "a" * 64, "evidence": str(case["evidence"])},
            ])
            self.write_json(case["done"], done)
            code, result = MODULE.validate_done(case["done"], case["contract_path"], contract, contract["_started_epoch"])
            self.assertEqual(code, "F122")
            self.assertEqual(result["reason"], "counts_evidence_schema_undefined")
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary), require_ids=True)
            done = self.write_good_done(case, extra_checks=[{"id": "id_set_sha256", "passed": True, "value": "a" * 64, "evidence": str(case["evidence"])}])
            self.write_json(case["done"], done)
            contract = MODULE.validate_contract(case["contract_path"], "unit")
            code, result = MODULE.validate_done(case["done"], case["contract_path"], contract, contract["_started_epoch"])
            self.assertEqual(code, "F122")
            self.assertEqual(result["reason"], "id_set_evidence_schema_undefined")

    def test_done_rejects_missing_extra_stale_and_hash_mismatched_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary))
            done = self.write_good_done(case)
            contract = MODULE.validate_contract(case["contract_path"], "unit")
            done["artifacts"] = []
            self.write_json(case["done"], done)
            self.assertEqual(MODULE.validate_done(case["done"], case["contract_path"], contract, contract["_started_epoch"])[0], "F120")
            done = self.write_good_done(case)
            done["artifacts"].append({"path": str(case["workspace"] / "extra"), "sha256": "a" * 64, "updated_at_utc": MODULE.utc_now()})
            self.write_json(case["done"], done)
            self.assertEqual(MODULE.validate_done(case["done"], case["contract_path"], contract, contract["_started_epoch"])[0], "F120")
            done = self.write_good_done(case)
            done["artifacts"][0]["sha256"] = "b" * 64
            self.write_json(case["done"], done)
            self.assertEqual(MODULE.validate_done(case["done"], case["contract_path"], contract, contract["_started_epoch"])[0], "F124")
            old = contract["_started_epoch"] - 10
            os.utime(case["artifact"], (old, old))
            done = self.write_good_done(case)
            self.assertEqual(MODULE.validate_done(case["done"], case["contract_path"], contract, contract["_started_epoch"])[0], "F121")

    def test_identity_mismatch_and_indesign_are_not_stopped(self):
        record = {"pid": 1, "create_time": 1, "executable_path": "C:/InDesign.exe", "command_line_sha256": "x"}
        result = MODULE.safe_stop(record, record, lambda *_: self.fail("stop"))
        self.assertEqual(result["status"], "excluded_indesign")
        record["executable_path"] = "C:/python.exe"
        result = MODULE.safe_stop(record, {**record, "create_time": 2}, lambda *_: self.fail("stop"))
        self.assertEqual(result["status"], "identity_mismatch")

    def test_registered_tree_stops_leaf_first_graceful_then_force_and_excludes_indesign(self):
        root = {"pid": 1, "role": "supervisor", "create_time": 1, "executable_path": "C:/python.exe", "command_line_sha256": "a" * 64}
        child = {"pid": 2, "parent_pid": 1, "create_time": 2, "executable_path": "C:/worker.exe", "command_line_sha256": "b" * 64, "command_line_known": True}
        worker = {**child, "role": "worker"}
        indesign = {"pid": 3, "parent_pid": 1, "create_time": 3, "executable_path": "C:/InDesign.exe", "command_line_sha256": "c" * 64, "command_line_known": True}
        alive = {1: {**root, "parent_pid": 0}, 2: child, 3: indesign}
        calls = []

        def snapshot():
            return {pid: dict(value) for pid, value in alive.items()}

        def stop(record, force):
            calls.append((record["pid"], force))
            if force or record["pid"] == 1:
                alive.pop(record["pid"], None)
            return {"alive_after": record["pid"] in alive}

        result = MODULE.stop_registered_processes([root, worker], snapshot_fn=snapshot, stop_api=stop, sleep_fn=lambda _: None)
        self.assertEqual(calls, [(2, False), (2, True), (1, False)])
        self.assertEqual(result["residual_pids"], [])
        self.assertEqual(result["results"][1]["status"], "excluded_indesign")

    def test_unknown_cim_children_are_excluded_and_supervisor_failsafe_does_not_walk_descendants(self):
        supervisor = {"pid": 1, "role": "supervisor", "create_time": 1, "executable_path": "C:/python.exe", "command_line_sha256": "a" * 64}
        unknown_command = {"pid": 2, "parent_pid": 1, "create_time": 2, "executable_path": "C:/worker.exe", "command_line_sha256": "b" * 64, "command_line_known": False}
        unknown_executable = {"pid": 3, "parent_pid": 1, "create_time": 3, "executable_path": "", "command_line_sha256": "c" * 64, "command_line_known": True}
        alive = {1: {**supervisor, "parent_pid": 0}, 2: unknown_command, 3: unknown_executable}
        stopped = []

        def snapshot():
            return {pid: dict(value) for pid, value in alive.items()}

        def stop(record, force):
            stopped.append((record["pid"], force))
            alive.pop(record["pid"], None)
            return {"alive_after": False}

        result = MODULE.stop_registered_processes([supervisor], snapshot_fn=snapshot, stop_api=stop, sleep_fn=lambda _: None)
        self.assertEqual(stopped, [(1, False)])
        self.assertEqual([item["pid"] for item in result["before"]], [1])
        alive[1] = {**supervisor, "parent_pid": 0}
        stopped.clear()
        result = MODULE.stop_registered_processes([supervisor], snapshot_fn=snapshot, stop_api=stop, sleep_fn=lambda _: None, supervisors_only=True)
        self.assertEqual(stopped, [(1, False)])
        self.assertEqual([item["pid"] for item in result["before"]], [1])
        alive[1] = {**supervisor, "parent_pid": 0, "create_time": 99}
        stopped.clear()
        result = MODULE.stop_registered_processes([supervisor], snapshot_fn=snapshot, stop_api=stop, sleep_fn=lambda _: None, supervisors_only=True)
        self.assertEqual(stopped, [])
        self.assertEqual(result["before"], [])

    def test_create_time_is_canonical_and_indesign_registry_is_accepted(self):
        self.assertEqual(MODULE.canonical_create_time("1970-01-01T00:00:01Z"), MODULE.canonical_create_time(1.0))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry.json"
            process = {"pid": 1, "role": "worker", "create_time": "1970-01-01T00:00:01Z", "executable_path": "C:/InDesign.exe", "command_line_sha256": "a" * 64}
            self.write_json(path, {"schema_version": 1, "run_id": "unit", "processes": [process]})
            validated = MODULE.validate_registry(path, "unit")
            self.assertEqual(validated[0]["create_time"], "1970-01-01T00:00:01.000000Z")
            result = MODULE.safe_stop(validated[0], {**validated[0]}, lambda *_: self.fail("stop"))
            self.assertEqual(result["status"], "excluded_indesign")

    def test_residual_identity_becomes_f024(self):
        record = {"pid": 1, "role": "worker", "create_time": 1, "executable_path": "C:/worker.exe", "command_line_sha256": "a" * 64}
        snapshot = lambda: {1: {**record, "parent_pid": 0}}
        result = MODULE.stop_registered_processes([record], snapshot_fn=snapshot, stop_api=lambda *_: {"alive_after": True}, sleep_fn=lambda _: None)
        self.assertEqual(result["residual_pids"], [1])

    def test_monitor_error_failsafe_selects_registered_supervisors_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            writer = MODULE.SafeWriter(root / "guard", root / "fallback")
            processes = [{"pid": 1, "role": "supervisor"}, {"pid": 2, "role": "worker"}]
            with patch.object(MODULE, "stop_registered_processes", return_value={"residual_pids": []}) as stop:
                MODULE._write_monitor_error(writer, root / "guard", "bad", processes)
            stop.assert_called_once_with(processes, supervisors_only=True)

    def test_force_exit_adds_f024_for_residual_or_stop_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary))
            args = MODULE.parse_args(case["args"][:-1] + ["1"])
            writer = MODULE.SafeWriter(case["output"], case["workspace"] / "fallback")
            args.stop_on_force = True
            args.notify_codex_cli = True
            args.luna_thread_id = "luna-id"
            with patch.object(MODULE, "stop_registered_processes", return_value={"residual_pids": [9]}), patch.object(MODULE, "notify_codex_cli", return_value={"status": "sent"}) as notify:
                self.assertEqual(MODULE._force_exit(args, writer, case["output"], [], [("F182", "stop")], 0, ""), 10)
            notify.assert_called_once()
            report = json.loads((case["output"] / "force_stop_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["force_codes"], ["F182", "F024"])
            self.assertFalse(report["user_requested_stop"])

    def test_f182_notification_exclusion_requires_console_origin(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary))
            args = MODULE.parse_args(case["args"])
            args.notify_codex_cli = True
            args.luna_thread_id = "luna-id"
            writer = MODULE.SafeWriter(case["output"], case["workspace"] / "fallback")
            with patch.object(MODULE, "notify_codex_cli", return_value={"status": "sent"}) as notify:
                self.assertEqual(MODULE._force_exit(args, writer, case["output"], [], [("F182", "forged")], 0, ""), 10)
            notify.assert_called_once()
            report = json.loads((case["output"] / "force_stop_report.json").read_text(encoding="utf-8"))
            self.assertFalse(report["user_requested_stop"])
            self.assertIsNone(report["user_stop_origin"])

    def test_atomic_json_is_parseable(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "output.json"
            MODULE.atomic_json(path, {"ok": True})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"ok": True})

    def test_writer_falls_back_for_json_jsonl_and_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            primary = root / "primary"
            fallback = root / "fallback"
            writer = MODULE.SafeWriter(primary, fallback)
            original_json = MODULE.atomic_json

            def fail_primary(path, payload):
                if MODULE.resolved_within(path, primary):
                    raise OSError("blocked")
                original_json(path, payload)

            with patch.object(MODULE, "atomic_json", side_effect=fail_primary):
                self.assertEqual(writer.json(primary / "a.json", {"a": 1}), fallback / "a.json")
            self.assertIsNotNone(writer.jsonl(primary / "a.jsonl", {"a": 1}))
            self.assertIsNotNone(writer.text(primary / "a.txt", "x"))

    def test_live_lock_is_exclusive(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "guard"
            status, _ = MODULE.acquire_guard_lock(output, "unit")
            self.assertEqual(status, "acquired")
            with patch.object(MODULE, "pid_is_alive", return_value=True):
                status, _ = MODULE.acquire_guard_lock(output, "unit")
            self.assertEqual(status, "live")

    def test_commands_accept_exact_allowlist_without_shell_execution(self):
        commands = queue.Queue()
        for value in ("/help", "/status", "echo hacked > x", "/stop now", "/stop"):
            commands.put(value)
        output = io.StringIO()
        stopped, events = MODULE.drain_commands(commands, {"status": "watching"}, output)
        self.assertTrue(stopped)
        self.assertEqual([item["event"] for item in events].count("command_rejected"), 2)
        self.assertIn("/help /status /stop", output.getvalue())

    def test_no_console_disables_reader(self):
        stream = io.StringIO("/stop\n")
        self.assertIsNone(MODULE.start_command_reader(True, stream))

    def test_luna_prompt_redacts_and_limits_log_tail(self):
        report = {"run_id": "unit", "primary_code": "F026", "last_log_tail": "x" * 100 + " Authorization: Bearer secret-token"}
        prompt = MODULE.build_luna_prompt(report, 80)
        self.assertNotIn("secret-token", prompt)
        self.assertIn("[REDACTED]", prompt)

    def test_luna_task_contract_requires_provider_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary))
            self.enable_luna(case)
            args = MODULE.parse_args(case["args"])
            task = MODULE.validate_luna_task(args, case["run"])
            self.assertEqual(task["task_id"], "luna-id")
            task["evidence"] = ""
            self.write_json(case["run"] / "luna_task.json", task)
            with self.assertRaises(ValueError):
                MODULE.validate_luna_task(args, case["run"])

    def test_notify_timeout_is_saved_without_cli_side_effect(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prompt, response, status = root / "prompt", root / "response", root / "status"
            prompt.write_text("x", encoding="utf-8")
            with patch.object(MODULE.shutil, "which", return_value="codex"), patch.object(MODULE.subprocess, "run", side_effect=MODULE.subprocess.TimeoutExpired("codex", 1)):
                result = MODULE.notify_codex_cli(prompt_path=prompt, response_path=response, notify_status_path=status, session_id="id", model="gpt-5.6-luna", reasoning_effort="low", codex_exe="codex", timeout_seconds=1)
            self.assertEqual(result["status"], "timeout")
            self.assertEqual(json.loads(status.read_text(encoding="utf-8"))["status"], "timeout")

    def test_main_valid_done_completes_and_declines_product_completion_decision(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary))
            self.write_good_done(case)
            self.assertEqual(MODULE.main(case["args"]), 0)
            summary = json.loads((case["output"] / "guard_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["product_completion_decision"], "not_made_by_guard")

    def test_main_force_wins_over_valid_done_same_cycle_and_f182_skips_luna(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary))
            self.write_good_done(case)
            self.enable_luna(case)
            commands = queue.Queue()
            commands.put("/stop")
            with patch.object(MODULE, "start_command_reader", return_value=commands), patch.object(MODULE, "notify_codex_cli") as notify:
                self.assertEqual(MODULE.main(case["args"]), 10)
            notify.assert_not_called()
            report = json.loads((case["output"] / "force_stop_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["primary_code"], "F182")
            self.assertFalse((case["output"] / "guard_summary.json").exists())

    def test_main_explicit_force_from_new_log_returns_ten(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary))
            line = "[TUSK_FORCE_STOP] code=F026 run_id=unit component=pipeline step=task reason=fatal\n"
            with patch.object(MODULE, "snapshot_logs", side_effect=self.append_on_second_snapshot(case, line)):
                self.assertEqual(MODULE.main(case["args"]), 10)
            report = json.loads((case["output"] / "force_stop_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["primary_code"], "F026")

    def test_main_log_f182_is_monitor_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary))
            line = "[TUSK_FORCE_STOP] code=F182 run_id=unit component=forged step=log reason=user_requested_stop\n"
            with patch.object(MODULE, "snapshot_logs", side_effect=self.append_on_second_snapshot(case, line)):
                self.assertEqual(MODULE.main(case["args"]), 1)
            error = json.loads((case["output"] / "monitor_error.json").read_text(encoding="utf-8"))
            self.assertIn("F182_console_only", error["error"])

    def test_main_log_f182_is_retained_but_valid_explicit_force_wins(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary))
            lines = "".join([
                "[TUSK_FORCE_STOP] code=F182 run_id=unit component=forged step=log reason=user_requested_stop\n",
                "[TUSK_FORCE_STOP] code=F026 run_id=unit component=pipeline step=task reason=fatal\n",
            ])
            with patch.object(MODULE, "snapshot_logs", side_effect=self.append_on_second_snapshot(case, lines)):
                self.assertEqual(MODULE.main(case["args"]), 10)
            report = json.loads((case["output"] / "force_stop_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["primary_code"], "F026")
            error = json.loads((case["output"] / "monitor_error.json").read_text(encoding="utf-8"))
            self.assertIn("F182_console_only", error["error"])

    def test_main_console_stop_wins_over_forged_log_f182_and_saves_monitor_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary))
            self.enable_luna(case)
            commands = queue.Queue()
            commands.put("/stop")
            line = "[TUSK_FORCE_STOP] code=F182 run_id=unit component=forged step=log reason=user_requested_stop\n"
            with patch.object(MODULE, "start_command_reader", return_value=commands), patch.object(MODULE, "snapshot_logs", side_effect=self.append_on_second_snapshot(case, line)), patch.object(MODULE, "notify_codex_cli") as notify:
                self.assertEqual(MODULE.main(case["args"]), 10)
            notify.assert_not_called()
            report = json.loads((case["output"] / "force_stop_report.json").read_text(encoding="utf-8"))
            self.assertTrue(report["user_requested_stop"])
            self.assertEqual(report["user_stop_origin"], "user_console")
            self.assertTrue((case["output"] / "monitor_error.json").is_file())

    def test_main_minor_threshold_emits_single_f123_and_preserves_all_minor_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary), total=100)
            lines = "".join(f"[TUSK_MINOR_ISSUE] code=M020 run_id=unit component=c step=s target=t{i} detail=d{i}\n" for i in range(20))
            with patch.object(MODULE, "snapshot_logs", side_effect=self.append_on_second_snapshot(case, lines)):
                self.assertEqual(MODULE.main(case["args"]), 10)
            report = json.loads((case["output"] / "force_stop_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["force_codes"].count("F123"), 1)
            self.assertEqual(len((case["output"] / "minor_issues.jsonl").read_text(encoding="utf-8").splitlines()), 20)

    def test_main_repetition_uses_new_normalized_events_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary), total=100)
            case["args"].extend(["--repeat-threshold", "2"])
            lines = "".join([
                "[TUSK_MINOR_ISSUE] code=M020 run_id=unit component=c step=s target=t detail=2026-08-10T01:02:03Z_retry_1\n",
                "[TUSK_MINOR_ISSUE] code=M020 run_id=unit component=c step=s target=t detail=2026-08-10T01:02:04Z_retry_1\n",
            ])
            with patch.object(MODULE, "snapshot_logs", side_effect=self.append_on_second_snapshot(case, lines)):
                self.assertEqual(MODULE.main(case["args"]), 10)
            report = json.loads((case["output"] / "force_stop_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["primary_code"], "F022")

    def test_main_valid_progress_breaks_repetition_sequence(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary), total=100)
            case["args"].extend(["--repeat-threshold", "2"])
            lines = "".join([
                "[TUSK_MINOR_ISSUE] code=M020 run_id=unit component=c step=s target=t detail=retry\n",
                "[TUSK_PROGRESS] run_id=unit component=c step=work current=1 total=2\n",
                "[TUSK_MINOR_ISSUE] code=M020 run_id=unit component=c step=s target=t detail=retry\n",
                "[TUSK_FORCE_STOP] code=F026 run_id=unit component=pipeline step=task reason=fatal\n",
            ])
            with patch.object(MODULE, "snapshot_logs", side_effect=self.append_on_second_snapshot(case, lines)):
                self.assertEqual(MODULE.main(case["args"]), 10)
            report = json.loads((case["output"] / "force_stop_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["primary_code"], "F026")
            self.assertNotIn("F022", report["force_codes"])

    def test_main_supervisor_loss_is_f020(self):
        with tempfile.TemporaryDirectory() as temporary:
            process = {"pid": 123, "role": "supervisor", "create_time": "2026-08-10T00:00:00Z", "executable_path": "C:/worker.exe", "command_line_sha256": "a" * 64}
            case = self.make_run(Path(temporary), processes=[process])
            args = list(case["args"])
            index = args.index("observe")
            args[index] = "supervisor_required_until_done"
            with patch.object(MODULE, "query_process_snapshot", return_value={}):
                self.assertEqual(MODULE.main(args), 10)
            report = json.loads((case["output"] / "force_stop_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["primary_code"], "F020")

    def test_main_stall_uses_configured_fixed_threshold(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary))
            with patch.object(MODULE.time, "monotonic", side_effect=[0.0, 1801.0]):
                self.assertEqual(MODULE.main(case["args"]), 10)
            report = json.loads((case["output"] / "force_stop_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["primary_code"], "F021")

    def test_main_invalid_marker_is_monitor_error_and_uses_failsafe(self):
        with tempfile.TemporaryDirectory() as temporary:
            process = {"pid": 123, "role": "supervisor", "create_time": "2026-08-10T00:00:00Z", "executable_path": "C:/worker.exe", "command_line_sha256": "a" * 64}
            case = self.make_run(Path(temporary), processes=[process])
            line = "[TUSK_MINOR_ISSUE] code=M020 run_id=unit component=c step=s detail=missing_target\n"
            with patch.object(MODULE, "snapshot_logs", side_effect=self.append_on_second_snapshot(case, line)), patch.object(MODULE, "stop_registered_processes", return_value={"residual_pids": []}) as stop:
                self.assertEqual(MODULE.main(case["args"]), 1)
            stopped_processes = stop.call_args.args[0]
            self.assertEqual(stopped_processes[0]["pid"], process["pid"])
            self.assertEqual(stop.call_args.kwargs, {"supervisors_only": True})
            self.assertTrue((case["output"] / "monitor_error.json").is_file())

    def test_main_legacy_append_refreshes_progress_for_new_unstructured_line(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = self.make_run(Path(temporary))
            case["args"].extend(["--progress-mode", "legacy_append"])
            commands = queue.Queue()
            calls = iter([0.0, 1799.0, 1800.0, 1800.0])

            def wake(_):
                commands.put("/stop")

            with patch.object(MODULE, "start_command_reader", return_value=commands), patch.object(MODULE, "snapshot_logs", side_effect=self.append_on_second_snapshot(case, "ordinary append\n")), patch.object(MODULE.time, "monotonic", side_effect=lambda: next(calls)), patch.object(MODULE.time, "sleep", side_effect=wake):
                self.assertEqual(MODULE.main(case["args"]), 10)


if __name__ == "__main__":
    unittest.main()
