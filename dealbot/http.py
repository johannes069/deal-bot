"""Hoefliche HTTP-Abrufe mit Wiederholungen und sauberer Fehlerbehandlung."""

from __future__ import annotations

import time

import requests

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0 Safari/537.36"
)


class FetchError(Exception):
    """Quelle war nicht erreichbar (Netzwerk, Zeitueberschreitung, Serverfehler)."""


class SourceBlocked(FetchError):
    """Quelle hat uns gebremst oder blockiert (403/429) - fuer diesen Lauf aufhoeren."""


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Language": "de-DE,de;q=0.9",
        }
    )
    return session


def get_text(session: requests.Session, url: str, timeout: int = 20, retries: int = 2) -> str:
    """Laedt eine Seite. Bei kurzen Stoerungen wird bis zu `retries`-mal neu versucht."""
    last_error = None
    for attempt in range(retries + 1):
        try:
            response = session.get(url, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = f"Netzwerkfehler: {exc.__class__.__name__}"
        else:
            if response.status_code in (403, 429):
                raise SourceBlocked(f"HTTP {response.status_code} bei {url}")
            if response.status_code >= 500:
                last_error = f"Serverfehler HTTP {response.status_code}"
            elif response.status_code >= 400:
                raise FetchError(f"HTTP {response.status_code} bei {url}")
            else:
                response.encoding = response.encoding or "utf-8"
                return response.text
        if attempt < retries:
            time.sleep(3 * (attempt + 1))
    raise FetchError(f"{url} nicht erreichbar ({last_error})")
