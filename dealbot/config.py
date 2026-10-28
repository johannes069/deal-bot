"""config.yaml einlesen und pruefen."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ConfigError(Exception):
    pass


@dataclass
class Config:
    min_rabatt_prozent: float = 50
    suchbegriffe: list[str] = field(default_factory=list)
    kategorien: list[str] = field(default_factory=list)
    verknuepfung: str = "oder"
    ausschlusswoerter: list[str] = field(default_factory=list)
    feeds: list[str] = field(default_factory=lambda: ["https://www.mydealz.de/rss/new"])
    max_detailseiten_pro_lauf: int = 15
    pause_zwischen_abrufen_sekunden: float = 3
    seen_aufbewahrung_tage: int = 30
    freebies_melden: bool = False


def _str_list(raw, name: str) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        raise ConfigError(f"'{name}' muss eine Liste sein (jede Zeile mit '- ' beginnen).")
    return [str(x).strip() for x in raw if str(x).strip()]


def load_config(path: str | Path = "config.yaml") -> Config:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"{path} nicht gefunden.")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(
            f"config.yaml hat einen Formatfehler (oft: Einrueckung oder fehlendes Leerzeichen nach ':'): {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise ConfigError("config.yaml ist leer oder falsch aufgebaut.")

    cfg = Config()
    try:
        cfg.min_rabatt_prozent = float(raw.get("min_rabatt_prozent", cfg.min_rabatt_prozent))
        cfg.max_detailseiten_pro_lauf = int(raw.get("max_detailseiten_pro_lauf", cfg.max_detailseiten_pro_lauf))
        cfg.pause_zwischen_abrufen_sekunden = float(
            raw.get("pause_zwischen_abrufen_sekunden", cfg.pause_zwischen_abrufen_sekunden)
        )
        cfg.seen_aufbewahrung_tage = int(raw.get("seen_aufbewahrung_tage", cfg.seen_aufbewahrung_tage))
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Eine Zahl in config.yaml ist ungueltig: {exc}") from exc

    cfg.suchbegriffe = [s.lower() for s in _str_list(raw.get("suchbegriffe"), "suchbegriffe")]
    cfg.kategorien = _str_list(raw.get("kategorien"), "kategorien")
    cfg.ausschlusswoerter = [s.lower() for s in _str_list(raw.get("ausschlusswoerter"), "ausschlusswoerter")]
    feeds = _str_list(raw.get("feeds"), "feeds")
    if feeds:
        cfg.feeds = feeds
    cfg.verknuepfung = str(raw.get("verknuepfung", "oder")).strip().lower()
    if cfg.verknuepfung not in ("oder", "und"):
        raise ConfigError("'verknuepfung' muss 'oder' oder 'und' sein.")
    cfg.freebies_melden = bool(raw.get("freebies_melden", False))

    if not 0 < cfg.min_rabatt_prozent < 100:
        raise ConfigError("'min_rabatt_prozent' muss zwischen 1 und 99 liegen.")
    cfg.max_detailseiten_pro_lauf = max(1, min(cfg.max_detailseiten_pro_lauf, 40))
    cfg.pause_zwischen_abrufen_sekunden = max(1.0, cfg.pause_zwischen_abrufen_sekunden)
    cfg.seen_aufbewahrung_tage = max(1, cfg.seen_aufbewahrung_tage)
    return cfg
