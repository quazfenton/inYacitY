import asyncio

from playwright.async_api import async_playwright, Playwright
from recognizer.agents.playwright import AsyncChallenger


async def run(playwright: Playwright):
    browser = await playwright.chromium.launch()
    page = await browser.new_page()

    challenger = AsyncChallenger(page, click_timeout=1000)
    await page.goto("https://recaptcha-demo.appspot.com/recaptcha-v2-checkbox-explicit.php")

    await challenger.solve_recaptcha()

    await browser.close()


async def main():
    async with async_playwright() as playwright:
        await run(playwright)


asyncio.run(main())