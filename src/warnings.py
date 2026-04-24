"""
WarningCollector — gathers warnings across all pipeline stages,
prints them to the terminal, and writes them to warnings.log.
"""

from __future__ import annotations
from pathlib import Path


class WarningCollector:
    def __init__(self) -> None:
        self._warnings: list[str] = []

    def add(self, message: str) -> None:
        self._warnings.append(message)
        print(f"  [WARNING] {message}")

    def has_warnings(self) -> bool:
        return bool(self._warnings)

    def save(self, run_dir: Path) -> None:
        log_path = run_dir / "warnings.log"
        if self._warnings:
            log_path.write_text("\n".join(self._warnings) + "\n", encoding="utf-8")
        else:
            log_path.write_text("No warnings.\n", encoding="utf-8")
        print(f"  Warnings saved to: {log_path}")

    def __len__(self) -> int:
        return len(self._warnings)
