import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from brew2port.cli import main


class TestGuide(unittest.TestCase):
    def test_no_argument_guide_describes_safe_shared_workflow(self):
        output = io.StringIO()
        with patch.object(sys, "argv", ["brew2port"]), redirect_stdout(output):
            main()
        guide = output.getvalue()
        for phrase in (
            "Inventory explicitly requested Homebrew packages",
            "brew2port prepare",
            "migration-preview.csv",
            "dry run",
            "--install",
            "brew2port verify",
            "never removed automatically",
        ):
            self.assertIn(phrase, guide)
        self.assertNotIn("brew uninstall", guide)


class TestMigrateYes(unittest.TestCase):
    def test_yes_skips_interactive_followup_for_remaining(self):
        plan = [{"homebrew": "wget", "candidates": []}]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as handle:
            json.dump(plan, handle)
            path = handle.name
        argv = ["brew2port", "migrate", "--plan", path, "--install", "--yes", "--mode", "near-hit"]

        def no_prompt(prompt):
            raise AssertionError("unattended --yes run must not prompt")

        with patch.object(sys, "argv", argv), patch("builtins.input", no_prompt):
            output = io.StringIO()
            with redirect_stdout(output):
                main()
        data = json.loads(output.getvalue().split("\n\n")[0])
        self.assertEqual(data[0]["status"], "intentionally-retained")
