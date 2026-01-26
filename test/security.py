"""
Security Test
"""

import requests

class TestSecurity:
    def test_security_headers_present(self):
        urls = [
            os.getenv("GATEWAY_URL"),
            os.getenv("PORTAL_URL"),
            os.getenv("BACKEND_URL")
        ]
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy"
        ]
        for url in urls:
            r = requests.get(url, verify=False)
            missing = [h for h in required_headers if h not in r.headers]
            assert not missing, f"Missing headers on {url}: {missing}"

    def test_no_debug_info_exposed(self):
        r = requests.get(f"{os.getenv('BACKEND_URL')}/api/debug", verify=False)
        assert r.status_code != 200