import json
import os
from konto import Konto
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import calendar
import secrets

class Bank:
    def __init__(self, data_file='data.json'):
        self.data_file = data_file
        self.konten = {}
        self.load_data()

    def load_data(self):
        if not os.path.exists(self.data_file):
            self.konten = {}
            return
        with open(self.data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for item in data:
            konto = Konto.from_dict(item)
            if konto and konto.kontonummer:
                self.konten[str(konto.kontonummer)] = konto

    def save_data(self):
        data = [k.to_dict() for k in self.konten.values()]
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _next_kontonummer(self):
        nums = [int(k) for k in self.konten.keys() if k.isdigit()]
        return str(max(nums) + 1) if nums else '1000'

    def konto_erstellen(self, name, pin, start_saldo=0, kontonummer=None):
        if kontonummer is None:
            kontonummer = self._next_kontonummer()
        hashed = generate_password_hash(pin)
        konto = Konto(kontonummer, name, hashed, start_saldo)
        self.konten[str(kontonummer)] = konto
        self.save_data()
        return konto

    def finde_konto(self, kontonummer):
        return self.konten.get(str(kontonummer))

    def authentifizieren(self, kontonummer, pin):
        konto = self.finde_konto(kontonummer)
        if not konto:
            return None
        if isinstance(konto.pin, str) and konto.pin.startswith('pbkdf2:'):
            if check_password_hash(konto.pin, pin):
                return konto
            return None
        
        if konto.pin == pin:
            try:
                konto.pin = generate_password_hash(pin)
                self.save_data()
            except Exception:
                pass
            return konto
        return None

    def einzahlen(self, kontonummer, betrag):
        konto = self.finde_konto(kontonummer)
        if not konto:
            return False
        ok = konto.einzahlen(betrag)
        if ok:
            self.save_data()
        return ok

    def auszahlen(self, kontonummer, betrag):
        konto = self.finde_konto(kontonummer)
        if not konto:
            return False
        ok = konto.auszahlen(betrag)
        if ok:
            self.save_data()
        return ok

    def ueberweisen(self, von_kontonr, nach_kontonr, betrag):
        von = self.finde_konto(von_kontonr)
        nach = self.finde_konto(nach_kontonr)
        if not von or not nach:
            return False
        ok = von.ueberweisen(nach, betrag)
        if ok:
            self.save_data()
        return ok

    def kontostand(self, kontonummer):
        konto = self.finde_konto(kontonummer)
        return konto.saldo if konto else None

    def add_sparplan(self, kontonummer, amount, frequency, target=None, start_next_run=None, name=None):
        konto = self.finde_konto(kontonummer)
        if not konto:
            return None
        plan = {
            'id': secrets.token_hex(8),
            'name': name or 'Sparplan',
            'amount': float(amount),
            'frequency': frequency,  # 'daily','weekly','biweekly','monthly'
            'target': float(target) if target is not None and target != '' else None,
            'active': True,
            'next_run': (start_next_run.isoformat() if start_next_run else datetime.now().isoformat())
        }
        if not hasattr(konto, 'sparplaene'):
            konto.sparplaene = []
        konto.sparplaene.append(plan)
        self.save_data()
        return plan

    def remove_sparplan(self, kontonummer, plan_id):
        konto = self.finde_konto(kontonummer)
        if not konto or not hasattr(konto, 'sparplaene'):
            return False
        for p in konto.sparplaene:
            if p.get('id') == plan_id:
                p['active'] = False
                self.save_data()
                return True
        return False

    def _add_months(self, dt, months):
        # add months to datetime safely
        year = dt.year + (dt.month - 1 + months) // 12
        month = (dt.month - 1 + months) % 12 + 1
        day = min(dt.day, calendar.monthrange(year, month)[1])
        return dt.replace(year=year, month=month, day=day)

    def process_sparplaene(self, now=None):
        now = now or datetime.now()
        changed = False
        for konto in self.konten.values():
            if not hasattr(konto, 'sparplaene'):
                continue
            for plan in konto.sparplaene:
                if not plan.get('active'):
                    continue
                try:
                    next_run = datetime.fromisoformat(plan.get('next_run'))
                except Exception:
                    next_run = now
                # process occurrences up to now
                ran = False
                while next_run <= now and plan.get('active'):
                    amount = float(plan.get('amount', 0))
                    target = plan.get('target')
                    # if target reached, deactivate plan
                    if target is not None:
                        try:
                            if konto.savings >= float(target):
                                plan['active'] = False
                                changed = True
                                break
                        except Exception:
                            pass

                    # attempt transfer if funds available
                    if konto.saldo >= amount and amount > 0:
                        # perform transfer
                        try:
                            konto.transfer_to_savings(amount, plan.get('name'))
                            changed = True
                            ran = True
                        except Exception:
                            pass

                    # advance next_run based on frequency
                    freq = plan.get('frequency')
                    if freq == 'daily':
                        next_run = next_run + timedelta(days=1)
                    elif freq == 'weekly':
                        next_run = next_run + timedelta(weeks=1)
                    elif freq == 'biweekly':
                        next_run = next_run + timedelta(weeks=2)
                    elif freq == 'monthly':
                        next_run = self._add_months(next_run, 1)
                    else:
                        # default to monthly
                        next_run = self._add_months(next_run, 1)

                    plan['next_run'] = next_run.isoformat()

                    # if target is set and reached after transfer, deactivate
                    if plan.get('target') is not None:
                        try:
                            if konto.savings >= float(plan.get('target')):
                                plan['active'] = False
                                changed = True
                                break
                        except Exception:
                            pass

                # end while
        if changed:
            self.save_data()
        return changed

    def alle_konten(self):
        return list(self.konten.values())