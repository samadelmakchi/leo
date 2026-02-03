"""
Smoke Test
"""

import pytest
from .base import BaseTest

class TestSmoke(BaseTest):
    def test_gateway_homepage_loads(self):
        r = self.session.get(self.gateway, timeout=15)
        assert r.status_code == 200
        assert "Calibri" in r.text or "login" in r.text.lower()

    def test_portal_loads(self):
        r = self.session.get(self.portal, timeout=15)
        assert r.status_code == 200
        assert any(x in r.text.lower() for x in ["portal", "dashboard", "react"])

    def test_backend_api_responds(self):
        r = self.session.get(f"{self.backend}/api/health", timeout=10)
        assert r.status_code in [200, 401]