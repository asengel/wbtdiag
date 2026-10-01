"""
Run configuration.

Everything that is specific to one dataset (column names, date format, units,
whether the numbers are volumes or rates, thresholds) lives here, so the
analysis code itself never needs to be edited to run on a new field.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, asdict
from pathlib import Path
from typing import Optional

import yaml


# Canonical internal column names -> meaning
CANONICAL_COLUMNS = {
    "well": "Well / wellbore identifier (required)",
    "date": "Production date (required unless year + month are given)",
    "year": "Calendar year (use with month when there is no date column)",
    "month": "Calendar month number 1-12 (use with year)",
    "oil": "Oil volume or rate (required)",
    "water": "Water volume or rate (required)",
    "gas": "Gas volume or rate (optional)",
    "water_inj": "Injected water volume or rate (optional)",
    "cum_oil": "Cumulative oil (optional; computed from oil if absent)",
    "cum_water": "Cumulative water (optional; computed from water if absent)",
}


@dataclass
class InputConfig:
    path: str = "data/production.csv"
    date_format: Optional[str] = None   # e.g. "%d-%b-%y"; None = let pandas infer
    dayfirst: bool = True
    thousands: Optional[str] = None     # e.g. "," when numbers look like "1,166"
    encoding: str = "utf-8-sig"
    sep: str = ","
    query: Optional[str] = None         # optional pandas .query() row filter
    # Excel only
    sheet: Optional[object] = 0         # sheet name or index
    skiprows: Optional[object] = None   # e.g. [1] to skip a units row under the header


@dataclass
class ChanParams:
    """Thresholds for the rolling-window Chan (SPE 30775) classifier."""
    win: int = 7                    # rolling-window length (points)
    min_log_span: float = 0.0       # widen window to span >= this many decades of time
                                    # (0 = original fixed-point window). ~0.2 is more
                                    # robust to noise for constant-WOR / coning wells
                                    # but can no longer detect multilayer channeling
    const_slope: float = 0.10       # |WOR slope| below this => flat
    worp_slope_neg: float = -0.15   # WOR' slope below this => coning
    worp_steep: float = 1.00        # WOR' slope above this => channeling
    departure_factor: float = 3.0   # WOR > factor x early baseline => departure
    nearwell_decade: float = 1.0    # >= this many decades of WOR rise ...
    nearwell_dt: float = 3.0        # ... within <= this many months => near-wellbore
    nearwell_min_wor: float = 0.0   # ignore jumps that land below this WOR (0 = original
                                    # behaviour; e.g. 0.1 ignores jumps at WC < ~9%)
    min_seg: int = 4                # merge runs shorter than this
    min_points: int = 8             # fewer WOR points => "Insufficient data"


@dataclass
class Config:
    name: str = "dataset"
    input: InputConfig = field(default_factory=InputConfig)
    columns: dict = field(default_factory=dict)
    # 'volume' : each row holds the volume produced during that row's period
    # 'rate'   : each row holds an average per-day rate (e.g. OFM CV.CDOIL)
    values_are: str = "volume"
    # Aggregate to this pandas frequency before analysis ("MS" = monthly).
    # None keeps the native sampling (only sensible if it is already monthly).
    resample: Optional[str] = "MS"
    volume_unit: str = "Sm3"
    wc_thresholds: tuple = (0.05, 0.50, 0.90)
    min_months: int = 3             # wells with fewer producing periods are skipped
    chan: ChanParams = field(default_factory=ChanParams)
    # output
    output_dir: str = "output"
    fig_format: str = "png"         # png | svg | pdf
    dpi: int = 150

    # ------------------------------------------------------------------ io
    @classmethod
    def from_yaml(cls, path: str | Path) -> "Config":
        with open(path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        return cls.from_dict(raw, base_dir=Path(path).parent)

    @classmethod
    def from_dict(cls, raw: dict, base_dir: Path | None = None) -> "Config":
        raw = dict(raw)
        inp = InputConfig(**_known(InputConfig, raw.pop("input", {}) or {}))
        chan = ChanParams(**_known(ChanParams, raw.pop("chan", {}) or {}))
        cfg = cls(**_known(cls, raw), input=inp, chan=chan)
        if "wc_thresholds" in raw:
            cfg.wc_thresholds = tuple(float(x) for x in raw["wc_thresholds"])
        cfg._base_dir = base_dir
        cfg.validate()
        return cfg

    def resolve_path(self, p: str) -> Path:
        """Paths in a config file are relative to that file (so an example
        folder holding data + config + output is self-contained)."""
        p = Path(p)
        base = getattr(self, "_base_dir", None)
        if p.is_absolute() or base is None:
            return p
        return base / p

    @property
    def output_path(self) -> Path:
        return self.resolve_path(self.output_dir)

    def validate(self) -> None:
        missing = [k for k in ("well", "oil", "water") if k not in self.columns]
        if "date" not in self.columns and not {"year", "month"} <= set(self.columns):
            missing.append("date (or year + month)")
        if missing:
            raise ValueError(f"config.columns is missing required keys: {missing}")
        unknown = set(self.columns) - set(CANONICAL_COLUMNS)
        if unknown:
            raise ValueError(f"config.columns has unknown keys {sorted(unknown)}; "
                             f"allowed: {sorted(CANONICAL_COLUMNS)}")
        if self.values_are not in ("volume", "rate"):
            raise ValueError("values_are must be 'volume' or 'rate'")
        if len(self.wc_thresholds) != 3:
            raise ValueError("wc_thresholds must have exactly three values, e.g. [0.05, 0.5, 0.9]")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["wc_thresholds"] = list(self.wc_thresholds)
        return d


def _known(dc, d: dict) -> dict:
    names = {f.name for f in fields(dc)}
    bad = set(d) - names - {"input", "chan"}
    if bad:
        raise ValueError(f"Unknown config key(s) for {dc.__name__}: {sorted(bad)}")
    return {k: v for k, v in d.items() if k in names and k not in ("input", "chan")}
