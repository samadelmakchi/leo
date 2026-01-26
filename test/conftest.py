"""
Conftest Test
"""

import pytest
import os
from datetime import datetime

@pytest.fixture(scope="session", autouse=True)
def environment_setup():
    """تنظیم متغیرهای محیطی از Ansible"""
    os.environ["GATEWAY_URL"] = f"https://{os.getenv('CUSTOMER_SUBDOMAIN_GATEWAY')}.{os.getenv('CUSTOMER_DOMAIN')}"
    os.environ["PORTAL_URL"] = f"https://{os.getenv('CUSTOMER_SUBDOMAIN_PORTAL')}.{os.getenv('CUSTOMER_DOMAIN')}"
    os.environ["BACKEND_URL"] = f"https://{os.getenv('CUSTOMER_SUBDOMAIN_BACKENDPORTAL')}.{os.getenv('CUSTOMER_DOMAIN')}"
    os.environ["CUSTOMER"] = os.getenv('INVENTORY_HOSTNAME', 'unknown')

@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    customer = os.getenv("CUSTOMER", "unknown")
    config._metadata.update({
        "Project": "LEO",
        "Customer": customer,
        "Environment": "Production" if "test" not in customer.lower() else "Testing",
        "Deploy Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })