"""
API Test
"""

import pytest
import json

class TestAPI:
    @pytest.mark.api
    def test_gateway_health_endpoint(self):
        import requests
        r = requests.get(f"{os.getenv('GATEWAY_URL')}/health", verify=False, timeout=10)
        assert r.status_code == 200
        data = r.json() if r.headers.get('content-type') == 'application/json' else {}
        assert data.get("status") == "ok" or "OK" in r.text

    @pytest.mark.api
    def test_portal_api_version(self):
        r = requests.get(f"{os.getenv('BACKEND_URL')}/api/v1/version", verify=False)
        assert r.status_code == 200
        assert "version" in r.text.lower()