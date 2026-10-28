"""Der eigentliche Ablauf eines Bot-Laufs."""

from __future__ import annotations

import time
from typing import Callable

from .config import Config
from .http import FetchError, SourceBlocked
from .mydealz import FeedItem, category_feed_url, parse_deal_page, parse_rss
from .prices import choose_comparison, find_uvp_in_text, format_eur
from .seen import SeenStore
from .telegram import TelegramError, deal_message

Fetch = Callable[[str], str]
Send = Callable[[str], None]


def collect_feed_items(cfg: Config, fetch: Fetch) -> tuple[list[FeedItem], list[str]]:
    """Laedt alle Feeds. Ein kaputter Feed bricht den Lauf nicht ab."""
    items: dict[str, FeedItem] = {}
    problems: list[str] = []

    sources = [(category_feed_url(slug), True) for slug in cfg.kategorien]
    sources += [(url, False) for url in cfg.feeds]

    for url, is_category in sources:
        try:
            text = fetch(url)
        except FetchError as exc:
            problems.append(str(exc))
            print(f"[warnung] Feed nicht erreichbar: {exc}")
            continue
        parsed = parse_rss(text, from_category_feed=is_category)
        print(f"[info] {url}: {len(parsed)} Deals im Feed")
        if not parsed:
            problems.append(f"{url} lieferte keine Deals (Kategorie-Name richtig?)")
        for item in parsed:
            existing = items.get(item.thread_id)
            if existing is None:
                items[item.thread_id] = item
            elif item.from_category_feed:
                existing.from_category_feed = True
    return list(items.values()), problems


def matches_filters(item: FeedItem, cfg: Config) -> bool:
    title = item.title.lower()
    full_text = f"{title} {item.description.lower()}"

    if any(word in full_text for word in cfg.ausschlusswoerter):
        return False

    has_keywords = bool(cfg.suchbegriffe)
    has_categories = bool(cfg.kategorien)
    keyword_hit = any(word in title for word in cfg.suchbegriffe)
    category_hit = item.from_category_feed

    if not has_keywords and not has_categories:
        return True
    if has_keywords and has_categories:
        if cfg.verknuepfung == "und":
            return keyword_hit and category_hit
        return keyword_hit or category_hit
    return keyword_hit if has_keywords else category_hit


def run(
    cfg: Config,
    seen: SeenStore,
    fetch: Fetch,
    send: Send | None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Ein kompletter Durchlauf. send=None bedeutet Trockenlauf (nichts senden, nichts speichern)."""
    stats = {"feed_deals": 0, "kandidaten": 0, "geprueft": 0, "gemeldet": 0, "probleme": []}

    removed = seen.prune(cfg.seen_aufbewahrung_tage)
    if removed:
        print(f"[info] {removed} alte Eintraege aus seen.json entfernt")

    items, problems = collect_feed_items(cfg, fetch)
    stats["feed_deals"] = len(items)
    stats["probleme"].extend(problems)
    if not items:
        print("[warnung] Keine Deals geladen - naechster Versuch beim naechsten Lauf.")
        return stats

    candidates = [i for i in items if not seen.contains(i.thread_id) and matches_filters(i, cfg)]
    stats["kandidaten"] = len(candidates)
    print(f"[info] {len(candidates)} neue passende Deals, pruefe bis zu {cfg.max_detailseiten_pro_lauf}")

    for index, item in enumerate(candidates[: cfg.max_detailseiten_pro_lauf]):
        if index:
            sleep(cfg.pause_zwischen_abrufen_sekunden)
        try:
            page = fetch(item.link)
        except SourceBlocked as exc:
            stats["probleme"].append(str(exc))
            print(f"[warnung] Mydealz bremst gerade ({exc}) - Rest folgt beim naechsten Lauf.")
            break
        except FetchError as exc:
            stats["probleme"].append(str(exc))
            print(f"[warnung] Deal-Seite nicht erreichbar, spaeter nochmal: {exc}")
            continue

        stats["geprueft"] += 1
        details = parse_deal_page(page, item.thread_id)
        if not details.found_thread_data:
            print(f"[warnung] Keine Preisdaten auf der Seite gefunden: {item.link}")

        price = details.price if details.price is not None else item.price
        merchant = details.merchant or item.merchant
        uvp = details.uvp or find_uvp_in_text(item.title, item.description)

        def remember(reported: bool, note: str):
            if send is not None:
                seen.add(item.thread_id, reported, note)

        if details.expired:
            remember(False, "abgelaufen")
            continue
        if price is None:
            remember(False, "kein Preis")
            continue
        if price == 0 and not cfg.freebies_melden:
            remember(False, "Freebie")
            continue

        choice = choose_comparison(price, details.market_price, uvp)
        if choice is None:
            print(f"[info] Kein Vergleichspreis: {item.title[:70]}")
            remember(False, "kein Vergleichspreis")
            continue

        reference, kind, discount = choice
        line = (
            f"{item.title[:70]} | {format_eur(price)} vs. {kind} {format_eur(reference)} "
            f"= -{discount:.0f} %"
        )
        if discount < cfg.min_rabatt_prozent:
            print(f"[info] Zu wenig Rabatt: {line}")
            remember(False, f"-{discount:.0f} % vs. {kind}")
            continue

        message = deal_message(item.title, price, reference, kind, discount, merchant, item.link)
        if send is None:
            print(f"[trockenlauf] WUERDE MELDEN: {line}")
            stats["gemeldet"] += 1
            continue
        try:
            send(message)
        except TelegramError as exc:
            stats["probleme"].append(f"Telegram: {exc}")
            print(f"[fehler] Telegram-Versand fehlgeschlagen, naechster Lauf versucht es erneut: {exc}")
            continue
        print(f"[gemeldet] {line}")
        remember(True, f"-{discount:.0f} % vs. {kind}")
        stats["gemeldet"] += 1
        sleep(1)

    return stats


def diagnose(cfg: Config, fetch: Fetch) -> list[str]:
    """Fuer den Testmodus: prueft, ob Mydealz erreichbar ist und Preise lesbar sind."""
    lines = []
    items, problems = collect_feed_items(cfg, fetch)
    if items:
        lines.append(f"✅ Mydealz-Feeds erreichbar: {len(items)} Deals geladen")
    else:
        lines.append("❌ Keine Deals aus den Feeds geladen")
    for problem in problems[:3]:
        lines.append(f"⚠️ {problem}")
    if not items:
        return lines

    with_market = with_any = checked = 0
    for item in items[:3]:
        try:
            page = fetch(item.link)
        except FetchError as exc:
            lines.append(f"❌ Deal-Seite nicht lesbar: {exc}")
            break
        checked += 1
        details = parse_deal_page(page, item.thread_id)
        if details.found_thread_data:
            with_any += 1
        if details.market_price:
            with_market += 1
        time.sleep(cfg.pause_zwischen_abrufen_sekunden)
    if checked:
        lines.append(f"✅ {with_any} von {checked} Deal-Seiten mit Preisdaten gelesen")
        lines.append(f"ℹ️ davon {with_market} mit Marktpreis (Vergleichspreis)")
    return lines
