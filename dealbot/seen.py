"""Merkt sich bereits gepruefte Deals in seen.json, damit nichts doppelt gemeldet wird."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class SeenStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.entries: dict[str, dict] = {}
        self.changed = False

    def load(self) -> None:
        if not self.path.exists():
            print(f"[info] {self.path} gibt es noch nicht - wird neu angelegt.")
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8") or "{}")
            self.entries = data if isinstance(data, dict) else {}
        except ValueError:
            print(f"[warnung] {self.path} ist beschaedigt - starte mit leerer Liste.")
            self.entries = {}
            self.changed = True

    def contains(self, thread_id: str) -> bool:
        return thread_id in self.entries

    def add(self, thread_id: str, reported: bool, note: str = "") -> None:
        entry = {"zeit": now_iso(), "gemeldet": reported}
        if note:
            entry["info"] = note
        self.entries[thread_id] = entry
        self.changed = True

    def prune(self, max_age_days: int) -> int:
        """Loescht Eintraege, die aelter als max_age_days sind."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        old = []
        for thread_id, entry in self.entries.items():
            try:
                when = datetime.fromisoformat(entry.get("zeit", ""))
            except (TypeError, ValueError):
                old.append(thread_id)
                continue
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            if when < cutoff:
                old.append(thread_id)
        for thread_id in old:
            del self.entries[thread_id]
        if old:
            self.changed = True
        return len(old)

    def save(self) -> None:
        if not self.changed:
            return
        self.path.write_text(
            json.dumps(self.entries, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
