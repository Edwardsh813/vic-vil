"""
Flask Web Dashboard for Water Monitor
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, date, timedelta
import database as db
import alerts
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


@app.route('/')
def dashboard():
    """Main dashboard showing all meters with daily and monthly usage."""
    today = date.today()
    accounts = db.get_all_accounts()

    # Get today's summaries (contains current month data)
    summaries = {s['account_id']: s for s in db.get_all_daily_summaries(today)}

    # Nelsonville water rates (effective Jan 1, 2025)
    BASE_RATE = 47.54  # Water ($26.23) + Sewer ($21.31) per 1500 gal minimum
    OVERAGE_RATE = 30.33  # Per 1000 gallons over minimum
    MIN_GALLONS_PER_UNIT = 1500
    STORM_SEWAGE_FEE = 3.00  # Flat fee per meter

    # Combine account info with usage data
    meters = []
    total_monthly = 0
    total_daily_avg = 0
    total_units = 0
    total_estimated_bill = 0

    for account in accounts:
        # Get monthly usage from account (scraped from Current Billing Cycle)
        monthly_usage = account.get('monthly_usage') or 0
        total_monthly += monthly_usage

        # Get unit count for this building
        unit_count = account.get('unit_count') or 1
        total_units += unit_count

        # Calculate estimated cost
        included_gallons = MIN_GALLONS_PER_UNIT * unit_count
        base_cost = BASE_RATE * unit_count
        if monthly_usage > included_gallons:
            overage_gallons = monthly_usage - included_gallons
            overage_cost = (overage_gallons / 1000) * OVERAGE_RATE
        else:
            overage_cost = 0
        estimated_cost = base_cost + overage_cost + STORM_SEWAGE_FEE
        total_estimated_bill += estimated_cost

        # Get 12-month average from scraped data or use default
        avg_12mo = account.get('avg_12mo') or 3000  # Default until scraped

        # Calculate daily average (monthly / days in month so far)
        days_in_month = today.day
        daily_avg = monthly_usage / days_in_month if days_in_month > 0 else 0
        total_daily_avg += daily_avg

        meters.append({
            'id': account['id'],
            'building': account['building_name'],
            'unit': account['unit_number'],
            'address': account.get('address', ''),
            'email': account['email'],
            'monthly_usage': monthly_usage,
            'daily_avg': daily_avg,
            'avg_12mo': avg_12mo,
            'last_scraped': account['last_scraped'],
            'leak_detected': False,  # Will be set from leak_alerts
            'unit_count': unit_count,
            'included_gallons': included_gallons,
            'estimated_cost': estimated_cost
        })

    # Group by building
    buildings = {}
    for meter in meters:
        building = meter['building'] or 'Unknown'
        if building not in buildings:
            buildings[building] = []
        buildings[building].append(meter)

    # Get recent alerts (including leaks)
    recent_alerts = db.get_recent_alerts(10)

    # Check for leaks in scrape logs
    with db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT sl.*, a.building_name, a.unit_number, a.address
            FROM scrape_logs sl
            JOIN accounts a ON sl.account_id = a.id
            WHERE sl.status = 'leak'
            ORDER BY sl.created_at DESC LIMIT 10
        ''')
        leak_alerts = [dict(row) for row in cursor.fetchall()]

        # Check for overage alerts (most recent per account)
        cursor.execute('''
            SELECT sl.*, a.building_name, a.unit_number, a.address
            FROM scrape_logs sl
            JOIN accounts a ON sl.account_id = a.id
            WHERE sl.status = 'overage_alert'
            AND sl.id IN (
                SELECT MAX(id) FROM scrape_logs
                WHERE status = 'overage_alert'
                GROUP BY account_id
            )
            ORDER BY sl.created_at DESC
        ''')
        overage_alerts = [dict(row) for row in cursor.fetchall()]

    # Mark meters with leak detection
    leak_account_ids = {leak['account_id'] for leak in leak_alerts}
    overage_account_ids = {oa['account_id'] for oa in overage_alerts}
    for building_meters in buildings.values():
        for meter in building_meters:
            if meter['id'] in leak_account_ids:
                meter['leak_detected'] = True
            if meter['id'] in overage_account_ids:
                meter['overage_alert'] = True

    return render_template('dashboard.html',
                           buildings=buildings,
                           total_monthly=total_monthly,
                           total_daily_avg=total_daily_avg,
                           total_units=total_units,
                           total_estimated_bill=total_estimated_bill,
                           meter_count=len(meters),
                           today=today,
                           alerts=recent_alerts,
                           leak_alerts=leak_alerts,
                           overage_alerts=overage_alerts)


@app.route('/accounts')
def accounts_list():
    """List all accounts."""
    accounts = db.get_all_accounts()
    return render_template('accounts.html', accounts=accounts)


@app.route('/accounts/add', methods=['GET', 'POST'])
def add_account():
    """Add a new account."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        building = request.form.get('building_name')
        unit = request.form.get('unit_number')

        if not email or not password:
            flash('Email and password are required', 'error')
            return redirect(url_for('add_account'))

        try:
            db.add_account(email, password, building, unit)
            flash('Account added successfully', 'success')
            return redirect(url_for('accounts_list'))
        except Exception as e:
            flash(f'Error adding account: {str(e)}', 'error')

    return render_template('account_form.html', account=None)


