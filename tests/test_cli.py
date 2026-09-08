import io
import sys
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
