"""Regression for the vision attachment leaking the source fixture directory."""
import os
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

from run import run_task


class VisionIsolation(unittest.TestCase):
    def test_attachment_points_to_the_editable_copy(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory(dir=Path(__file__).parent) as protected:
            root = Path(tmp)
            task = root / "08-vision"
            fixture = task / "fixture"
            fixture.mkdir(parents=True)
            (fixture / "styles.css").write_text("broken")
            (task / "prompt.md").write_text("Fix styles.css from the screenshot.")
            (task / "screenshot.png").write_bytes(b"test attachment")
            (task / "verify.sh").write_text('[ "$(cat styles.css)" = fixed ]\n')
            binary = root / "bin"
            binary.mkdir()
            pi = binary / "pi"
            pi.write_text('''#!/usr/bin/env python3
import os, sys
from pathlib import Path
image = Path(next(a[1:] for a in sys.argv[1:] if a.startswith("@")))
folder = image.resolve().parent
target = folder / "styles.css"
if not target.exists():
    target = folder / "fixture" / "styles.css"
target.write_text("fixed")
canary = os.environ.get("EVAL_ISOLATION_CANARY")
if canary:
    try:
        Path(canary).write_text("changed")
    except PermissionError:
        pass
''')
            pi.chmod(0o755)
            canary = Path(protected) / "canary.txt"
            canary.write_text("unchanged")
            environment = {"PATH": str(binary) + os.pathsep + os.environ["PATH"]}
            if sys.platform == "darwin":
                environment["EVAL_ISOLATION_CANARY"] = str(canary)
            with patch.dict(os.environ, environment):
                result, _ = run_task(task, "test/model", 10, False, "pi", "xhigh")
            self.assertEqual(result["status"], "pass", result)
            self.assertEqual((fixture / "styles.css").read_text(), "broken")
            self.assertEqual(canary.read_text(), "unchanged")


if __name__ == "__main__":
    unittest.main()