@app.route('/accounts/<int:account_id>/edit', methods=['GET', 'POST'])
def edit_account(account_id):
    """Edit an existing account."""
    account = db.get_account(account_id)
    if not account:
        flash('Account not found', 'error')
        return redirect(url_for('accounts_list'))

    if request.method == 'POST':
        updates = {
            'email': request.form.get('email'),
            'building_name': request.form.get('building_name'),
            'unit_number': request.form.get('unit_number')
        }

        password = request.form.get('password')
        if password:
            updates['password'] = password

        try:
            db.update_account(account_id, **updates)
            flash('Account updated successfully', 'success')
            return redirect(url_for('accounts_list'))
        except Exception as e:
            flash(f'Error updating account: {str(e)}', 'error')

    return render_template('account_form.html', account=account)


@app.route('/accounts/<int:account_id>/delete', methods=['POST'])
def delete_account(account_id):
    """Delete an account."""
    db.delete_account(account_id)
    flash('Account deleted', 'success')
    return redirect(url_for('accounts_list'))


@app.route('/meter/<int:account_id>')
def meter_detail(account_id):
    """Show detailed usage for a specific meter."""
    account = db.get_account(account_id)
    if not account:
        flash('Meter not found', 'error')
        return redirect(url_for('dashboard'))

    # Get date range from query params
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    if request.args.get('start_date'):
        start_date = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d').date()
    if request.args.get('end_date'):
        end_date = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d').date()

    # Get daily summaries
    daily_data = db.get_daily_summaries(account_id, start_date, end_date)

    # Get today's hourly data
    hourly_data = db.get_hourly_readings(account_id, date.today())

    return render_template('meter_detail.html',
                           account=account,
                           daily_data=daily_data,
                           hourly_data=hourly_data,
                           start_date=start_date,
                           end_date=end_date)


@app.route('/alerts')
def alerts_list():
    """Show alert history and configuration."""
    alert_history = db.get_recent_alerts(100)
    alert_configs = db.get_alert_configs()
    accounts = db.get_all_accounts()

    return render_template('alerts.html',
                           alert_history=alert_history,
                           alert_configs=alert_configs,
                           accounts=accounts,
                           alert_types=[
                               ('high_daily_usage', 'High Daily Usage (gallons)'),
                               ('high_hourly_usage', 'High Hourly Usage (gallons)'),
                               ('no_data', 'No Data (hours)'),
                               ('leak_detection', 'Leak Detection (continuous hours)')
                           ])


@app.route('/alerts/add', methods=['POST'])
def add_alert():
    """Add a new alert configuration."""
    alert_type = request.form.get('alert_type')
    threshold = float(request.form.get('threshold', 0))
    account_id = request.form.get('account_id')

    if account_id == 'all':
        account_id = None
    else:
        account_id = int(account_id)

    try:
        db.add_alert_config(alert_type, threshold, account_id)
        flash('Alert configuration added', 'success')
    except Exception as e:
        flash(f'Error adding alert: {str(e)}', 'error')

    return redirect(url_for('alerts_list'))


@app.route('/api/leak/dismiss/<int:log_id>', methods=['POST'])
def dismiss_leak(log_id):
    """Dismiss a leak alert."""
    with db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM scrape_logs WHERE id = ? AND status = ?', (log_id, 'leak'))
        conn.commit()
    return jsonify({'status': 'success'})


@app.route('/api/overage/dismiss/<int:log_id>', methods=['POST'])
def dismiss_overage(log_id):
    """Dismiss an overage alert."""
    with db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM scrape_logs WHERE id = ? AND status = ?', (log_id, 'overage_alert'))
        conn.commit()
    return jsonify({'status': 'success'})


@app.route('/api/leak/add-alert/<int:account_id>', methods=['POST'])
def add_leak_alert(account_id):
    """Add a leak detection alert config for an account."""
    try:
        db.add_alert_config('leak_detection', 1, account_id)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/usage/<int:account_id>')
def api_usage(account_id):
    """API endpoint for usage data (for charts)."""
    days = int(request.args.get('days', 30))
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    daily_data = db.get_daily_summaries(account_id, start_date, end_date)

    return jsonify({
        'dates': [d['reading_date'] for d in daily_data],
        'usage': [d['total_usage_gallons'] or 0 for d in daily_data]
    })


@app.route('/api/hourly/<int:account_id>')
def api_hourly(account_id):
    """API endpoint for hourly data."""
    reading_date = request.args.get('date', date.today().isoformat())
    reading_date = datetime.strptime(reading_date, '%Y-%m-%d').date()

    hourly_data = db.get_hourly_readings(account_id, reading_date)

    return jsonify({
        'hours': [d['hour'] for d in hourly_data],
        'usage': [d['usage_gallons'] or 0 for d in hourly_data]
    })


@app.route('/api/scrape', methods=['POST'])
def trigger_scrape():
    """Manually trigger a scrape."""
    from scraper import run_scrape
    try:
        results = run_scrape()
        return jsonify({'status': 'success', 'results': results})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    db.init_db()
    app.run(host='0.0.0.0', port=5000, debug=config.DEBUG)
