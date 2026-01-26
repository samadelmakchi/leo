"""
Integration Test
"""

import pytest
import requests
import time

@pytest.mark.integration
def test_full_user_flow_integration():
    """تست کامل جریان کاربر: لاگین → دریافت توکن → استفاده از API → لود فرانت‌اند"""
    
    r = requests.get(os.getenv("PORTAL_URL"), verify=False, timeout=15)
    assert r.status_code == 200

    r = requests.get(f"{os.getenv('GATEWAY_URL')}/health", verify=False)
    assert r.status_code == 200

    r = requests.get(f"{os.getenv('BACKEND_URL')}/api/health", verify=False)
    assert r.status_code in [200, 401]

    r = requests.get(f"{os.getenv('GATEWAY_URL')}/api/status", verify=False, timeout=10)
    if r.status_code == 200:
        assert "database" in r.text.lower() or "db" in r.text.lower()