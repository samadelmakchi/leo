"""
Performance Test
"""

import time
import statistics

def test_response_time_under_3_seconds():
    import requests
    urls = [
        os.getenv("GATEWAY_URL"),
        os.getenv("PORTAL_URL"),
        f"{os.getenv('BACKEND_URL')}/api/health"
    ]
    times = []
    for url in urls:
        start = time.time()
        requests.get(url, verify=False, timeout=10)
        elapsed = time.time() - start
        times.append(elapsed)
        assert elapsed < 3.0, f"{url} took {elapsed:.2f}s"
    avg = statistics.mean(times)
    print(f"Average response time: {avg:.2f}s")