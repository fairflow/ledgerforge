"""Per-entity runtime configuration.

One accounting entity (a household, a business, the demo) supplies a `Settings` describing where
its data lives and how transfers/FX are handled. The engine carries NO entity paths, account
names, or numbers — everything entity-specific arrives through here, typically from a TOML file
kept OUT of any public repo. `extra_markers` (e.g. an orphan account number) belongs only in a
private config, never in tracked engine source.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    entity: str = "entity"
    base_currency: str = "GBP"
    txn_dir: Path | None = None          # statements to ingest
    book_path: Path | None = None        # GnuCash book to build/read
    rules_path: Path | None = None       # categorisation rules JSON
    output_dir: Path | None = None       # generated HTML (the serve root)
    save_dir: Path | None = None         # where /save/<tool> POSTs land
    chart_csv: Path | None = None        # chart of accounts CSV
    master_dirs: list[str] = field(default_factory=list)
    master_files: tuple[str, ...] = ("accounts.json", "accounts-master.json")
    name_markers: list[str] = field(default_factory=list)   # holder names that mark own transfers
    extra_markers: list[str] = field(default_factory=list)  # PRIVATE only (e.g. an orphan acct number)
    fx_to_base: dict = field(default_factory=dict)          # currency mnemonic -> rate (string/number)

    @classmethod
    def from_toml(cls, path) -> "Settings":
        path = Path(path)
        data = tomllib.loads(path.read_text())
        base = path.parent

        def p(v):
            if not v:
                return None
            q = Path(v).expanduser()
            return q if q.is_absolute() else (base / q).resolve()

        paths = data.get("paths", {})
        markers = data.get("markers", {})
        return cls(
            entity=data.get("entity", "entity"),
            base_currency=data.get("base_currency", "GBP"),
            txn_dir=p(paths.get("txn_dir")),
            book_path=p(paths.get("book_path")),
            rules_path=p(paths.get("rules_path")),
            output_dir=p(paths.get("output_dir")),
            save_dir=p(paths.get("save_dir")),
            chart_csv=p(paths.get("chart_csv")),
            master_dirs=[str(Path(d).expanduser()) for d in data.get("master_dirs", [])],
            master_files=tuple(data.get("master_files", ("accounts.json", "accounts-master.json"))),
            name_markers=markers.get("names", []),
            extra_markers=markers.get("extra", []),
            fx_to_base=data.get("fx_to_base", {}),
        )
