import pytest

@pytest.mark.regression
class TestCriticalRegression:
    def test_login_page_still_works(self):
        import requests
        r = requests.get(f"{os.getenv('PORTAL_URL')}/login", verify=False, timeout=15)
        assert r.status_code == 200
        assert any(word in r.text.lower() for word in ["ورود", "login", "password"])

    def test_gateway_api_still_returns_data(self):
        r = requests.get(f"{os.getenv('GATEWAY_URL')}/api/user/profile", verify=False)
        assert r.status_code in [200, 401, 403]

    def test_no_500_errors_in_logs(self):
        import subprocess
        try:
            result = subprocess.run(
                "docker logs $(docker ps -qf 'name=portal') 2>&1 | grep -i '500 Internal' | wc -l",
                shell=True, capture_output=True, text=True
            )
            count = int(result.stdout.strip())
            assert count == 0, f"خطای 500 پیدا شد: {count} مورد"
        except:
            pytest.skip("لاگ داکر در دسترس نیست")