from __future__ import annotations

import shutil
import sys
import time
from dataclasses import dataclass
from typing import TextIO


def format_duration(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _truncate(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: width - 1] + "…"


@dataclass
class ProgressBar:
    total: int
    label: str = ""
    stream: TextIO = sys.stdout
    width: int = 28
    enabled: bool = True

    def __post_init__(self) -> None:
        self.total = max(0, self.total)
        self.current = 0
        self.started_at = time.monotonic()
        self._closed = False
        self._last_render = ""

    def update_total(self, total: int) -> None:
        self.total = max(0, total)
        self.render()

    def update_label(self, label: str) -> None:
        self.label = label
        self.render()

    def advance(self, amount: int = 1, label: str | None = None) -> None:
        self.current = min(self.total, self.current + amount) if self.total else self.current + amount
        if label is not None:
            self.label = label
        self.render()

    def render(self) -> None:
        if not self.enabled:
            return

        elapsed = time.monotonic() - self.started_at
        rate = self.current / elapsed if elapsed > 0 else 0.0
        if self.total:
            ratio = min(1.0, self.current / self.total)
            completed = int(round(self.width * ratio))
            bar = "#" * completed + "-" * (self.width - completed)
            pct = f"{ratio * 100:6.2f}%"
            counter = f"{self.current:,}/{self.total:,}"
            remaining = max(0, self.total - self.current)
            eta = remaining / rate if rate > 0 else 0.0
            suffix = f"eta {format_duration(eta)}"
        else:
            bar = "-" * self.width
            pct = f"{0.0 if self.current == 0 else 100.0:6.2f}%"
            counter = f"{self.current:,}"
            suffix = "eta --:--"

        parts = [f"[{bar}]", pct, counter, f"{rate:,.1f}/s", f"elapsed {format_duration(elapsed)}", suffix]
        if self.label:
            parts.append(self.label)
        line = " | ".join(parts)
        terminal_width = shutil.get_terminal_size(fallback=(120, 24)).columns
        rendered = _truncate(line, max(20, terminal_width - 1))
        if rendered == self._last_render:
            return
        self._last_render = rendered
        self.stream.write("\r" + rendered)
        self.stream.flush()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.enabled:
            self.render()
            self.stream.write("\n")
            self.stream.flush()

    def __enter__(self) -> "ProgressBar":
        if self.total or self.current:
            self.render()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
