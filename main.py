"""Startpunkt des Deal-Bots.

Aufruf:
  python main.py                    normaler Lauf (sucht Deals und meldet sie)
  python main.py --modus test       schickt eine Testnachricht + kurzen Systemcheck an Telegram
  python main.py --modus trockenlauf  zeigt nur im Log, was gemeldet wuerde (sendet nichts)
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from dealbot.bot import diagnose, run
from dealbot.config import ConfigError, load_config
from dealbot.http import get_text, make_session
from dealbot.seen import SeenStore
from dealbot.telegram import TelegramError, send_message


def main() -> int:
    parser = argparse.ArgumentParser(description="Mydealz-Deal-Bot")
    parser.add_argument("--modus", default="normal", choices=["normal", "test", "trockenlauf"])
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--seen", default="seen.json")
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(f"[fehler] {exc}")
        return 1

    session = make_session()

    def fetch(url: str) -> str:
        return get_text(session, url)

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if args.modus == "trockenlauf":
        seen = SeenStore(args.seen)
        seen.load()
        stats = run(cfg, seen, fetch, send=None)
        print(f"[fertig] Trockenlauf: {stats['gemeldet']} Deals wuerden gemeldet")
        return 0

    if not token or not chat_id:
        print(
            "[fehler] TELEGRAM_BOT_TOKEN oder TELEGRAM_CHAT_ID fehlt. "
            "Bitte als GitHub Secrets eintragen (siehe README, Schritt 4)."
        )
        return 1

    def send(text: str) -> None:
        send_message(token, chat_id, text)

    if args.modus == "test":
        stamp = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%d.%m.%Y %H:%M")
        try:
            send(
                "✅ <b>Deal-Bot Testnachricht</b>\n\n"
                f"Die Verbindung zu Telegram funktioniert ({stamp}).\n"
                f"Aktuelle Rabattschwelle: {cfg.min_rabatt_prozent:.0f} %\n\n"
                "Ich prüfe jetzt noch kurz, ob Mydealz erreichbar ist …"
            )
        except TelegramError as exc:
            print(f"[fehler] Testnachricht konnte nicht gesendet werden: {exc}")
            print("Tipp: Token oder Chat-ID pruefen und dem Bot vorher einmal /start schreiben.")
            return 1
        print("[ok] Testnachricht gesendet")
        lines = diagnose(cfg, fetch)
        print("\n".join(lines))
        try:
            send("🔎 <b>Systemcheck</b>\n\n" + "\n".join(lines))
        except TelegramError as exc:
            print(f"[warnung] Systemcheck konnte nicht gesendet werden: {exc}")
        return 0

    seen = SeenStore(args.seen)
    seen.load()
    try:
        stats = run(cfg, seen, fetch, send=send)
    finally:
        seen.save()  # auch bei unerwarteten Fehlern den bisherigen Stand sichern
    print(
        f"[fertig] {stats['feed_deals']} Deals geladen, {stats['kandidaten']} passend, "
        f"{stats['geprueft']} geprueft, {stats['gemeldet']} gemeldet"
    )
    # Probleme mit der Quelle sind kein Absturz: der naechste Lauf versucht es einfach erneut.
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # letzte Sicherung: nie mit Traceback-Chaos enden
        print(f"[fehler] Unerwarteter Fehler: {exc.__class__.__name__}: {exc}")
        sys.exit(0)
