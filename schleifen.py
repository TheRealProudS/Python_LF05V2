def countdown():
    """Aufgabe 1: Countdown von 10 bis 0."""
    for zahl in range(10, -1, -1):
        print(zahl)
    print("Start!")


def fizzbuzz():
    """Aufgabe 2: FizzBuzz von 1 bis 100."""
    for zahl in range(1, 101):
        if zahl % 15 == 0:
            print("FizzBuzz")
        elif zahl % 3 == 0:
            print("Fizz")
        elif zahl % 5 == 0:
            print("Buzz")
        else:
            print(zahl)


def number_analysis():
    """Aufgabe 3: Zahlen-Analyse bis zur leeren Eingabe."""
    count = 0
    summe = 0
    gerade = 0
    ungerade = 0
    maximum = None
    minimum = None

    while True:
        eingabe = input("Zahl (Enter zum Beenden): ")
        if eingabe == "":
            break

        try:
            zahl = int(eingabe)
        except ValueError:
            print("Ungültige Eingabe. Bitte eine ganze Zahl eingeben.")
            continue

        count += 1
        summe += zahl
        if zahl % 2 == 0:
            gerade += 1
        else:
            ungerade += 1

        if maximum is None or zahl > maximum:
            maximum = zahl
        if minimum is None or zahl < minimum:
            minimum = zahl

    if count == 0:
        print("Keine Zahlen eingegeben.")
        return

    durchschnitt = summe / count
    print(f"Anzahl:       {count}")
    print(f"Summe:        {summe}")
    print(f"Durchschnitt: {durchschnitt}")
    print(f"Maximum:      {maximum}")
    print(f"Minimum:      {minimum}")
    print(f"Gerade:       {gerade}")
    print(f"Ungerade:     {ungerade}")


def read_positive_int(prompt):
    while True:
        eingabe = input(prompt)
        try:
            wert = int(eingabe)
            if wert > 0:
                return wert
            print("Bitte eine positive ganze Zahl eingeben.")
        except ValueError:
            print("Ungültige Eingabe. Bitte eine ganze Zahl eingeben.")


def draw_rectangle():
    """Aufgabe 4: Rechteck mit Symbolen zeichnen."""
    zeilen = read_positive_int("Anzahl der Zeilen: ")
    spalten = read_positive_int("Anzahl der Spalten: ")
    symbol = input("Symbol: ")
    if symbol == "":
        symbol = "#"

    for _ in range(zeilen):
        print(symbol * spalten)


def calculator():
    """Aufgabe 5: Taschenrechner mit Schleife."""
    print("=== Taschenrechner ===")
    berechnungen = 0

    while True:
        erste_zahl = None
        while erste_zahl is None:
            eingabe = input("Erste Zahl: ")
            try:
                erste_zahl = float(eingabe)
            except ValueError:
                print("Ungültige Eingabe. Bitte eine Zahl eingeben.")

        operation = input("Operation (+, -, *, /): ").strip()
        zweite_zahl = None
        while zweite_zahl is None:
            eingabe = input("Zweite Zahl: ")
            try:
                zweite_zahl = float(eingabe)
            except ValueError:
                print("Ungültige Eingabe. Bitte eine Zahl eingeben.")

        berechnungen += 1

        if operation == "+":
            ergebnis = erste_zahl + zweite_zahl
            print(f"{erste_zahl} + {zweite_zahl} = {ergebnis}")
        elif operation == "-":
            ergebnis = erste_zahl - zweite_zahl
            print(f"{erste_zahl} - {zweite_zahl} = {ergebnis}")
        elif operation == "*":
            ergebnis = erste_zahl * zweite_zahl
            print(f"{erste_zahl} * {zweite_zahl} = {ergebnis}")
        elif operation == "/":
            if zweite_zahl == 0:
                print("Fehler: Division durch 0 nicht möglich.")
            else:
                ergebnis = erste_zahl / zweite_zahl
                print(f"{erste_zahl} / {zweite_zahl} = {ergebnis}")
        else:
            print("Ungültige Operation. Bitte +, -, * oder / eingeben.")

        weiter = input("Weiter? (ja/nein): ").strip().lower()
        if weiter not in ("ja", "j", "yes", "y"):
            break

    print(f"{berechnungen} Berechnung(en) durchgeführt. Auf Wiedersehen!")


def login():
    """Aufgabe 6: Login mit Versuchslimit."""
    benutzername_richtig = "admin"
    passwort_richtig = "geheim123"
    versuche = 3

    while versuche > 0:
        print(f"Versuche verbleibend: {versuche}")
        benutzername = input("Benutzername: ")
        passwort = input("Passwort: ")

        if benutzername == benutzername_richtig and passwort == passwort_richtig:
            print(f"Willkommen, {benutzername}! Du bist eingeloggt.")
            return

        versuche -= 1
        print("Fehler: Benutzername oder Passwort falsch.")

        if versuche == 0:
            print("Konto gesperrt. Zu viele Fehlversuche.")
            return


def main():
    aufgaben = {
        "1": ("Countdown", countdown),
        "2": ("FizzBuzz", fizzbuzz),
        "3": ("Zahlen-Analyse", number_analysis),
        "4": ("Rechteck mit Symbolen zeichnen", draw_rectangle),
        "5": ("Taschenrechner mit Schleife", calculator),
        "6": ("Login mit Versuchslimit", login),
        "0": ("Beenden", None),
    }

    while True:
        print("\nAufgabenblatt: Schleifen")
        for nummer, eintrag in aufgaben.items():
            print(f"{nummer}. {eintrag[0]}")

        auswahl = input("Auswahl: ").strip()
        if auswahl == "0":
            print("Auf Wiedersehen!")
            break

        if auswahl in aufgaben:
            print()
            aufgaben[auswahl][1]()
        else:
            print("Ungültige Auswahl. Bitte 0 bis 6 eingeben.")


if __name__ == "__main__":
    main()
