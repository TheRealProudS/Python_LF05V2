from flask import Flask, render_template, request, session, redirect, url_for, Response
from markupsafe import Markup
from datetime import datetime, timedelta
from bank import Bank
import html
import re
import json
import secrets
import io
import csv
import os
import atexit
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    APSCHEDULER_AVAILABLE = True
except Exception:
    APSCHEDULER_AVAILABLE = False

try:
    from flask_wtf import FlaskForm
    from wtforms import StringField, PasswordField, DecimalField, IntegerField
    from wtforms.validators import DataRequired, NumberRange, Length
    WTFormsAvailable = True
except ImportError:
    WTFormsAvailable = False

    class Field:
        def __init__(self, name, data=''):
            self.name = name
            self.data = data or ''
            self.errors = []

        def __call__(self, **kwargs):
            attrs = ' '.join(f'{k}="{v}"' for k, v in kwargs.items() if v is not None)
            typ = 'text'
            if self.name == 'pin':
                typ = 'password'
            elif self.name in ('amount', 'betrag', 'rate', 'months'):
                typ = 'number'
            step = ' step="0.01"' if self.name in ('amount', 'rate', 'betrag') else ''
            value = html.escape(str(self.data)) if self.data is not None else ''
            return Markup(f'<input type="{typ}" name="{self.name}" value="{value}"{step} {attrs}>')

        def __iter__(self):
            return iter(self.errors)

        def __len__(self):
            return len(self.errors)

        def __getitem__(self, idx):
            return self.errors[idx]

    class StringField(Field):
        pass

    class PasswordField(Field):
        pass

    class DecimalField(Field):
        pass

    class IntegerField(Field):
        pass

    class FlaskForm:
        def hidden_tag(self):
            return Markup('')


app = Flask(__name__, template_folder='pages')
# TODO: in production set secret from environment variable
app.secret_key = 'geheimnis123'
app.permanent_session_lifetime = timedelta(hours=1)
# session cookie security
app.config['SESSION_COOKIE_HTTPONLY'] = True
# app.config['SESSION_COOKIE_SECURE'] = True  # enable when using HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

bank = Bank('data.json')


if WTFormsAvailable:
    class LoginForm(FlaskForm):
        kontonummer = StringField('Kontonummer', validators=[DataRequired(message='Kontonummer erforderlich'), Length(min=3, max=20)])
        pin = PasswordField('PIN', validators=[DataRequired(message='PIN erforderlich'), Length(min=4, max=12)])
        class Meta:
            csrf = False

    class KreditForm(FlaskForm):
        amount = DecimalField('Kreditbetrag', places=2, validators=[DataRequired(message='Kreditbetrag erforderlich'), NumberRange(min=100, max=1000000, message='Betrag muss zwischen 100 und 1.000.000 liegen')])
        months = IntegerField('Laufzeit', default=12, validators=[DataRequired(message='Laufzeit erforderlich'), NumberRange(min=1, max=180, message='Laufzeit muss zwischen 1 und 180 Monaten liegen')])
        rate = DecimalField('Effektiver Jahreszins', places=2, default=5.0, validators=[DataRequired(message='Zinssatz erforderlich'), NumberRange(min=0, max=25, message='Zinssatz muss zwischen 0 und 25 liegen')])
        class Meta:
            csrf = False

    class TransactionForm(FlaskForm):
        amount = DecimalField('Betrag', places=2, validators=[DataRequired(message='Betrag erforderlich'), NumberRange(min=0.01, max=1000000, message='Betrag muss größer als 0 sein')])
        class Meta:
            csrf = False

    class TransferForm(FlaskForm):
        ziel_kontonummer = StringField('Zielkontonummer', validators=[DataRequired(message='Zielkontonummer erforderlich'), Length(min=3, max=20)])
        betrag = DecimalField('Betrag', places=2, validators=[DataRequired(message='Betrag erforderlich'), NumberRange(min=0.01, max=1000000, message='Betrag muss größer als 0 sein')])
        class Meta:
            csrf = False
