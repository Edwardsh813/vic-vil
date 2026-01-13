#!/usr/bin/env python3
"""Quick inspection of mywateradvisor2.com"""

import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Loading mywateradvisor2.com...")
        await page.goto("https://mywateradvisor2.com/", wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(5000)

        # Save screenshot
        await page.screenshot(path='homepage.png', full_page=True)
        print("Saved: homepage.png")

        # Get page text
        text = await page.inner_text('body')
        print("\n=== PAGE TEXT ===")
        print(text[:2000])

        # Look for links
        links = await page.query_selector_all('a')
        print(f"\n=== FOUND {len(links)} LINKS ===")
        for link in links[:20]:
            try:
                href = await link.get_attribute('href')
                text = await link.inner_text()
                print(f"  {text.strip()[:30]}: {href}")
            except:
                pass

        # Look for buttons
        buttons = await page.query_selector_all('button')
        print(f"\n=== FOUND {len(buttons)} BUTTONS ===")
        for btn in buttons[:20]:
            try:
                text = await btn.inner_text()
                print(f"  Button: {text.strip()[:50]}")
            except:
                pass

        # Save HTML
        html = await page.content()
        with open('homepage.html', 'w') as f:
            f.write(html)
        print("\nSaved: homepage.html")

        await browser.close()

asyncio.run(main())
