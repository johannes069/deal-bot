"""Alles, was mit Mydealz zu tun hat: RSS-Feeds lesen und Deal-Seiten auswerten."""

from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from .prices import parse_price

BASE_URL = "https://www.mydealz.de"

# Felder, unter denen Mydealz/Pepper eine UVP bzw. einen alten Preis ablegen koennte
_UVP_KEYS = ("uvp", "rrp", "listPrice", "originalPrice", "oldPrice")


@dataclass
class FeedItem:
    thread_id: str
    title: str
    link: str
    description: str = ""
    categories: list[str] = field(default_factory=list)
    merchant: str | None = None
    price: float | None = None
    from_category_feed: bool = False


@dataclass
class DealDetails:
    price: float | None = None
    market_price: float | None = None  # Mydealz-Vergleichspreis ("nextBestPrice")
    uvp: float | None = None
    expired: bool = False
    merchant: str | None = None
    found_thread_data: bool = False


def category_feed_url(slug: str) -> str:
    return f"{BASE_URL}/rss/gruppe/{slug.strip().strip('/')}"


def thread_id_from_link(link: str) -> str | None:
    match = re.search(r"-(\d{5,})(?:[/?#]|$)", link or "")
    return match.group(1) if match else None


def _local(tag: str) -> str:
    """'{http://...}merchant' -> 'merchant'"""
    return tag.rsplit("}", 1)[-1].split(":")[-1]


def parse_rss(xml_text: str, from_category_feed: bool = False) -> list[FeedItem]:
    """Liest einen Mydealz-RSS-Feed. Kaputte Feeds liefern eine leere Liste statt eines Absturzes."""
    try:
        root = ET.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
    except ET.ParseError:
        return []

    items: list[FeedItem] = []
    for item in root.iter():
        if _local(item.tag) != "item":
            continue
        data: dict = {"categories": []}
        for child in item:
            name = _local(child.tag)
            text = (child.text or "").strip()
            if name == "title":
                data["title"] = html.unescape(text)
            elif name == "link":
                data["link"] = text
            elif name == "guid" and "link" not in data and text.startswith("http"):
                data["guid_link"] = text
            elif name == "description":
                data["description"] = text
            elif name == "category" and text:
                data["categories"].append(html.unescape(text))
            elif name == "merchant":
                data["merchant"] = child.attrib.get("name") or text or None
                data["price"] = parse_price(child.attrib.get("price"))
        link = data.get("link") or data.get("guid_link") or ""
        thread_id = thread_id_from_link(link)
        if not thread_id or not data.get("title"):
            continue
        items.append(
            FeedItem(
                thread_id=thread_id,
                title=data["title"],
                link=link,
                description=_strip_html(data.get("description", "")),
                categories=data["categories"],
                merchant=data.get("merchant"),
                price=data.get("price"),
                from_category_feed=from_category_feed,
            )
        )
    return items


def _strip_html(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Deal-Seite auswerten
# ---------------------------------------------------------------------------

def _iter_json_blobs(page: str):
    """Mydealz bettet Deal-Daten als JSON in data-vue3/data-vue2-Attribute ein."""
    for match in re.finditer(r'data-vue[23]=(["\'])(.*?)\1', page, re.DOTALL):
        raw = html.unescape(match.group(2))
        try:
            yield json.loads(raw)
        except (ValueError, TypeError):
            continue
    for match in re.finditer(
        r'<script[^>]*type="application/(?:ld\+)?json"[^>]*>(.*?)</script>', page, re.DOTALL
    ):
        try:
            yield json.loads(match.group(1))
        except (ValueError, TypeError):
            continue


def _find_thread(obj, thread_id: str):
    """Sucht im JSON rekursiv nach dem Objekt, das genau diesen Deal beschreibt."""
    if isinstance(obj, dict):
        if str(obj.get("threadId", "")) == thread_id and (
            "price" in obj or "nextBestPrice" in obj
        ):
            return obj
        for value in obj.values():
            found = _find_thread(value, thread_id)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _find_thread(value, thread_id)
            if found is not None:
                return found
    return None


def _positive(value) -> float | None:
    price = parse_price(value)
    return price if price is not None and price > 0 else None


def _from_thread_dict(thread: dict) -> DealDetails:
    details = DealDetails(found_thread_data=True)
    details.price = parse_price(thread.get("price"))
    details.market_price = _positive(thread.get("nextBestPrice"))
    for key in _UVP_KEYS:
        if _positive(thread.get(key)):
            details.uvp = _positive(thread.get(key))
            break
    details.expired = bool(thread.get("isExpired") or thread.get("expired"))
    merchant = thread.get("merchant")
    if isinstance(merchant, dict):
        details.merchant = merchant.get("merchantName") or merchant.get("name")
    elif isinstance(merchant, str):
        details.merchant = merchant
    return details


def _number_after(key: str, text: str) -> float | None:
    match = re.search(rf'"{key}"\s*:\s*"?(-?\d+(?:\.\d+)?)', text)
    return float(match.group(1)) if match else None


def parse_deal_page(page: str, thread_id: str) -> DealDetails:
    """Holt Preis, Marktpreis (Vergleichspreis) und ggf. UVP von einer Mydealz-Deal-Seite."""
    # 1. Weg: eingebettete JSON-Daten sauber auslesen
    for blob in _iter_json_blobs(page):
        thread = _find_thread(blob, thread_id)
        if thread is not None:
            return _from_thread_dict(thread)

    # 2. Weg (Fallback): im Text rund um die Deal-ID nach den Feldern suchen
    text = html.unescape(page)
    match = re.search(rf'"threadId"\s*:\s*"?{re.escape(thread_id)}"?', text)
    if match:
        window = text[match.start(): match.start() + 6000]
        details = DealDetails(found_thread_data=True)
        details.price = _number_after("price", window)
        market = _number_after("nextBestPrice", window)
        details.market_price = market if market and market > 0 else None
        details.expired = bool(re.search(r'"isExpired"\s*:\s*true', window))
        merchant = re.search(r'"merchantName"\s*:\s*"([^"]+)"', window)
        details.merchant = merchant.group(1) if merchant else None
        return details

    return DealDetails(found_thread_data=False)