else:
    class LoginForm:
        def __init__(self, formdata=None):
            formdata = formdata if formdata is not None else request.form
            self.kontonummer = StringField('kontonummer', formdata.get('kontonummer', ''))
            self.pin = PasswordField('pin', formdata.get('pin', ''))

        def hidden_tag(self):
            return Markup('')

        def validate_on_submit(self):
            if request.method != 'POST':
                return False
            valid = True
            self.kontonummer.errors = []
            self.pin.errors = []
            if not self.kontonummer.data.strip():
                self.kontonummer.errors.append('Kontonummer erforderlich')
                valid = False
            if not self.pin.data.strip():
                self.pin.errors.append('PIN erforderlich')
                valid = False
            return valid

    class KreditForm:
        def __init__(self, formdata=None):
            formdata = formdata if formdata is not None else request.form
            self.amount = DecimalField('amount', formdata.get('amount', ''))
            self.months = IntegerField('months', formdata.get('months', '12'))
            self.rate = DecimalField('rate', formdata.get('rate', '5.0'))

        def hidden_tag(self):
            return Markup('')

        def validate_on_submit(self):
            if request.method != 'POST':
                return False
            valid = True
            self.amount.errors = []
            self.months.errors = []
            self.rate.errors = []
            try:
                amount = float(self.amount.data)
                if amount < 100 or amount > 1000000:
                    raise ValueError
            except Exception:
                self.amount.errors.append('Kreditbetrag muss zwischen 100 und 1.000.000 liegen')
                valid = False
            try:
                months = int(self.months.data)
                if months < 1 or months > 180:
                    raise ValueError
            except Exception:
                self.months.errors.append('Laufzeit muss zwischen 1 und 180 Monaten liegen')
                valid = False
            try:
                rate = float(self.rate.data)
                if rate < 0 or rate > 25:
                    raise ValueError
            except Exception:
                self.rate.errors.append('Zinssatz muss zwischen 0 und 25 liegen')
                valid = False
            return valid

    class TransactionForm:
        def __init__(self, formdata=None):
            formdata = formdata if formdata is not None else request.form
            self.amount = DecimalField('amount', formdata.get('amount', ''))

        def hidden_tag(self):
            return Markup('')

        def validate_on_submit(self):
            if request.method != 'POST':
                return False
            valid = True
            self.amount.errors = []
            try:
                amount = float(self.amount.data)
                if amount < 0.01 or amount > 1000000:
                    raise ValueError
            except Exception:
                self.amount.errors.append('Betrag muss größer als 0 sein')
                valid = False
            return valid

    class TransferForm:
        def __init__(self, formdata=None):
            formdata = formdata if formdata is not None else request.form
            self.ziel_kontonummer = StringField('ziel_kontonummer', formdata.get('ziel_kontonummer', ''))
            self.betrag = DecimalField('betrag', formdata.get('betrag', ''))

        def hidden_tag(self):
            return Markup('')

        def validate_on_submit(self):
            if request.method != 'POST':
                return False
            valid = True
            self.ziel_kontonummer.errors = []
            self.betrag.errors = []
            if not self.ziel_kontonummer.data.strip():
                self.ziel_kontonummer.errors.append('Zielkontonummer erforderlich')
                valid = False
            try:
                amount = float(self.betrag.data)
                if amount < 0.01 or amount > 1000000:
                    raise ValueError
            except Exception:
                self.betrag.errors.append('Betrag muss größer als 0 sein')
                valid = False
            return valid


def parse_transactions(konto):
    parsed = []
    for t in konto.transaktionen:
        m = re.match(r"\[(.*?)\]\s*(.*):\s*([+-]?[0-9,.]+)€", t)
        if m:
            dt_s, desc, amt = m.groups()
            try:
                amt_f = float(amt.replace(',', '.'))
            except:
                amt_f = 0.0
            parsed.append({'datetime': dt_s, 'desc': desc, 'amount': amt_f})
        else:
            parsed.append({'datetime': '', 'desc': t, 'amount': 0.0})

    balances = []
    bal = 0.0
    for p in parsed:
        bal += p['amount']
        balances.append(bal)
    total = balances[-1] if balances else 0.0
    # offset so that the last computed balance matches konto.saldo
    offset = (konto.saldo if hasattr(konto, 'saldo') else 0.0) - total
    for i, p in enumerate(parsed):
        p['balance'] = balances[i] + offset
    return parsed


# calc function
def calc_monthly_payment(principal, annual_rate_percent, months):
    if months <= 0:
        return 0.0
    if annual_rate_percent <= 0:
        return principal / months
    r = annual_rate_percent / 100.0 / 12.0
    return principal * r / (1 - (1 + r) ** -months)

