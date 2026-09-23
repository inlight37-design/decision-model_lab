"""Temporary review observation capture; removed before the final review PR."""
import subprocess
import sys
import unittest
from pathlib import Path


class A1ReviewObservationCapture(unittest.TestCase):
    def test_capture_review_observations(self):
        root = Path(__file__).resolve().parents[1]
        script = root / "docs/reviews/2026-09-23-a1-handoff-review/reproduce.py"
        result = subprocess.run([sys.executable, str(script), "--repo", str(root)],
                                capture_output=True, text=True, timeout=90)
        print(result.stdout, flush=True)
        if result.stderr:
            print(result.stderr, flush=True)
        self.assertEqual(result.returncode, 0, "Observation procedure did not complete")
