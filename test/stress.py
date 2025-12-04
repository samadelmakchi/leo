import pytest
import requests
import threading
import time

@pytest.mark.stress
def test_system_under_extreme_concurrent_requests():
    url = f"{os.getenv('GATEWAY_URL')}/health"
    success_count = 0
    failure_count = 0
    total_requests = 500

    def make_request():
        nonlocal success_count, failure_count
        try:
            r = requests.get(url, verify=False, timeout=5)
            if r.status_code == 200:
                success_count += 1
            else:
                failure_count += 1
        except:
            failure_count += 1

    threads = []
    for _ in range(total_requests):
        t = threading.Thread(target=make_request)
        t.start()
        threads.append(t)

    for t in threads:
        t.join(timeout=30)

    success_rate = success_count / total_requests * 100
    print(f"\nStress Test Result: {success_count}/{total_requests} موفق ({success_rate:.1f}%)")
    assert success_rate >= 95, f"نرخ موفقیت زیر 95%: فقط {success_rate:.1f}%"