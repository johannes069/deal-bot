"""Nachrichten an Telegram schicken."""

from __future__ import annotations

import html
import time

import requests

from .prices import format_eur


class TelegramError(Exception):
    pass


def send_message(token: str, chat_id: str, text: str, retries: int = 2) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    last_error = ""
    for attempt in range(retries + 1):
        try:
            response = requests.post(url, data=payload, timeout=20)
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = exc.__class__.__name__
        else:
            if response.ok:
                return
            try:
                body = response.json()
            except ValueError:
                body = {}
            description = body.get("description", response.text[:200])
            if response.status_code == 429:
                wait = body.get("parameters", {}).get("retry_after", 5)
                time.sleep(min(int(wait), 30))
                last_error = "zu viele Nachrichten (429)"
                continue
            # 400/401/403 = falscher Token, falsche Chat-ID o. ae. -> Wiederholen bringt nichts
            raise TelegramError(f"HTTP {response.status_code}: {description}")
        if attempt < retries:
            time.sleep(3)
    raise TelegramError(f"Telegram nicht erreichbar ({last_error})")


def deal_message(
    title: str,
    price: float,
    reference: float,
    kind: str,
    discount: float,
    merchant: str | None,
    link: str,
) -> str:
    e = html.escape
    return (
        f"🔥 <b>−{discount:.0f} % vs. {kind}</b>\n\n"
        f"<b>{e(title)}</b>\n\n"
        f"💶 Angebotspreis: <b>{format_eur(price)}</b>\n"
        f"🏷️ Vergleichspreis: <s>{format_eur(reference)}</s> ({kind})\n"
        f"📉 Rabatt: {discount:.0f} %\n"
        f"🏪 Shop: {e(merchant or 'unbekannt')}\n"
        f"🔗 <a href=\"{e(link, quote=True)}\">Zum Deal auf Mydealz</a>"
    )
