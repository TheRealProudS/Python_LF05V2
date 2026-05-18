import json
import os
from konto import Konto
from werkzeug.security import generate_password_hash, check_password_hash

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

    def alle_konten(self):
        return list(self.konten.values())