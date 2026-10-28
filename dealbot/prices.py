"""Preise lesen, Rabatt berechnen und Preise huebsch formatieren."""

from __future__ import annotations

import re

# Findet Preisangaben wie "UVP 129,99 €", "statt 99€", "regulär: 1.299 €", "Normalpreis 49,-"
_UVP_PATTERN = re.compile(
    r"(?:uvp|statt|regul(?:ä|ae)r(?:er preis)?|normalpreis|listenpreis)"
    r"\s*[:.]?\s*(?:von\s*|ca\.?\s*)?"
    r"(?:€\s*)?(\d{1,3}(?:\.\d{3})*(?:,\d{1,2}|,-)?|\d+(?:[.,]\d{1,2})?)\s*(?:€|eur|euro|,-)?",
    re.IGNORECASE,
)


def parse_price(value) -> float | None:
    """Wandelt '1.299,99 €', '12,97€', '129,-', 49.9 usw. in eine Zahl um."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().lower()
    s = s.replace("€", "").replace("eur", "").replace("\xa0", "").replace(" ", "")
    s = s.replace(",-", "").replace(",–", "")
    if not s:
        return None
    if "," in s:
        # Deutsches Format: Punkt = Tausender, Komma = Dezimal
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        # "1.299" ohne Komma = Tausenderpunkt
        s = s.replace(".", "")
    s = re.sub(r"[^0-9.]", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def find_uvp_in_text(*texts: str) -> float | None:
    """Sucht eine UVP / einen 'statt'-Preis im Titel oder in der Beschreibung."""
    for text in texts:
        if not text:
            continue
        for match in _UVP_PATTERN.finditer(text):
            price = parse_price(match.group(1))
            if price and price > 0:
                return price
    return None


def choose_comparison(price: float, market_price: float | None, uvp: float | None):
    """Waehlt den Vergleichspreis nach der festgelegten Reihenfolge.

    1. Marktpreis (Mydealz-Vergleichspreis), falls vorhanden
    2. sonst UVP / 'statt'-Preis

    Gibt (vergleichspreis, art, rabatt_prozent) zurueck oder None.
    """
    if market_price and market_price > 0:
        reference, kind = market_price, "Marktpreis"
    elif uvp and uvp > 0:
        reference, kind = uvp, "UVP"
    else:
        return None
    discount = (1 - price / reference) * 100
    return reference, kind, discount


def format_eur(value: float) -> str:
    """129.9 -> '129,90 €', 1299 -> '1.299,00 €'"""
    s = f"{value:,.2f}"  # 1,299.00
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"
