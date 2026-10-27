"""VPN-2 preparation checks; no service installation or production changes."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
UNIT = ROOT / "services/recovery_enrollment/systemd/redeti-recovery-broker-staging.service"
PLAN = ROOT / "services/recovery_enrollment/VPN2_DEPLOYMENT_PLAN.md"


class Vpn2PreparationTests(unittest.TestCase):
    def test_staging_unit_is_closed_and_not_enableable(self):
        unit = UNIT.read_text()
        self.assertIn("User=redeti-recovery", unit)
        self.assertIn("Group=redeti-recovery", unit)
        self.assertIn("--serve-closed", unit)
        self.assertIn("RuntimeDirectoryMode=0700", unit)
        self.assertIn("UMask=0077", unit)
        self.assertIn("NoNewPrivileges=yes", unit)
        self.assertIn("ProtectSystem=strict", unit)
        self.assertIn("PrivateDevices=yes", unit)
        self.assertIn("IPAddressDeny=any", unit)
        self.assertIn("IPAddressAllow=localhost", unit)
        self.assertIn("CapabilityBoundingSet=", unit)
        self.assertNotIn("\n[Install]\n", "\n" + unit + "\n")
        self.assertNotIn("enable_key_issuance=True", unit)
        self.assertNotIn("oauth-client-secret", unit)

    def test_plan_keeps_activation_and_external_ingress_gated(self):
        plan = PLAN.read_text()
        for expected in (
            "PREPARADO, NÃO ATIVADO",
            "serviço foi instalado",
            "foi alterado",
            "auth key real foi emitida",
            "Service Desk",
            "OAuth",
            "HTTPS",
            "rollback",
        ):
            self.assertIn(expected, plan)
        self.assertNotRegex(plan, re.compile(r"tskey-auth-[A-Za-z0-9]{20,}"))
        self.assertNotRegex(plan, re.compile(r"BEGIN .*PRIVATE KEY"))

    def test_public_contract_keeps_operator_route_private(self):
        contract = (ROOT / "services/recovery_enrollment/openapi.yaml").read_text()
        self.assertIn("This route is NOT public", contract)
        self.assertIn("OperatorSession", contract)
        self.assertIn("https://enrollment.example.invalid", contract)
        self.assertNotIn("https://api.tailscale.com", contract)


if __name__ == "__main__":
    unittest.main()
