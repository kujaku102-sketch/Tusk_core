import json
import sys
import tempfile
import unittest
from pathlib import Path

from runtime import orchestrator as module


class OrchestratorTests(unittest.TestCase):
    def task(self, number):
        return {"slice_id": f"slice-{number:02d}", "objective": "x", "readable_paths": [], "writable_paths": [f"part{number}/a.py"], "input_contract": {}, "output_contract": {}, "dependencies": [], "acceptance_test": "test", "forbidden_changes": []}

    def test_runs_three_slices_and_validates_results(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            helper = root / "agent.py"
            helper.write_text("import json,sys\nfrom pathlib import Path\nt=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))\nr={'schema_version':1,'slice_id':t['slice_id'],'status':'success','changed_files':t['writable_paths'],'tests':['ok'],'summary':'done','issues':[]}\nPath(sys.argv[2]).write_text(json.dumps(r),encoding='utf-8')\n", encoding="utf-8")
            plan = {"schema_version": 1, "route": "SPLIT", "reason": "test", "slices": [self.task(1), self.task(2), self.task(3)]}
            report = module.run_plan(plan, [sys.executable, str(helper), "{slice}", "{result}"], root / "tasks", root / "results", 10, root)
            self.assertEqual("success", report["status"])
            self.assertEqual(3, len(report["results"]))

    def test_overlapping_paths_are_rejected(self):
        first = self.task(1)
        second = self.task(2)
        second["writable_paths"] = first["writable_paths"]
        with self.assertRaises(ValueError):
            module.validate_plan({"schema_version": 1, "route": "SPLIT", "reason": "x", "slices": [first, second]})

    def test_stop_route_does_not_launch(self):
        result = module.run_plan({"schema_version": 1, "route": "STOP", "reason": "protected", "slices": []}, ["unused", "{slice}", "{result}"], Path("x"), Path("y"), 1)
        self.assertEqual("needs_review", result["status"])

    def test_default_command_is_antigravity_flash(self):
        command = module.command_template(None)
        self.assertEqual("agy", command[0])
        self.assertIn("gemini-3.6-flash-medium", command)

    def test_missing_result_keeps_cli_diagnostics(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            helper = root / "agent.py"
            helper.write_text("print('not-json')\n", encoding="utf-8")
            result = module.run_slice(self.task(1), [sys.executable, str(helper), "{slice}", "{result}"], root / "tasks", root / "results", 10, root)
            self.assertEqual("F002", result["code"])
            self.assertEqual("not-json\n", result["stdout_tail"])

    def test_accepts_agy_structured_output_wrapper(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            helper = root / "agent.py"
            inner = {"schema_version": 1, "slice_id": "slice-01", "status": "success", "changed_files": [], "tests": [], "summary": "ok", "issues": []}
            helper.write_text("import json\nprint(json.dumps({'status':'SUCCESS','structured_output':" + repr(inner) + "}))\n", encoding="utf-8")
            result = module.run_slice(self.task(1), [sys.executable, str(helper), "{slice}", "{result}"], root / "tasks", root / "results", 10, root)
            self.assertEqual("success", result["status"])


if __name__ == "__main__":
    unittest.main()
