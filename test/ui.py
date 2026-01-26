"""
UI Test
"""

import pytest
from playwright.sync_api import sync_playwright

@pytest.mark.ui
def test_portal_login_page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(os.getenv("PORTAL_URL"), wait_until="networkidle", timeout=30000)
        page.wait_for_selector("text=ورود", timeout=10000)
        assert page.title()
        browser.close()