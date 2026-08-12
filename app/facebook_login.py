"""
Run this once, manually: `python -m app.sources.facebook_login`
A real browser window opens - log into Facebook yourself (handle 2FA etc),
then press Enter in the terminal. Your session gets saved to fb_session.json
so facebook.py can reuse it headlessly afterward.

Re-run this whenever the session expires or Facebook logs you out.
"""
import asyncio
from playwright.async_api import async_playwright
from . import facebook


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://www.facebook.com/login")

        input("Log in in the opened browser window, then press Enter here...")

        await context.storage_state(path=facebook.SESSION_FILE)
        print(f"Session saved to {facebook.SESSION_FILE}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
