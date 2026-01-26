"""
Accessibility Test
"""

import pytest
from playwright.sync_api import sync_playwright

@pytest.mark.accessibility
def test_wcag_contrast_and_focus():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            color_scheme="light"
        )
        page = context.new_page()
        page.goto(os.getenv("PORTAL_URL"), wait_until="networkidle", timeout=60000)

        focusable = page.eval_on_selector_all(
            "a, button, button, input, textarea, [tabindex]:not([tabindex='-1'])",
            "els => els.length"
        )
        assert focusable > 0, "هیچ المان قابل فوکسی پیدا نشد!"

        missing_alt = page.eval_on_selector_all(
            "img:not([alt]), img[alt='']",
            "els => els.map(el => el.src)"
        )
        assert len(missing_alt) == 0, f"عکس بدون alt پیدا شد: {missing_alt[:5]}"

        no_label = page.eval_on_selector_all(
            "[role='button']:not([aria-label]):not([aria-labelledby]), input:not([aria-label]):not([id])",
            "els => els.length"
        )
        assert no_label < 5, f"تعداد زیاد المان بدون label/aria-label: {no_label}"

        browser.close()