@app.context_processor
def inject_user():
    name = session.get('name')
    kontonr = session.get('kontonummer')
    masked = None
    if kontonr and len(str(kontonr)) > 4:
        s = str(kontonr)
        masked = '•••' + s[-4:]
    elif kontonr:
        masked = kontonr
    return dict(name=name, csrf_token=session.get('csrf_token'), masked_kontonummer=masked)


@app.before_request
def check_csrf():
    # Only enforce for POST requests and when logged in
    if request.method == 'POST' and request.endpoint not in ('login', None):
        token = session.get('csrf_token')
        form_token = request.form.get('csrf_token')
        if not token or not form_token or token != form_token:
            return "Ungültiges Formular (CSRF).", 400


# Login & Logout
@app.route('/')
def index():
    if 'kontonummer' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    error = None
    if form.validate_on_submit():
        kontonummer = form.kontonummer.data.strip()
        pin = form.pin.data.strip()

        konto = bank.authentifizieren(kontonummer, pin)
        if konto:
            session.permanent = True
            session['kontonummer'] = kontonummer
            session['name'] = konto.name
            session['csrf_token'] = secrets.token_hex(16)
            return redirect(url_for('dashboard'))
        error = 'Kontonummer oder PIN falsch!'
    elif request.method == 'POST':
        error = 'Bitte überprüfen Sie die Eingaben.'

    return render_template('login.html', form=form, error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'kontonummer' not in session:
        return redirect(url_for('login'))

    konto = bank.finde_konto(session['kontonummer'])
    if not konto:
        session.clear()
        return redirect(url_for('login'))

    # process any due sparplaene before showing dashboard
    try:
        bank.process_sparplaene()
    except Exception:
        pass

    parsed = parse_transactions(konto)
    last = parsed[-10:]
    labels = [p['datetime'] for p in last]
    amounts = [p['amount'] for p in last]
    balances = [p['balance'] for p in last]
    last_activity = last[-1]['datetime'] if last else 'Keine Aktivitäten'
    last_5 = parsed[-5:][::-1] if parsed else []

    return render_template('dashboard.html',
                           kontonummer=konto.kontonummer,
                           name=konto.name,
                           saldo=f"{konto.saldo:.2f}",
                           savings=f"{getattr(konto,'savings',0.0):.2f}",
                           chart_labels=json.dumps(labels),
                           chart_amounts=json.dumps(amounts),
                           chart_balances=json.dumps(balances),
                           last_activity=last_activity,
                           last_transaktionen=last_5)


# Einzahlung
@app.route('/einzahlung', methods=['GET', 'POST'])
def einzahlung():
    if 'kontonummer' not in session:
        return redirect(url_for('login'))

    form = TransactionForm()
    error = None
    success = None
    konto = bank.finde_konto(session['kontonummer'])

    if request.method == 'POST':
        if form.validate_on_submit():
            amount = float(form.amount.data)
            if bank.einzahlen(session['kontonummer'], amount):
                success = f'Einzahlung von {amount:.2f}€ erfolgreich!'
                konto = bank.finde_konto(session['kontonummer'])
            else:
                error = 'Einzahlung fehlgeschlagen!'
        else:
            error = 'Bitte überprüfen Sie die Eingaben.'

    return render_template('einzahlung.html',
                           name=konto.name,
                           saldo=f"{konto.saldo:.2f}",
                           form=form,
                           error=error,
                           success=success)


# Auszahlung
@app.route('/auszahlung', methods=['GET', 'POST'])
def auszahlung():
    if 'kontonummer' not in session:
        return redirect(url_for('login'))

    form = TransactionForm()
    error = None
    success = None
    konto = bank.finde_konto(session['kontonummer'])

    if request.method == 'POST':
        if form.validate_on_submit():
            amount = float(form.amount.data)
            if bank.auszahlen(session['kontonummer'], amount):
                success = f'Auszahlung von {amount:.2f}€ erfolgreich!'
                konto = bank.finde_konto(session['kontonummer'])
            else:
                error = 'Nicht genug Guthaben oder ungültiger Betrag!'
        else:
            error = 'Bitte überprüfen Sie die Eingaben.'

    return render_template('auszahlung.html',
                           name=konto.name,
                           saldo=f"{konto.saldo:.2f}",
                           form=form,
                           error=error,
                           success=success)


# Überweisung
@app.route('/ueberweisung', methods=['GET', 'POST'])
def ueberweisung():
    if 'kontonummer' not in session:
        return redirect(url_for('login'))

    form = TransferForm()
    error = None
    success = None
    konto = bank.finde_konto(session['kontonummer'])

    if request.method == 'POST':
        if form.validate_on_submit():
            ziel_kontonummer = form.ziel_kontonummer.data.strip()
            betrag = float(form.betrag.data)

            if session['kontonummer'] == ziel_kontonummer:
                error = 'Kann nicht auf gleiches Konto überweisen!'
            elif not bank.finde_konto(ziel_kontonummer):
                error = 'Zielkonto nicht gefunden!'
            elif bank.ueberweisen(session['kontonummer'], ziel_kontonummer, betrag):
                ziel = bank.finde_konto(ziel_kontonummer)
                success = f'Überweisung von {betrag:.2f}€ an {ziel.name} erfolgreich!'
                konto = bank.finde_konto(session['kontonummer'])
            else:
                error = 'Überweisung fehlgeschlagen (nicht genug Guthaben?)!'
        else:
            error = 'Bitte überprüfen Sie die Eingaben.'

    return render_template('ueberweisung.html',
                           name=konto.name,
                           saldo=f"{konto.saldo:.2f}",
                           form=form,
                           error=error,
                           success=success)


# Transaktionen
@app.route('/transaktionen')
def transaktionen():
    if 'kontonummer' not in session:
        return redirect(url_for('login'))

    konto = bank.finde_konto(session['kontonummer'])
    parsed = parse_transactions(konto)

    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    betrag_min = request.args.get('betrag_min', '').strip()
    betrag_max = request.args.get('betrag_max', '').strip()
    search = request.args.get('search', '').strip().lower()

    def parse_date(value):
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except Exception:
            return None

    def parse_float(value):
        try:
            return float(value)
        except Exception:
            return None

    df = parse_date(date_from)
    dt = parse_date(date_to)
    min_amt = parse_float(betrag_min)
    max_amt = parse_float(betrag_max)

    # If any filter parameter is present, open the filter panel by default
    filter_open = bool(date_from or date_to or betrag_min or betrag_max or search)

    def matches(tx):
        try:
            ts = tx.get('datetime', '').split('.')[0]
            tx_date = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').date()
        except Exception:
            return False

        if df and tx_date < df:
            return False
        if dt and tx_date > dt:
            return False
        if min_amt is not None and tx['amount'] < min_amt:
            return False
        if max_amt is not None and tx['amount'] > max_amt:
            return False
        if search:
            term = search
            if term not in tx['desc'].lower() and term not in tx.get('datetime','').lower() and term not in f"{tx['amount']:.2f}":
                return False
        return True

    filtered = [tx for tx in parsed if matches(tx)]

    labels = [p['datetime'] for p in filtered]
    amounts = [p['amount'] for p in filtered]
    balances = [p.get('balance', 0.0) for p in filtered]

    return render_template('transaktionen.html',
                           name=konto.name,
                           saldo=f"{konto.saldo:.2f}",
                           transaktionen=filtered,
                           chart_labels=json.dumps(labels),
                           chart_amounts=json.dumps(amounts),
                           chart_balances=json.dumps(balances),
                           filter_open=filter_open,
                           date_from=date_from,
                           date_to=date_to,
                           betrag_min=betrag_min,
                           betrag_max=betrag_max,
                           search=search)
                            
# Export transactions as CSV
@app.route('/export_csv')
def export_csv():
    if 'kontonummer' not in session:
        return redirect(url_for('login'))

    konto = bank.finde_konto(session['kontonummer'])
    parsed = parse_transactions(konto)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Datum/Zeit', 'Beschreibung', 'Betrag', 'Kontostand'])
    for p in parsed:
        writer.writerow([p['datetime'], p['desc'], f"{p['amount']:.2f}", f"{p.get('balance',0.0):.2f}"])

    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=transaktionen.csv'
        }
    )
    
