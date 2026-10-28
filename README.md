# 🔥 Deal-Bot

Der Bot schaut alle 30 Minuten auf **Mydealz** nach neuen Deals. Wenn ein Angebot **mindestens 50 %** (einstellbar) unter dem Vergleichspreis liegt, schickt er dir eine Nachricht in deinen eigenen Telegram-Chat.

**So entscheidet der Bot, was „außergewöhnlich günstig“ ist:**

1. Er liest neue Deals aus den offiziellen Mydealz-RSS-Feeds.
2. Er behält nur Deals, die zu deinen Suchbegriffen oder Kategorien passen und keine Ausschlusswörter enthalten.
3. Für diese Kandidaten öffnet er **einmal** die Mydealz-Deal-Seite und liest dort die Preise. Shops wie Amazon oder Zalando ruft er nie auf.
4. Als Vergleichspreis nimmt er:
   - **zuerst den Marktpreis**, also den Vergleichspreis, den Mydealz beim Deal anzeigt (meist der beste Preis bei anderen Händlern),
   - **sonst die UVP / den „statt“-Preis** aus Titel oder Beschreibung.
5. Ist der Rabatt groß genug, kommt eine Telegram-Nachricht. In der Nachricht steht, ob gegen den Marktpreis oder gegen die UVP gerechnet wurde.

> ℹ️ **Ehrlicher Hinweis:** Die RSS-Feeds von Mydealz enthalten nur den Angebotspreis, keinen Vergleichspreis. Deshalb liest der Bot die Deal-Seite selbst. Ändert Mydealz eines Tages den Aufbau seiner Seiten, findet der Bot vielleicht keine Vergleichspreise mehr. Das merkst du daran, dass im Test-Modus (Schritt 6) „0 Deal-Seiten mit Preisdaten“ steht. Dann muss der Code angepasst werden.

---

## Was du einmalig erledigen musst

Du brauchst etwa 20 Minuten. Am besten am Laptop, weil GitHub am Handy unübersichtlich ist.

### Schritt 1: Repo auf GitHub anlegen und Dateien hochladen

