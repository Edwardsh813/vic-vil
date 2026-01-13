#!/usr/bin/env python3
"""
Automated Account Registration for mywateradvisor2.com
Goes directly to: https://mywateradvisor2.com/register/account
"""

import asyncio
from playwright.async_api import async_playwright

# Remaining 16 Victorian Village meters (250 Harper already done)
ACCOUNTS = [
    # {"email": "victorianvillageapts+250harper@gmail.com", "account": "1092140000w", "address": "250 Harper Street"},  # DONE
    {"email": "victorianvillageapts+300harper@gmail.com", "account": "1092142000w", "address": "300 Harper Street"},
    {"email": "victorianvillageapts+350harper@gmail.com", "account": "1092143000w", "address": "350 Harper Street"},
    {"email": "victorianvillageapts+400harper@gmail.com", "account": "1092144000w", "address": "400 Harper Street"},
    {"email": "victorianvillageapts+450harper@gmail.com", "account": "1092145000w", "address": "450 Harper Street"},
    {"email": "victorianvillageapts+500harper@gmail.com", "account": "1092147000w", "address": "500 Harper Street"},
    {"email": "victorianvillageapts+550harper@gmail.com", "account": "1092148000w", "address": "550 Harper Street"},
    {"email": "victorianvillageapts+600harper@gmail.com", "account": "1092149000w", "address": "600 Harper Street"},
    {"email": "victorianvillageapts+650harper@gmail.com", "account": "1092149100w", "address": "650 Harper Street"},
    {"email": "victorianvillageapts+700harper@gmail.com", "account": "1092149500w", "address": "700 Harper Street"},
    {"email": "victorianvillageapts+750harper@gmail.com", "account": "1092149600w", "address": "750 Harper Street"},
    {"email": "victorianvillageapts+775harper@gmail.com", "account": "1092149800w", "address": "775 Harper Street"},
    {"email": "victorianvillageapts+800harper@gmail.com", "account": "1092149700w", "address": "800 Harper Street"},
    {"email": "victorianvillageapts+825harper@gmail.com", "account": "1092149900w", "address": "825 Harper Street"},
    {"email": "victorianvillageapts+850harper@gmail.com", "account": "1092155500w", "address": "850 Harper Street"},
    {"email": "victorianvillageapts+875harper@gmail.com", "account": "1092156600w", "address": "875 Harper Street"},
    {"email": "victorianvillageapts+900harper@gmail.com", "account": "1092137001w", "address": "900 Harper Street"},
]

PASSWORD = "Jolinda@27"
NAME = "Victorian Village Apartments"
REGISTER_URL = "https://mywateradvisor2.com/register/account"


async def register_account(page, email, password, account_number, address, index, total):
    """Register a single account."""
    print(f"\n[{index}/{total}] Registering: {address}")
    print(f"    Email: {email}")
    print(f"    Account: {account_number}")

    try:
        # Go directly to registration page
        await page.goto(REGISTER_URL, wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(3000)

        # STEP 1: Enter Account Number (first input field)
        print("    Step 1: Entering account number...")
        inputs = await page.query_selector_all('input[type="text"], input:not([type])')
        if inputs:
            await inputs[0].fill(account_number)
            print(f"    Filled account: {account_number}")

        await page.wait_for_timeout(500)

        # STEP 2: Enter Name (Victorian Village Apartments) - second input field
        print("    Step 2: Entering name...")
        if len(inputs) > 1:
            await inputs[1].fill(NAME)
            print(f"    Filled name: {NAME}")

        await page.wait_for_timeout(500)

        # STEP 3: Click Enter/Next button
        print("    Step 3: Clicking Enter button...")
        enter_selectors = [
            'button:has-text("Enter")',
            'button:has-text("Next")',
            'button:has-text("Continue")',
            'button:has-text("Submit")',
            'button[type="submit"]',
        ]

        for selector in enter_selectors:
            try:
                btn = await page.wait_for_selector(selector, timeout=2000)
                if btn:
                    await btn.click()
                    print(f"    Clicked: {selector}")
                    break
            except:
                continue

        await page.wait_for_timeout(5000)  # Wait for page to load after Enter

        # STEP 4: Wait for email fields to appear, then fill
        print("    Step 4: Waiting for email fields...")
        try:
            await page.wait_for_selector('input[type="email"]', timeout=10000)
        except:
            print("    Waiting longer for page...")
            await page.wait_for_timeout(3000)

        email_inputs = await page.query_selector_all('input[type="email"], input[name*="email" i], input[placeholder*="email" i]')
        for inp in email_inputs:
            await inp.fill(email)
            await page.wait_for_timeout(300)
        if email_inputs:
            print(f"    Filled {len(email_inputs)} email field(s)")

        await page.wait_for_timeout(1000)

        # STEP 5: Wait for password fields, then fill
        print("    Step 5: Entering password...")
        try:
            await page.wait_for_selector('input[type="password"]', timeout=5000)
        except:
            pass

        password_inputs = await page.query_selector_all('input[type="password"]')
        for inp in password_inputs:
            await inp.fill(password)
            await page.wait_for_timeout(300)
        if password_inputs:
            print(f"    Filled {len(password_inputs)} password field(s)")

        await page.wait_for_timeout(1000)

        # STEP 6: Click Finish and Login
        print("    Step 6: Clicking Finish and Login...")
        finish_selectors = [
            'button:has-text("Finish and Login")',
            'button:has-text("Finish")',
            'button:has-text("Complete")',
            'button:has-text("Create")',
            'button:has-text("Register")',
            'button[type="submit"]',
        ]

        for selector in finish_selectors:
            try:
                btn = await page.wait_for_selector(selector, timeout=2000)
                if btn:
                    await btn.click()
                    print(f"    Clicked: {selector}")
                    break
            except:
                continue

        await page.wait_for_timeout(4000)

        print(f"    DONE!")
        return True

    except Exception as e:
        print(f"    ERROR: {e}")
        return False


async def main():
    print("=" * 60)
    print("Victorian Village Water Meter Registration")
    print("=" * 60)
    print(f"URL: {REGISTER_URL}")
    print(f"Registering {len(ACCOUNTS)} accounts")
    print(f"Name: {NAME}")
    print(f"Password: {'*' * len(PASSWORD)}")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=800,  # Slower to let pages load
        )

        page = await browser.new_page()

        print("\nStarting registration...")
        print("Watch the browser. Help click if needed.\n")

        results = {'success': 0, 'failed': 0}

        for i, acc in enumerate(ACCOUNTS, 1):
            success = await register_account(
                page,
                acc['email'],
                PASSWORD,
                acc['account'],
                acc['address'],
                i,
                len(ACCOUNTS)
            )

            if success:
                results['success'] += 1
            else:
                results['failed'] += 1

            if i < len(ACCOUNTS):
                print("\n    Waiting 5 seconds...")
                await page.wait_for_timeout(5000)

        print("\n" + "=" * 60)
        print("REGISTRATION COMPLETE")
        print(f"Processed: {results['success']} accounts")
        print("=" * 60)

        input("\nPress Enter to close browser...")
        await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled by user")
