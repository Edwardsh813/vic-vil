"""
Water Meter Scraper for mywateradvisor2.com
"""

import asyncio
from datetime import datetime, date
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser
import database as db
import config
import re
import notifications

class WaterMeterScraper:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.playwright = None

    async def start(self):
        """Start the browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )

    async def stop(self):
        """Close the browser."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def login(self, page: Page, email: str, password: str) -> bool:
        """Log into mywateradvisor2.com"""
        try:
            # Go directly to login page
            await page.goto("https://mywateradvisor2.com/login", wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)

            # Find and fill email field
            email_input = await page.wait_for_selector('input[type="email"], input[name*="email" i], input[placeholder*="email" i]', timeout=10000)
            if email_input:
                await email_input.fill(email)

            await page.wait_for_timeout(500)

            # Find and fill password field
            password_input = await page.wait_for_selector('input[type="password"]', timeout=5000)
            if password_input:
                await password_input.fill(password)

            await page.wait_for_timeout(500)

            # Click login button
            login_selectors = [
                'button:has-text("Login")',
                'button:has-text("Sign In")',
                'button:has-text("Log In")',
                'button[type="submit"]',
                'input[type="submit"]',
            ]

            for selector in login_selectors:
                try:
                    btn = await page.wait_for_selector(selector, timeout=2000)
                    if btn:
                        await btn.click()
                        break
                except:
                    continue

            # Wait for login to complete
            await page.wait_for_timeout(5000)

            # Check if logged in (look for dashboard elements or logout button)
            page_text = await page.inner_text('body')
            if 'dashboard' in page_text.lower() or 'usage' in page_text.lower() or 'logout' in page_text.lower() or 'gallons' in page_text.lower():
                return True

            return True  # Assume success if no error

        except Exception as e:
            db.log_scrape(None, 'error', f'Login error: {str(e)}')
            return False

    async def scrape_usage_data(self, page: Page, account_id: int) -> dict:
        """Scrape usage data from the dashboard."""
        result = {
            'hourly_data': [],
            'daily_total': None,       # Will store daily average
            'monthly_total': None,     # Current billing cycle total
            'monthly_forecast': None,  # End of cycle forecast
            'monthly_avg_12mo': None,  # 12-month average
            'daily_min': None,
            'daily_max': None,
            'daily_avg': None,
            'current_reading': None,
            'leak_detected': False,
            'leak_message': None
        }

        try:
            await page.wait_for_timeout(3000)

            # Get all text from page
            page_text = await page.inner_text('body')

            # Extract "Current Billing Cycle" usage (monthly total)
            current_match = re.search(r'Current Billing Cycle\s*([\d,]+)\s*gal', page_text, re.IGNORECASE)
            if current_match:
                result['monthly_total'] = float(current_match.group(1).replace(',', ''))

            # Extract forecast
            forecast_match = re.search(r'Forecast\s*([\d,]+)\s*gal', page_text, re.IGNORECASE)
            if forecast_match:
                result['monthly_forecast'] = float(forecast_match.group(1).replace(',', ''))

            # Click "Daily" tab to get daily stats
            daily_btn = await page.query_selector('text=Daily')
            if daily_btn:
                await daily_btn.click()
                await page.wait_for_timeout(2000)
                page_text = await page.inner_text('body')

            # Extract daily stats (Average is most useful for daily usage)
            avg_match = re.search(r'Average\s*([\d,]+)', page_text)
            if avg_match:
                result['daily_avg'] = float(avg_match.group(1).replace(',', ''))
                result['daily_total'] = result['daily_avg']  # Use average as daily usage

            min_match = re.search(r'Minimum\s*([\d,]+)', page_text)
            if min_match:
                result['daily_min'] = float(min_match.group(1).replace(',', ''))

            max_match = re.search(r'Maximum\s*([\d,]+)', page_text)
            if max_match:
                result['daily_max'] = float(max_match.group(1).replace(',', ''))

            # Try to find hourly data in tables
            tables = await page.query_selector_all('table')
            for table in tables:
                rows = await table.query_selector_all('tr')
                for row in rows:
                    cells = await row.query_selector_all('td')
                    if len(cells) >= 2:
                        try:
                            cell_texts = [await c.inner_text() for c in cells]
                            # Look for hour:value pairs
                            for i, text in enumerate(cell_texts[:-1]):
                                hour_match = re.match(r'^(\d{1,2})(?::00)?$', text.strip())
                                if hour_match:
                                    hour = int(hour_match.group(1))
                                    value_text = cell_texts[i+1]
                                    value_match = re.search(r'([\d.]+)', value_text)
                                    if value_match:
                                        result['hourly_data'].append({
                                            'hour': hour,
                                            'usage': float(value_match.group(1))
                                        })
                        except:
                            continue

            # Click "Billing Month" tab to get 12-month average
            billing_month_btn = await page.query_selector('text=Billing Month')
            if not billing_month_btn:
                billing_month_btn = await page.query_selector('text="Billing Month"')
            if billing_month_btn:
                await billing_month_btn.click()
                await page.wait_for_timeout(2000)
                page_text = await page.inner_text('body')

                # Look for 12-month average (the Average stat at bottom of chart)
                avg_12mo_match = re.search(r'Average\s*[-]?([\d,]+)', page_text)
                if avg_12mo_match:
                    result['monthly_avg_12mo'] = float(avg_12mo_match.group(1).replace(',', ''))
                    print(f"    Found 12-month avg: {result['monthly_avg_12mo']}")

            # LEAK DETECTION - look for red elements or leak text
            page_text = await page.inner_text('body')
            if 'leak' in page_text.lower():
                result['leak_detected'] = True
                # Try to get leak message
                leak_match = re.search(r'(leak[^.]*\.)', page_text, re.IGNORECASE)
                if leak_match:
                    result['leak_message'] = leak_match.group(1)
                else:
                    result['leak_message'] = 'Leak detected on meter'

            # Also check for red colored elements (potential leak indicators)
            red_elements = await page.query_selector_all('[style*="red"], [class*="red"], [class*="alert"], [class*="warning"], [class*="danger"]')
            for el in red_elements:
                el_text = await el.inner_text()
                if el_text.strip():
                    result['leak_detected'] = True
                    result['leak_message'] = el_text.strip()[:200]
                    break

            # Take screenshot for debugging
            await page.screenshot(path=f'/home/hunter/projects/vic-vil/water-monitor/screenshots/account_{account_id}.png')

        except Exception as e:
            db.log_scrape(account_id, 'error', f'Scrape error: {str(e)}')

        return result

    async def scrape_account(self, account: dict) -> bool:
        """Scrape data for a single account."""
        page = await self.browser.new_page()

        try:
            # Decrypt password
            password = db.decrypt_password(account['password_encrypted'])

            # Login
            logged_in = await self.login(page, account['email'], password)

            if not logged_in:
                db.log_scrape(account['id'], 'error', 'Login failed')
                return False

            # Scrape usage data
            data = await self.scrape_usage_data(page, account['id'])

            # Save data to database
            today = date.today()
            current_hour = datetime.now().hour

            if data['hourly_data']:
                for hour_data in data['hourly_data']:
                    db.save_hourly_reading(
                        account['id'],
                        today,
                        hour_data['hour'],
                        hour_data['usage']
                    )

            if data['daily_total']:
                db.save_daily_summary(account['id'], today, data['daily_total'])

            # Handle leak detection (if enabled for this meter)
            if data['leak_detected']:
                db.log_scrape(account['id'], 'leak', data['leak_message'])
                print(f"    LEAK DETECTED: {data['leak_message']}")
                if account.get('leak_alerts', 1) == 1:
                    monthly = data['monthly_total'] or 0
                    avg = data['monthly_avg_12mo'] or 0
                    leak_msg = f"{data['leak_message']}\nThis month: {monthly:,.0f} gal\n12-mo avg: {avg:,.0f} gal"
                    notifications.send_leak_alert(
                        account.get('address', account['unit_number']),
                        leak_msg
                    )
                else:
                    print(f"    (Leak alerts disabled for this meter)")

            # Update last scraped time, monthly usage, and 12-month average
            update_data = {'last_scraped': datetime.now().isoformat()}
            if data['monthly_total']:
                update_data['monthly_usage'] = data['monthly_total']
            if data['monthly_avg_12mo']:
                update_data['avg_12mo'] = data['monthly_avg_12mo']
            db.update_account(account['id'], **update_data)

            # Check for projected overage (10%, 20%, 30%, 40% over 12-month average)
            if data['monthly_total'] and data['monthly_avg_12mo']:
                import calendar
                day_of_month = datetime.now().day

                # No alerts for first 5 days of month
                if day_of_month > 5:
                    avg_12mo = data['monthly_avg_12mo']
                    days_in_month = calendar.monthrange(datetime.now().year, datetime.now().month)[1]
                    current_month = datetime.now().strftime('%Y-%m')

                    # Calculate projected usage
                    projected_usage = (data['monthly_total'] / day_of_month) * days_in_month
                    overage_pct = ((projected_usage - avg_12mo) / avg_12mo) * 100

                    # Check which thresholds have been alerted this month
                    with db.get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            SELECT message FROM scrape_logs
                            WHERE account_id = ? AND status = 'overage_alert'
                            AND strftime('%Y-%m', created_at) = ?
                        ''', (account['id'], current_month))
                        existing_alerts = [row[0] for row in cursor.fetchall()]

                    # Determine which threshold levels have been triggered
                    # Use meter's min_overage_pct setting (default 10%)
                    min_threshold = account.get('min_overage_pct', 10) or 10
                    thresholds = [t for t in [10, 20, 30, 40] if t >= min_threshold]
                    for threshold in thresholds:
                        threshold_tag = f"[{threshold}%]"
                        already_alerted = any(threshold_tag in msg for msg in existing_alerts)

                        if not already_alerted and overage_pct >= threshold:
                            overage_threshold = avg_12mo * (1 + threshold/100)
                            expected_at_this_point = overage_threshold * (day_of_month / days_in_month)

                            if data['monthly_total'] > expected_at_this_point:
                                alert_msg = f"[{threshold}%] At {data['monthly_total']:.0f} gal (day {day_of_month}), projected {projected_usage:.0f} gal ({overage_pct:.0f}% over {avg_12mo:.0f} avg)"
                                db.log_scrape(account['id'], 'overage_alert', alert_msg)
                                print(f"    OVERAGE ALERT: {alert_msg}")
                                notifications.send_overage_alert(
                                    account.get('address', account['unit_number']),
                                    alert_msg
                                )
                                break  # Only send one alert per scrape

            db.log_scrape(account['id'], 'success', f'Daily: {data["daily_total"]}, Monthly: {data["monthly_total"]}, 12mo avg: {data["monthly_avg_12mo"]}, Leak: {data["leak_detected"]}')

            return True

        except Exception as e:
            db.log_scrape(account['id'], 'error', str(e))
            return False

        finally:
            await page.close()

    async def scrape_all_accounts(self):
        """Scrape data for all active accounts."""
        await self.start()

        accounts = db.get_all_accounts()
        results = {'success': 0, 'failed': 0}

        for account in accounts:
            print(f"Scraping: {account['building_name']} - {account['unit_number']}")
            success = await self.scrape_account(account)
            if success:
                results['success'] += 1
                print(f"  Success")
            else:
                results['failed'] += 1
                print(f"  Failed")

            # Small delay between accounts
            await asyncio.sleep(2)

        await self.stop()
        return results


def run_scrape():
    """Synchronous wrapper for scraping all accounts."""
    scraper = WaterMeterScraper()
    return asyncio.run(scraper.scrape_all_accounts())


if __name__ == "__main__":
    import os
    os.makedirs('/home/hunter/projects/vic-vil/water-monitor/screenshots', exist_ok=True)
    results = run_scrape()
    print(f"\nScrape complete: {results['success']} successful, {results['failed']} failed")