@app.route('/kredit', methods=['GET', 'POST'])
def kredit():
    if 'kontonummer' not in session:
        return redirect(url_for('login'))
    konto = bank.finde_konto(session['kontonummer'])
    form = KreditForm()
    error = None
    result = None

    if request.method == 'POST':
        if form.validate_on_submit():
            amount = float(form.amount.data)
            months = int(form.months.data)
            rate = float(form.rate.data)
            monthly = calc_monthly_payment(amount, rate, months)
            app_entry = {
                'id': secrets.token_hex(8),
                'amount': amount,
                'months': months,
                'rate': rate,
                'monthly': round(monthly, 2),
                'status': 'offen',
                'applied_at': datetime.now().isoformat()
            }
            konto.kredite.append(app_entry)
            bank.save_data()
            result = app_entry
        else:
            error = 'Bitte überprüfen Sie die Eingaben im Kreditformular.'

    return render_template('kredit.html', name=konto.name, saldo=f"{konto.saldo:.2f}", form=form, error=error, result=result)
        
        
@app.route('/admin/kredite')
def admin_kredite():
    if 'kontonummer' not in session:
        return redirect(url_for('login'))
    # simple admin check example: kontonummer == '9999' oder erweitern
    if session.get('kontonummer') != '9999':
        return "Zugriff verweigert", 403
    alle = []
    for k in bank.alle_konten():
        for c in getattr(k, 'kredite', []):
            alle.append({'konto': k.kontonummer, 'name': k.name, **c})
    return render_template('admin_kredite.html', kredite=alle)


