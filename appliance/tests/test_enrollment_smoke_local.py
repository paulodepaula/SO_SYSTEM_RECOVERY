"""Require the on-Hermes dry-run to exercise full fake enrollment."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.recovery_enrollment.smoke_local import check


class FullLocalSmokeTest(unittest.TestCase):
    def test_private_http_agent_signed_operator_and_single_mock_issuance(self):
        check()


if __name__ == "__main__":
    unittest.main()
