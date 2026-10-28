"""Automatische Tests mit Beispieldaten (laufen ohne Internet).

Starten mit:  pip install pytest  und dann  pytest
"""

import html
import json
from pathlib import Path

from dealbot.bot import matches_filters, run
from dealbot.config import Config, load_config
from dealbot.http import FetchError
from dealbot.mydealz import parse_deal_page, parse_rss
from dealbot.prices import choose_comparison, find_uvp_in_text, format_eur, parse_price
from dealbot.seen import SeenStore

FIXTURES = Path(__file__).parent / "fixtures"
FEED = (FIXTURES / "feed.xml").read_text(encoding="utf-8")


def deal_page(thread_id, price, next_best, related=True, expired=False):
    """Baut eine Beispiel-Deal-Seite wie bei Mydealz (Daten als JSON im data-vue3-Attribut)."""
    thread = {
        "threadId": str(thread_id),
        "title": "Beispiel",
        "price": price,
        "nextBestPrice": next_best,
        "isExpired": expired,
        "merchant": {"merchantName": "Amazon"},
    }
    other = {"threadId": "1111111", "price": 1.0, "nextBestPrice": 999.0}
    blobs = [{"name": "ThreadMainContent", "props": {"thread": thread}}]
    if related:
        blobs.insert(0, {"name": "RelatedThreads", "props": {"threads": [other]}})
    divs = "".join(f'<div data-vue3="{html.escape(json.dumps(b))}"></div>' for b in blobs)
    return f"<html><body>{divs}</body></html>"


# --- Preise -----------------------------------------------------------------

def test_parse_price_formats():
    assert parse_price("1.299,99 €") == 1299.99
    assert parse_price("12,97€") == 12.97
    assert parse_price("129,-") == 129
    assert parse_price("1.299") == 1299
    assert parse_price(49.9) == 49.9
    assert parse_price("") is None
    assert parse_price(None) is None


def test_uvp_from_text():
    assert find_uvp_in_text("Nike Sneaker, UVP 179,99 €") == 179.99
    assert find_uvp_in_text("Jacke statt 99€ nur heute") == 99
    assert find_uvp_in_text("nichts drin") is None


def test_comparison_order_prefers_market_price():
    ref, kind, discount = choose_comparison(50, market_price=80, uvp=200)
    assert (ref, kind) == (80, "Marktpreis")
    assert round(discount) == 38
    ref, kind, _ = choose_comparison(50, market_price=None, uvp=200)
    assert kind == "UVP"
    assert choose_comparison(50, None, None) is None


def test_format_eur():
    assert format_eur(1299) == "1.299,00 €"
    assert format_eur(9.5) == "9,50 €"


# --- Mydealz ----------------------------------------------------------------

def test_parse_rss():
    items = parse_rss(FEED)
    assert len(items) == 4
    first = items[0]
    assert first.thread_id == "2900001"
    assert first.merchant == "Amazon"
    assert first.price == 149.0
    assert "UVP 419,00" in first.description


def test_parse_rss_broken_feed_does_not_crash():
    assert parse_rss("<html>Wartungsarbeiten</html") == []


def test_deal_page_picks_the_right_thread():
    page = deal_page("2900001", 149.0, 349.0)
    details = parse_deal_page(page, "2900001")
    assert details.price == 149.0
    assert details.market_price == 349.0
    assert details.merchant == "Amazon"


def test_deal_page_without_data():
    details = parse_deal_page("<html>nichts</html>", "2900001")
    assert not details.found_thread_data


# --- Filter + kompletter Lauf ------------------------------------------------

def make_cfg(**kwargs):
    cfg = Config(
        min_rabatt_prozent=50,
        suchbegriffe=["kopfhörer", "sneaker"],
        kategorien=[],
        ausschlusswoerter=["refurbished"],
        feeds=["https://www.mydealz.de/rss/new"],
        pause_zwischen_abrufen_sekunden=1,
    )
    for key, value in kwargs.items():
        setattr(cfg, key, value)
    return cfg


def test_filters():
    items = {i.thread_id: i for i in parse_rss(FEED)}
    cfg = make_cfg()
    assert matches_filters(items["2900001"], cfg)        # Kopfhörer
    assert matches_filters(items["2900002"], cfg)        # Sneaker
    assert not matches_filters(items["2900003"], cfg)    # refurbished ausgeschlossen
    assert not matches_filters(items["2900004"], cfg)    # Waschmittel passt nicht