1. Geh auf [github.com](https://github.com) und melde dich an.
2. Klick oben rechts auf **„+“** und dann auf **„New repository“**.
3. Unter **Repository name** gibst du `deal-bot` ein.
4. Wähle **Public** (Begründung siehe unten), lass alle Häkchen weg und klick auf **„Create repository“**.
5. Auf der neuen, leeren Seite klickst du auf den Link **„uploading an existing file“**.
6. Lade die Datei **`deal-bot.zip`** herunter. Du findest sie im Claude-Chat als Datei-Karte: draufklicken und dann auf „Herunterladen“. Sie landet meist im Ordner **Downloads**.
   - Entpacken: **Mac** → Doppelklick auf die ZIP. **Windows** → Rechtsklick → **„Alle extrahieren…“**.
   - Öffne den entpackten Ordner `deal-bot`, **markiere alles darin** (Mac: Cmd + A, Windows: Strg + A; nicht den Ordner selbst) und zieh die Auswahl ins Browserfenster.
7. Klick unten auf **„Commit changes“**.
8. **Wichtig:** Prüfe in der Dateiliste, ob es einen Ordner **`.github`** gibt. Mac und Windows verstecken Ordner, die mit einem Punkt beginnen, deshalb fehlt er oft. Wenn er fehlt:
   - Klick auf **„Add file“** und dann auf **„Create new file“**.
   - Tippe als Dateinamen genau `.github/workflows/deal-bot.yml` ein. Die Schrägstriche legen die Ordner automatisch an.
   - Öffne auf deinem Computer die Datei `deal-bot.yml` aus dem Ordner `.github/workflows` mit einem Texteditor, kopiere den ganzen Inhalt und füge ihn bei GitHub ein.
     - Mac: Im Finder **Cmd + Shift + .** drücken, dann siehst du versteckte Ordner.
     - Windows: Im Explorer unter **Ansicht** das Häkchen bei **„Ausgeblendete Elemente“** setzen.
   - Klick auf **„Commit changes“**.

**Warum Public?** Bei öffentlichen Repos sind GitHub Actions kostenlos und unbegrenzt. Bei privaten Repos hast du 2.000 Gratis-Minuten pro Monat, und dieser Bot braucht davon etwa 1.500. Zusammen mit deinem Flug-Bot würden die Minuten nicht reichen. Im Code stehen keine Geheimnisse, denn Token und Chat-ID liegen nur in den Secrets (Schritt 4). Sichtbar sind nur der Code, deine Suchbegriffe und die Liste der gemeldeten Deal-Nummern.

---

### Schritt 2: Neuen Telegram-Bot erstellen und Token holen

Du brauchst einen **neuen** Bot, damit die Deals nicht im Chat deines Flug-Bots landen.

1. Öffne Telegram und such nach **@BotFather**. Er hat einen blauen Haken.
2. Tippe auf **Start** und schick dann `/newbot`.
3. BotFather fragt nach einem **Namen**. Den sieht man im Chat, zum Beispiel `Johannes Deals`.
4. Dann fragt er nach einem **Benutzernamen**. Der muss auf `bot` enden, zum Beispiel `johannes_deals_bot`. Ist der Name schon vergeben, probier einen anderen.
5. BotFather schickt dir eine Nachricht mit dem **Token**. Das sieht ungefähr so aus:
   `7123456789:AAH...langer-text...`
6. Kopiere den Token und heb ihn kurz auf. **Gib ihn niemandem und schreib ihn nirgends in den Code.**

---

### Schritt 3: Chat für die Deals festlegen und Chat-ID herausfinden

**Variante A (einfachste): Privater Chat mit dem neuen Bot**

Weil es ein neuer Bot ist, ist das automatisch ein eigener Chat, getrennt vom Flug-Bot.

1. Klick in der BotFather-Nachricht auf den Link zu deinem Bot, zum Beispiel `t.me/johannes_deals_bot`.
2. Tippe auf **Start** und schick ihm danach irgendeine Nachricht, zum Beispiel `hallo`.
3. Öffne im Browser diese Adresse. Ersetze `DEIN_TOKEN` durch den Token aus Schritt 2:
   `https://api.telegram.org/botDEIN_TOKEN/getUpdates`
   Beispiel: `https://api.telegram.org/bot7123456789:AAH.../getUpdates`
4. Du siehst Text in geschweiften Klammern. Such die Stelle `"chat":{"id":123456789`.
5. Die Zahl hinter `"id":` ist deine **Chat-ID**. Kopiere sie.

**Variante B: Eigene Gruppe, zum Beispiel „Deals 🔥“**

1. Erstelle in Telegram eine neue Gruppe und füge deinen neuen Bot als Mitglied hinzu.
2. Schreib in der Gruppe `/start@johannes_deals_bot`, natürlich mit deinem Bot-Namen.
3. Öffne die `getUpdates`-Adresse wie in Variante A.
4. Such dort die Chat-ID der Gruppe. Sie beginnt mit einem Minus, zum Beispiel `-1001234567890`. Kopiere sie **mit Minus**.

> Wenn bei `getUpdates` nur `{"ok":true,"result":[]}` steht: Schick dem Bot noch eine Nachricht und lade die Seite neu.

---

### Schritt 4: Token und Chat-ID als GitHub Secrets eintragen

1. Öffne dein Repo `deal-bot` auf GitHub.
2. Klick oben in der Leiste auf **⚙️ Settings**. Das ist der letzte Reiter rechts.
3. Klick links auf **„Secrets and variables“** und dann auf **„Actions“**.
4. Klick auf den grünen Button **„New repository secret“**.
5. Trag das erste Secret ein:
   - **Name:** `TELEGRAM_BOT_TOKEN`
   - **Secret:** dein Token aus Schritt 2
   - Klick auf **„Add secret“**.
6. Klick noch einmal auf **„New repository secret“** und trag das zweite ein:
   - **Name:** `TELEGRAM_CHAT_ID`
   - **Secret:** deine Chat-ID aus Schritt 3
   - Klick auf **„Add secret“**.

Die Namen müssen **genau so** geschrieben sein: Großbuchstaben, mit Unterstrichen.

---

### Schritt 5: GitHub Actions aktivieren und Schreibrechte erlauben

Der Bot muss nach jedem Lauf die Datei `seen.json` speichern dürfen. Darin merkt er sich, welche Deals er schon gemeldet hat.

1. Klick im Repo auf **⚙️ Settings**.
2. Klick links auf **„Actions“** und dann auf **„General“**.
3. Unter **„Actions permissions“** muss **„Allow all actions and reusable workflows“** ausgewählt sein. Das ist meist schon so.
4. Scroll nach unten zu **„Workflow permissions“**.
5. Wähle **„Read and write permissions“** und klick auf **„Save“**.
6. Klick oben auf den Reiter **▶️ Actions**. Falls dort ein grüner Button wie **„I understand my workflows, go ahead and enable them“** erscheint, klick ihn an.

---

### Schritt 6: Testlauf starten

1. Klick im Repo auf den Reiter **▶️ Actions**.
2. Klick links auf **„Deal-Bot“**.
3. Rechts erscheint ein grauer Button **„Run workflow“**. Klick darauf.
4. Wähle beim Modus **`test`** aus und klick auf den grünen Button **„Run workflow“**.
5. Warte etwa 1 Minute. Danach solltest du in Telegram **zwei Nachrichten** bekommen:
   - **„Deal-Bot Testnachricht“**: Die Verbindung zu Telegram klappt.
   - **„Systemcheck“**: Zeigt, ob Mydealz erreichbar ist und ob Preise gelesen werden konnten.

**Was die Ergebnisse bedeuten:**

| Ergebnis | Bedeutung |
|---|---|
| ✅ grüner Haken in Actions + beide Nachrichten | Alles funktioniert. Der Bot läuft ab jetzt alle 30 Minuten von selbst. |
| ❌ roter Haken und keine Nachricht | Token oder Chat-ID ist falsch, oder du hast dem Bot noch nie geschrieben. Klick auf den Lauf und dann auf **„deals“**, um die Fehlermeldung zu lesen. Prüf danach Schritt 3 und 4. |
| Testnachricht da, aber „❌ Keine Deals aus den Feeds geladen“ | Mydealz ist gerade nicht erreichbar oder blockt GitHub. Probier es später noch einmal. |
| „⚠️ … lieferte keine Deals (Kategorie-Name richtig?)“ | Ein Kategorie-Name in der `config.yaml` stimmt nicht (siehe Schritt 7). |
| „0 von 3 Deal-Seiten mit Preisdaten“ | Mydealz hat den Seitenaufbau geändert. Der Code muss angepasst werden. |

**Tipp:** Mit dem Modus **`trockenlauf`** siehst du im Log (Lauf anklicken und dann **„deals“**), welche Deals gemeldet **würden**. Dabei wird nichts gesendet und nichts gespeichert. So kannst du gut ausprobieren, ob deine Einstellungen passen.

---

### Schritt 7: Rabattschwelle und Suchbegriffe ändern

Alles Wichtige steht in der Datei **`config.yaml`**:

1. Klick im Repo auf **`config.yaml`**.
2. Klick oben rechts auf das **Stift-Symbol ✏️** („Edit this file“).
3. Ändere, was du möchtest:
   - **Rabattschwelle:** `min_rabatt_prozent: 50`. Setz zum Beispiel `40` ein, dann bekommst du mehr Deals. Mit `60` bekommst du weniger, dafür nur krassere.
   - **Suchbegriffe:** Füg eine neue Zeile mit `  - begriff` hinzu. Achte auf die 2 Leerzeichen und den Bindestrich am Anfang. Schreib am besten auch die Variante ohne Umlaut dazu, zum Beispiel `kopfhörer` und `kopfhoerer`.
   - **Kategorien:** Öffne auf mydealz.de eine Kategorie. In der Adresszeile steht dann zum Beispiel `mydealz.de/gruppe/elektronik`. Der letzte Teil (`elektronik`) kommt in die Liste. Wenn du **nur** bestimmte Produkte willst, lösch die Kategorien. Dann prüft der Bot nur Deals mit deinen Suchbegriffen.
   - **Ausschlusswörter:** Deals mit diesen Wörtern werden ignoriert.
4. Klick oben rechts auf **„Commit changes…“** und dann noch einmal auf **„Commit changes“**.
5. Die Änderung gilt ab dem nächsten Lauf. Wenn du sie gleich prüfen willst, starte einen `trockenlauf` (Schritt 6).

> ⚠️ Wenn nach einer Änderung ein roter Haken mit **„config.yaml hat einen Formatfehler“** erscheint, liegt das meistens an einem fehlenden Leerzeichen oder einer falschen Einrückung. Vergleich deine Zeile mit den Zeilen darüber.

---

## Gut zu wissen

- **Die Zeiten sind nicht exakt.** GitHub startet geplante Läufe manchmal 5 bis 20 Minuten später. Das ist normal.
- **Bei Pausen schaltet GitHub ab.** Hat ein öffentliches Repo 60 Tage lang keine Aktivität, deaktiviert GitHub den Zeitplan. Die Speicher-Commits des Bots zählen normalerweise als Aktivität. Falls doch einmal Schluss ist, aktivierst du den Workflow unter **Actions** einfach wieder.
- **Nichts kommt doppelt.** In `seen.json` steht jede geprüfte Deal-Nummer. Einträge, die älter als 30 Tage sind, werden automatisch gelöscht.
- **Der Bot ist rücksichtsvoll.** Er liest höchstens 15 Mydealz-Seiten pro Lauf, mit 3 Sekunden Pause dazwischen. Wird er gebremst, hört er auf und macht beim nächsten Lauf weiter.
- **Ausfälle sind kein Problem.** Ist Mydealz nicht erreichbar, endet der Lauf ohne Absturz, und der nächste Lauf versucht es erneut.
- **Der Marktpreis kommt aus der Community.** Den Vergleichspreis tragen die Mydealz-Nutzer selbst ein. Er ist meistens gut, aber nicht immer perfekt. Ein Blick auf den Deal lohnt sich vor dem Kauf.

## Aufbau des Projekts (für Neugierige)

```
deal-bot/
├── main.py                     Startpunkt (Modi: normal, test, trockenlauf)
├── config.yaml                 deine Einstellungen
├── seen.json                   bereits geprüfte Deals (pflegt der Bot selbst)
├── requirements.txt            benötigte Python-Pakete
├── dealbot/
│   ├── bot.py                  Ablauf: Feeds -> Filter -> Preise -> Telegram
│   ├── mydealz.py              RSS lesen und Deal-Seiten auswerten
│   ├── prices.py               Preise lesen, Rabatt berechnen
│   ├── telegram.py             Nachrichten senden
│   ├── seen.py                 Duplikat-Schutz
│   ├── config.py               config.yaml einlesen und prüfen
│   └── http.py                 Abrufe mit Wiederholung und Fehlerbehandlung
├── tests/                      automatische Tests mit Beispieldaten
└── .github/workflows/deal-bot.yml   Zeitplan für GitHub Actions
```

Lokal testen (optional, falls Python installiert ist):

```bash
pip install -r requirements.txt pytest
pytest                                  # Tests mit Beispieldaten
python main.py --modus trockenlauf      # echter Abruf, nichts wird gesendet
```
