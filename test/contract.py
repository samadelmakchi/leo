"""
Contract Test
"""

import requests
import json
import os

@pytest.mark.contract
def test_api_contract_compliance():
    url = f"{os.getenv('BACKEND_URL')}/api/v1/contract"
    if not url.startswith("http"):
        pytest.skip("BACKEND_URL تنظیم نشده")

    r = requests.get(url, verify=False, timeout=10)
    assert r.status_code == 200

    try:
        data = r.json()
    except json.JSONDecodeError:
        pytest.fail("پاسخ JSON معتبر نیست")

    expected_keys = {"version", "endpoints", "auth", "rate_limit"}
    missing = expected_keys - data.keys()
    assert not missing, f"کلیدهای قرارداد گم شده: {missing}"

    assert isinstance(data["endpoints"], list)
    assert len(data["endpoints"]) > 0