def fake_fetch(pages):
    def fetch(url):
        if url in pages:
            return pages[url]
        raise FetchError(f"{url} nicht erreichbar")
    return fetch


def test_full_run_reports_and_remembers(tmp_path):
    pages = {
        "https://www.mydealz.de/rss/new": FEED,
        # 149 € vs. Marktpreis 349 € = -57 % -> melden
        "https://www.mydealz.de/deals/sony-wh-1000xm5-kopfhorer-2900001": deal_page("2900001", 149.0, 349.0),
        # kein Marktpreis -> UVP aus dem Titel 179,99 € vs. 69,99 € = -61 % -> melden (vs. UVP)
        "https://www.mydealz.de/deals/nike-air-max-2900002": deal_page("2900002", 69.99, None),
    }
    sent = []
    seen = SeenStore(tmp_path / "seen.json")
    stats = run(make_cfg(), seen, fake_fetch(pages), send=sent.append, sleep=lambda s: None)

    assert stats["gemeldet"] == 2
    assert "vs. Marktpreis" in sent[0] and "57 %" in sent[0]
    assert "vs. UVP" in sent[1] and "61 %" in sent[1]
    seen.save()
    saved = json.loads((tmp_path / "seen.json").read_text())
    assert saved["2900001"]["gemeldet"] is True

    # Zweiter Lauf: nichts doppelt
    sent.clear()
    seen2 = SeenStore(tmp_path / "seen.json")
    seen2.load()
    stats2 = run(make_cfg(), seen2, fake_fetch(pages), send=sent.append, sleep=lambda s: None)
    assert stats2["gemeldet"] == 0 and sent == []


def test_too_small_discount_not_reported(tmp_path):
    pages = {
        "https://www.mydealz.de/rss/new": FEED,
        "https://www.mydealz.de/deals/sony-wh-1000xm5-kopfhorer-2900001": deal_page("2900001", 149.0, 199.0),
        "https://www.mydealz.de/deals/nike-air-max-2900002": deal_page("2900002", 69.99, 89.99),
    }
    sent = []
    seen = SeenStore(tmp_path / "seen.json")
    stats = run(make_cfg(), seen, fake_fetch(pages), send=sent.append, sleep=lambda s: None)
    assert stats["gemeldet"] == 0
    assert seen.contains("2900001")  # gemerkt, damit die Seite nicht jedes Mal neu geladen wird


def test_source_down_does_not_crash(tmp_path):
    seen = SeenStore(tmp_path / "seen.json")
    stats = run(make_cfg(), seen, fake_fetch({}), send=lambda m: None, sleep=lambda s: None)
    assert stats["feed_deals"] == 0
    assert stats["probleme"]


def test_failed_detail_page_is_retried_later(tmp_path):
    pages = {"https://www.mydealz.de/rss/new": FEED}  # Deal-Seiten nicht erreichbar
    seen = SeenStore(tmp_path / "seen.json")
    run(make_cfg(), seen, fake_fetch(pages), send=lambda m: None, sleep=lambda s: None)
    assert not seen.contains("2900001")


def test_dry_run_changes_nothing(tmp_path):
    pages = {
        "https://www.mydealz.de/rss/new": FEED,
        "https://www.mydealz.de/deals/sony-wh-1000xm5-kopfhorer-2900001": deal_page("2900001", 149.0, 349.0),
    }
    seen = SeenStore(tmp_path / "seen.json")
    stats = run(make_cfg(), seen, fake_fetch(pages), send=None, sleep=lambda s: None)
    assert stats["gemeldet"] == 1
    assert not seen.changed


def test_seen_prune(tmp_path):
    seen = SeenStore(tmp_path / "seen.json")
    seen.entries = {"alt": {"zeit": "2020-01-01T00:00:00+00:00"}, "neu": {"zeit": "2999-01-01T00:00:00+00:00"}}
    assert seen.prune(30) == 1
    assert list(seen.entries) == ["neu"]


def test_real_config_file_loads():
    cfg = load_config(Path(__file__).parent.parent / "config.yaml")
    assert cfg.min_rabatt_prozent == 50
    assert "refurbished" in cfg.ausschlusswoerter
