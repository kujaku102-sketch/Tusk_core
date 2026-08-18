import argparse
import json
from pathlib import Path


RULES = (
    (("indesign_pid.py", "watch_pipeline.py"), ("test_spec014_pid_scope.py", "test_spec035_window_log_consolidation.py")),
    (("pipeline_runtime.py", "main.py"), ("test_spec015_checkpoint_contract.py", "test_spec026_gui_close_contract.py")),
    (("translation_backends.py", "translate_tsv.py"), ("test_spec031_token_mismatch_relaxation.py", "test_spec037_translation_batch_size.py")),
    (("3_apply_default_style.jsx", "4_autoshrink_text.js"), ("test_spec009_style_contract.py", "test_spec032_marker_style_application.py")),
    (("learning_package_export.py",), ("test_learning_package_export_redesign.py",)),
)


def select(changed):
    selected = set()
    normalized = [Path(path).name.casefold() for path in changed]
    for names, tests in RULES:
        if any(name.casefold() in normalized for name in names):
            selected.update(tests)
    return sorted(selected)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args(argv)
    tests = select(args.paths)
    print(json.dumps({"changed": args.paths, "tests": tests, "needs_review": not bool(tests)}, ensure_ascii=False))
    return 0 if tests else 3


if __name__ == "__main__":
    raise SystemExit(main())
