"""Headless browser management using Playwright."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright


@asynccontextmanager
async def get_browser() -> AsyncGenerator[Browser, None]:
    """Get a headless Chromium browser instance."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            yield browser
        finally:
            await browser.close()


@asynccontextmanager
async def get_page(
    browser: Browser,
    *,
    mobile: bool = False,
    width: int = 1920,
    height: int = 1080,
) -> AsyncGenerator[Page, None]:
    """Get a browser page with configurable viewport."""
    if mobile:
        device = {
            "viewport": {"width": 375, "height": 812},
            "user_agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/17.0 Mobile/15E148 Safari/604.1"
            ),
            "device_scale_factor": 3,
            "is_mobile": True,
            "has_touch": True,
        }
        context = await browser.new_context(**device)
    else:
        context = await browser.new_context(
            viewport={"width": width, "height": height},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

    page = await context.new_page()
    try:
        yield page
    finally:
        await context.close()


async def render_page(url: str, *, wait_until: str = "networkidle", timeout: int = 30000) -> str:
    """Render a page with a headless browser and return the full HTML."""
    async with get_browser() as browser:
        async with get_page(browser) as page:
            await page.goto(url, wait_until=wait_until, timeout=timeout)
            return await page.content()


async def take_screenshot(
    url: str,
    output_path: str,
    *,
    full_page: bool = True,
    mobile: bool = False,
) -> str:
    """Take a screenshot of a URL and save it to output_path."""
    async with get_browser() as browser:
        async with get_page(browser, mobile=mobile) as page:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.screenshot(path=output_path, full_page=full_page)
            return output_path


def render_page_sync(url: str, **kwargs) -> str:
    """Synchronous wrapper for render_page."""
    return asyncio.run(render_page(url, **kwargs))


def take_screenshot_sync(url: str, output_path: str, **kwargs) -> str:
    """Synchronous wrapper for take_screenshot."""
    return asyncio.run(take_screenshot(url, output_path, **kwargs))
