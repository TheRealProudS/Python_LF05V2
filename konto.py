from datetime import datetime


class Konto:

    def __init__(self, kontonummer, name, pin, saldo=0):
        self.kontonummer = kontonummer
        self.name = name
        self.pin = pin
        self.saldo = saldo
        self.transaktionen = []
        self.kredite = []
        self.savings = 0.0
        self.sparplaene = []

    def einzahlen(self, betrag):
        if betrag <= 0:
            return False

        self.saldo += betrag
        zeitstempel = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.transaktionen.append(f"[{zeitstempel}] Einzahlung: +{betrag:.2f}€")
        return True

    def transfer_to_savings(self, betrag, plan_name=None):
        """Transfer from main saldo to savings (depot). Records a transaction.

        Returns True on success, False otherwise.
        """
        if betrag <= 0:
            return False
        if self.saldo < betrag:
            return False
        self.saldo -= betrag
        self.savings += betrag
        zeitstempel = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        name = f" {plan_name}" if plan_name else ""
        # record as outgoing transaction from main account
        self.transaktionen.append(f"[{zeitstempel}] Sparplan{name}: -{betrag:.2f}€")
        return True

    def auszahlen(self, betrag):
        if betrag <= 0:
            return False

        if self.saldo < betrag:
            return False

        self.saldo -= betrag
        zeitstempel = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.transaktionen.append(f"[{zeitstempel}] Auszahlung: -{betrag:.2f}€")
        return True

    def ueberweisen(self, zielkonto, betrag):
        if betrag <= 0:
            return False

        if not self.auszahlen(betrag):
            return False

        zielkonto.einzahlen(betrag)

        zeitstempel = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.transaktionen[-1] = f"[{zeitstempel}] Überweisung an {zielkonto.name}: -{betrag:.2f}€"
        zielkonto.transaktionen[-1] = f"[{zeitstempel}] Überweisung von {self.name}: +{betrag:.2f}€"
        return True

    def zeige_transaktionen(self):
        if not self.transaktionen:
            return "Keine Transaktionen vorhanden."
        return "\n".join(self.transaktionen)

    def to_dict(self):
        return {
            "kontonummer": self.kontonummer,
            "name": self.name,
            "pin": self.pin,
            "saldo": self.saldo,
            "savings": getattr(self, 'savings', 0.0),
            "sparplaene": getattr(self, 'sparplaene', []),
            "transaktionen": self.transaktionen,
            "kredite": self.kredite,
        }

    @staticmethod
    def from_dict(data):
        kontonummer = data.get("kontonummer") or data.get("konto_nummer") or data.get("kontonr")
        name = data.get("name") or data.get("kontoinhaber") or data.get("inhaber") or "Unbekannt"
        pin = data.get("pin") or data.get("pin_code") or data.get("pincode") or "0000"
        saldo = data.get("saldo", 0)

        konto = Konto(kontonummer, name, pin, saldo)
        konto.transaktionen = data.get("transaktionen", [])
        konto.kredite = data.get("kredite", [])
        konto.savings = data.get("savings", 0.0)
        konto.sparplaene = data.get("sparplaene", [])
        return konto
