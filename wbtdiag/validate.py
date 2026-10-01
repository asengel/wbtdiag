"""
Data-integrity checks run on every dataset: volume conservation through
parsing/resampling, water cut in [0, 1], monotonic cumulatives, no negative
volumes, one row per well and period.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Check:
    name: str
    passed: bool
    detail: str
    kind: str = "integrity"

    def as_dict(self):
        return {"check": self.name, "kind": self.kind, "passed": bool(self.passed),
                "detail": self.detail}


def _rel(a, b):
    return abs(a - b) / abs(b) if b else np.inf


def integrity_checks(df: pd.DataFrame) -> list[Check]:
    """`df` is the output of io.load(); input totals are read from df.attrs."""
    out = []
    tot_in = df.attrs.get("input_totals", {})
    for c in ("Oil", "Water", "Water_Inj"):
        if c not in tot_in:
            continue
        a, b = tot_in[c], df[c].sum()
        ok = np.isclose(a, b, rtol=1e-9, atol=1e-6)
        out.append(Check(f"{c} volume conserved through resampling", ok,
                         f"input {a:,.0f} vs processed {b:,.0f}"))
    wc = df["Water_Cut"].dropna()
    out.append(Check("Water cut within [0, 1]", bool(((wc >= 0) & (wc <= 1)).all()),
                     f"min {wc.min():.3f}, max {wc.max():.3f}" if len(wc) else "no data"))
    mono = df.groupby("Well")["Cum_Oil"].apply(lambda s: bool((s.diff().dropna() >= -1e-6).all()))
    out.append(Check("Cumulative oil non-decreasing in every well", bool(mono.all()),
                     "violations: " + ", ".join(mono[~mono].index) if not mono.all() else "ok"))
    last = df.sort_values("Date").groupby("Well").tail(1).set_index("Well")["Cum_Oil"]
    tot = df.groupby("Well")["Oil"].sum()
    close = np.isclose(last.reindex(tot.index), tot, rtol=1e-6)
    out.append(Check("Final cumulative oil equals sum of oil volumes", bool(close.all()),
                     "ok" if close.all() else "mismatch in " + ", ".join(tot.index[~close]),))
    neg = int((df[["Oil", "Water", "Gas", "Water_Inj"]] < 0).to_numpy().sum())
    out.append(Check("No negative volumes after cleaning", neg == 0, f"{neg} negative"))
    dup = int(df.duplicated(["Well", "Date"]).sum())
    out.append(Check("One row per well and period", dup == 0, f"{dup} duplicates"))
    return out

