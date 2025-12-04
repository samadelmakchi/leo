from locust import HttpUser, task, between, tag
import os

class CalibriUser(HttpUser):
    wait_time = between(2, 8)
    host = os.getenv("PORTAL_URL", "https://portal.simnad.com")

    @tag("load")
    @task(5)
    def visit_homepage(self):
        self.client.get("/", verify=False)

    @task(3)
    def visit_dashboard(self):
        self.client.get("/dashboard", verify=False)

    @task(2)
    def api_call(self):
        self.client.get("/api/health", verify=False)

    @task(1)
    def heavy_report(self):
        self.client.get("/reports/sales", verify=False)