@app.route('/sparplan', methods=['GET', 'POST'])
def sparplan():
    if 'kontonummer' not in session:
        return redirect(url_for('login'))
    konto = bank.finde_konto(session['kontonummer'])
    error = None
    success = None

    if request.method == 'POST':
        # create new sparplan
        name = request.form.get('name', '').strip() or 'Sparplan'
        amount = request.form.get('amount', '').strip()
        frequency = request.form.get('frequency', 'monthly')
        target = request.form.get('target', '').strip()

        try:
            amount_f = float(amount)
            if amount_f <= 0:
                raise ValueError
        except Exception:
            error = 'Bitte gültigen Betrag angeben.'
            amount_f = None

        if not error:
            plan = bank.add_sparplan(session['kontonummer'], amount_f, frequency, target if target else None, None, name)
            if plan:
                success = 'Sparplan erstellt.'
            else:
                error = 'Sparplan konnte nicht erstellt werden.'

    # refresh account (may have changed due to processing elsewhere)
    konto = bank.finde_konto(session['kontonummer'])
    sparplaene = getattr(konto, 'sparplaene', [])
    # process any due plans for immediate effect
    try:
        bank.process_sparplaene()
    except Exception:
        pass

    return render_template('sparplan.html', name=konto.name, saldo=f"{konto.saldo:.2f}", sparplaene=sparplaene, error=error, success=success)


@app.route('/sparplan/cancel/<plan_id>', methods=['POST'])
def sparplan_cancel(plan_id):
    if 'kontonummer' not in session:
        return redirect(url_for('login'))
    ok = bank.remove_sparplan(session['kontonummer'], plan_id)
    return redirect(url_for('sparplan'))

@app.route('/admin/kredit/<kto>/<app_id>/<action>', methods=['POST'])
def admin_kredit_decide(kto, app_id, action):
    if session.get('kontonummer') != '9999':
        return "Zugriff verweigert", 403
    konto = bank.finde_konto(kto)
    if not konto:
        return "Konto nicht gefunden", 404
    for a in konto.kredite:
        if a.get('id') == app_id and a.get('status') == 'offen':
            if action == 'accept':
                a['status'] = 'akzeptiert'
                a['decision_at'] = datetime.now().isoformat()
                konto.saldo += a['amount']
                zeit = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                konto.transaktionen.append(f"[{zeit}] Kredit Auszahlung: +{a['amount']:.2f}€")
                bank.save_data()
            elif action == 'reject':
                a['status'] = 'abgelehnt'
                a['decision_at'] = datetime.now().isoformat()
                bank.save_data()
            break
    return redirect(url_for('admin_kredite'))
            
            
if __name__ == '__main__':
    # start background scheduler for sparplaene if available
    start_scheduler = APSCHEDULER_AVAILABLE and (not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true')
    if start_scheduler:
        scheduler = BackgroundScheduler()
        # run process_sparplaene every minute
        scheduler.add_job(func=lambda: bank.process_sparplaene(), trigger='interval', minutes=1, id='sparplan_job', replace_existing=True)
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown(wait=False))
        print('APScheduler started: sparplan job running every minute')
    else:
        if not APSCHEDULER_AVAILABLE:
            print('APScheduler not available; sparplan scheduler disabled')

    app.run(debug=True, host='127.0.0.1', port=5000)
