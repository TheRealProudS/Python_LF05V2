from flask import Flask, render_template, request, session, redirect, url_for, Response
from bank import Bank
from datetime import timedelta
import re
import json
import secrets
import io
import csv

app = Flask(__name__, template_folder='pages')
# TODO: in production set secret from environment variable
app.secret_key = 'geheimnis123'
app.permanent_session_lifetime = timedelta(hours=1)
# session cookie security
app.config['SESSION_COOKIE_HTTPONLY'] = True
# app.config['SESSION_COOKIE_SECURE'] = True  # enable when using HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

bank = Bank('data.json')


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

    # compute running balances from the beginning and align to actual konto.saldo
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


# make session name, csrf_token and masked account available in all templates (for navbar)
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
    if request.method == 'POST':
        kontonummer = request.form.get('kontonummer', '').strip()
        pin = request.form.get('pin', '').strip()

        konto = bank.authentifizieren(kontonummer, pin)
        if konto:
            session.permanent = True
            session['kontonummer'] = kontonummer
            session['name'] = konto.name
            session['csrf_token'] = secrets.token_hex(16)
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Kontonummer oder PIN falsch!')

    return render_template('login.html')


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

    parsed = parse_transactions(konto)
    # prepare last 10 points for mini chart
    last = parsed[-10:]
    labels = [p['datetime'] for p in last]
    amounts = [p['amount'] for p in last]
    balances = [p['balance'] for p in last]
    last_activity = last[-1]['datetime'] if last else 'Keine Aktivitäten'

    return render_template('dashboard.html',
                           kontonummer=konto.kontonummer,
                           name=konto.name,
                           saldo=f"{konto.saldo:.2f}",
                           chart_labels=json.dumps(labels),
                           chart_amounts=json.dumps(amounts),
                           chart_balances=json.dumps(balances),
                           last_activity=last_activity)


# Einzahlung
@app.route('/einzahlung', methods=['GET', 'POST'])
def einzahlung():
    if 'kontonummer' not in session:
        return redirect(url_for('login'))

    error = None
    success = None

    if request.method == 'POST':
        try:
            betrag = float(request.form.get('betrag', 0))
            if betrag <= 0:
                error = 'Betrag muss größer als 0 sein!'
            elif bank.einzahlen(session['kontonummer'], betrag):
                success = f'Einzahlung von {betrag:.2f}€ erfolgreich!'
            else:
                error = 'Einzahlung fehlgeschlagen!'
        except ValueError:
            error = 'Ungültiger Betrag!'

    konto = bank.finde_konto(session['kontonummer'])
    return render_template('einzahlung.html',
                           name=konto.name,
                           saldo=f"{konto.saldo:.2f}",
                           error=error,
                           success=success)


# Auszahlung
@app.route('/auszahlung', methods=['GET', 'POST'])
def auszahlung():
    if 'kontonummer' not in session:
        return redirect(url_for('login'))

    error = None
    success = None

    if request.method == 'POST':
        try:
            betrag = float(request.form.get('betrag', 0))
            if betrag <= 0:
                error = 'Betrag muss größer als 0 sein!'
            elif bank.auszahlen(session['kontonummer'], betrag):
                success = f'Auszahlung von {betrag:.2f}€ erfolgreich!'
            else:
                error = 'Nicht genug Guthaben oder ungültiger Betrag!'
        except ValueError:
            error = 'Ungültiger Betrag!'

    konto = bank.finde_konto(session['kontonummer'])
    return render_template('auszahlung.html',
                           name=konto.name,
                           saldo=f"{konto.saldo:.2f}",
                           error=error,
                           success=success)


# Überweisung
@app.route('/ueberweisung', methods=['GET', 'POST'])
def ueberweisung():
    if 'kontonummer' not in session:
        return redirect(url_for('login'))

    error = None
    success = None

    if request.method == 'POST':
        ziel_kontonummer = request.form.get('ziel_kontonummer', '').strip()
        try:
            betrag = float(request.form.get('betrag', 0))

            if not ziel_kontonummer:
                error = 'Zielkontonummer erforderlich!'
            elif betrag <= 0:
                error = 'Betrag muss größer als 0 sein!'
            elif session['kontonummer'] == ziel_kontonummer:
                error = 'Kann nicht auf gleiches Konto überweisen!'
            elif not bank.finde_konto(ziel_kontonummer):
                error = 'Zielkonto nicht gefunden!'
            elif bank.ueberweisen(session['kontonummer'], ziel_kontonummer, betrag):
                ziel = bank.finde_konto(ziel_kontonummer)
                success = f'Überweisung von {betrag:.2f}€ an {ziel.name} erfolgreich!'
            else:
                error = 'Überweisung fehlgeschlagen (nicht genug Guthaben?)!'
        except ValueError:
            error = 'Ungültiger Betrag!'

    konto = bank.finde_konto(session['kontonummer'])
    return render_template('ueberweisung.html',
                           name=konto.name,
                           saldo=f"{konto.saldo:.2f}",
                           error=error,
                           success=success)


# Transaktionen
@app.route('/transaktionen')
def transaktionen():
    if 'kontonummer' not in session:
        return redirect(url_for('login'))

    konto = bank.finde_konto(session['kontonummer'])
    parsed = parse_transactions(konto)

    labels = [p['datetime'] for p in parsed]
    amounts = [p['amount'] for p in parsed]
    balances = [p.get('balance', 0.0) for p in parsed]

    return render_template('transaktionen.html',
                           name=konto.name,
                           saldo=f"{konto.saldo:.2f}",
                           transaktionen=parsed,
                           chart_labels=json.dumps(labels),
                           chart_amounts=json.dumps(amounts),
                           chart_balances=json.dumps(balances))


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


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
