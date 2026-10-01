"""
Loading and preprocessing.

Turns any well-level production table into one tidy, *monthly* frame with the
canonical columns used by the rest of the package:

    Well, Date, Oil, Water, Gas, Water_Inj, Days,
    Oil_Rate, Water_Rate, Total_Liquid, Water_Cut, WOR,
    Cum_Oil, Cum_Water, Cum_Liquid, Prod_Months

`Oil`, `Water`, ... are VOLUMES per period after this step, whatever the input.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .config import Config

log = logging.getLogger(__name__)

_RATE_COLS = ["oil", "water", "gas", "water_inj"]
_CANON = {"oil": "Oil", "water": "Water", "gas": "Gas", "water_inj": "Water_Inj",
          "cum_oil": "Cum_Oil", "cum_water": "Cum_Water"}


# ----------------------------------------------------------------------------
def read_raw(cfg: Config) -> pd.DataFrame:
    path = cfg.resolve_path(cfg.input.path)
    if not path.exists():
        raise FileNotFoundError(
            f"Input file not found: {path}. Check `input.path` in your config "
            f"(paths are relative to the config file).")
    if path.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        df = pd.read_excel(path, sheet_name=cfg.input.sheet, skiprows=cfg.input.skiprows,
                           thousands=cfg.input.thousands)
    else:
        df = pd.read_csv(path, sep=cfg.input.sep, encoding=cfg.input.encoding,
                         thousands=cfg.input.thousands, skiprows=cfg.input.skiprows,
                         low_memory=False)
    df.columns = df.columns.str.strip()
    if cfg.input.query:
        n0 = len(df)
        df = df.query(cfg.input.query)
        log.info("query %r kept %d of %d rows", cfg.input.query, len(df), n0)
    return df


def _to_number(s: pd.Series) -> pd.Series:
    """Robust numeric parse. Strips thousands separators and blanks BEFORE
    coercing, so '1,166' becomes 1166 and not NaN -> 0."""
    if pd.api.types.is_numeric_dtype(s):
        return s.astype(float)
    cleaned = (s.astype("string").str.strip()
                .str.replace(",", "", regex=False)
                .str.replace(" ", "", regex=False)
                .replace({"": pd.NA}))
    out = pd.to_numeric(cleaned, errors="coerce")
    bad = s.notna() & out.isna() & (s.astype("string").str.strip() != "")
    if bad.any():
        log.warning("%d non-numeric value(s) in column %r set to NaN, e.g. %r",
                    int(bad.sum()), s.name, s[bad].iloc[0])
    return out.astype(float)


def standardise(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Rename mapped columns to canonical names and parse types."""
    cols = cfg.columns
    missing = [src for src in cols.values() if src not in df.columns]
    if missing:
        raise KeyError(f"Column(s) {missing} from config not found in input. "
                       f"Available: {list(df.columns)}")
    df = df[df[cols["well"]].notna()]                  # drop blank / total rows
    out = pd.DataFrame({"Well": df[cols["well"]].astype(str).str.strip()})
    if "date" not in cols:
        y = pd.to_numeric(df[cols["year"]], errors="coerce")
        m = pd.to_numeric(df[cols["month"]], errors="coerce")
        out["Date"] = pd.to_datetime(pd.DataFrame({"year": y, "month": m, "day": 1}),
                                     errors="coerce")
    elif cfg.input.date_format:
        out["Date"] = pd.to_datetime(df[cols["date"]], format=cfg.input.date_format,
                                     errors="coerce")
    else:
        out["Date"] = pd.to_datetime(df[cols["date"]], dayfirst=cfg.input.dayfirst,
                                     errors="coerce", format="mixed")
    nbad = int(out["Date"].isna().sum())
    if nbad:
        log.warning("%d row(s) with unparseable dates dropped", nbad)
        out = out[out["Date"].notna()]
    for key, canon in _CANON.items():
        if key in cols:
            out[canon] = _to_number(df.loc[out.index, cols[key]])
    for c in ("Oil", "Water", "Gas", "Water_Inj"):
        if c not in out:
            out[c] = 0.0
        neg = int((out[c] < 0).sum())
        if neg:
            log.warning("%d negative value(s) in %s clipped to 0", neg, c)
        out[c] = out[c].fillna(0).clip(lower=0)
    return out.sort_values(["Well", "Date"]).reset_index(drop=True)


def to_periodic(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Convert to volumes per period and (optionally) resample to monthly."""
    df = df.copy()
    has_cum = [c for c in ("Cum_Oil", "Cum_Water") if c in df]

    if cfg.values_are == "rate":
        # per-day rate -> volume over the interval each row represents
        step = df.groupby("Well")["Date"].diff().dt.days
        med = step.median() if step.notna().any() else 30.0
        if med <= 1.5:                                   # daily rows
            days = pd.Series(1.0, index=df.index)
        elif 27 <= med <= 32:                            # monthly rows
            days = df["Date"].dt.days_in_month.astype(float)
        else:                                            # irregular
            days = step.fillna(med).clip(lower=1).astype(float)
        for c in ("Oil", "Water", "Gas", "Water_Inj"):
            df[c] = df[c] * days

    input_totals = {c: float(df[c].sum()) for c in ("Oil", "Water", "Gas", "Water_Inj")}

    if cfg.resample:
        agg = {c: "sum" for c in ("Oil", "Water", "Gas", "Water_Inj")}
        agg.update({c: "last" for c in has_cum})
        parts = []
        for well, g in df.groupby("Well", sort=True):
            r = g.set_index("Date").resample(cfg.resample).agg(agg)
            r["Well"] = well
            parts.append(r.reset_index())
        df = pd.concat(parts, ignore_index=True)
        df["Days"] = df["Date"].dt.days_in_month.astype(float)
    else:
        d = df.groupby("Well")["Date"].diff().dt.days
        df["Days"] = d.fillna(d.median() if d.notna().any() else 30.44).clip(lower=1)
    df.attrs["input_totals"] = input_totals
    return df


def derive(df: pd.DataFrame) -> pd.DataFrame:
    """Water cut, WOR, cumulatives and producing time."""
    attrs = dict(df.attrs)
    df = df.sort_values(["Well", "Date"]).reset_index(drop=True)
    df["Total_Liquid"] = df["Oil"] + df["Water"]
    df["Water_Cut"] = np.where(df["Total_Liquid"] > 0, df["Water"] / df["Total_Liquid"], np.nan)
    df["WOR"] = np.where(df["Oil"] > 0, df["Water"] / df["Oil"], np.nan)
    df["Oil_Rate"] = df["Oil"] / df["Days"]
    df["Water_Rate"] = df["Water"] / df["Days"]
    df["Liquid_Rate"] = df["Total_Liquid"] / df["Days"]
    df["Water_Inj_Rate"] = df["Water_Inj"] / df["Days"]

    g = df.groupby("Well")
    if "Cum_Oil" not in df or df["Cum_Oil"].isna().all():
        df["Cum_Oil"] = g["Oil"].cumsum()
    if "Cum_Water" not in df or df["Cum_Water"].isna().all():
        df["Cum_Water"] = g["Water"].cumsum()
    df["Cum_Oil"] = g["Cum_Oil"].ffill().fillna(0)
    df["Cum_Water"] = g["Cum_Water"].ffill().fillna(0)
    df["Cum_Liquid"] = df["Cum_Oil"] + df["Cum_Water"]

    # Producing time is measured from each well's FIRST liquid production (not
    # its first record, which may be an injection or pre-production row) and
    # is offset by half a period so t > 0 for log-log (Chan) plotting.
    first = df[df["Total_Liquid"] > 0].groupby("Well")["Date"].min()
    t0 = df["Well"].map(first)
    half = df["Days"] / 2.0
    df["Prod_Months"] = ((df["Date"] - t0).dt.days + half) / 30.4375
    df.attrs.update(attrs)
    return df


def load(cfg: Config) -> pd.DataFrame:
    """Full pipeline: read -> standardise -> periodic -> derive -> drop empties."""
    raw = read_raw(cfg)
    df = standardise(raw, cfg)
    df = to_periodic(df, cfg)
    df = derive(df)
    tot = df.groupby("Well")[["Oil", "Water"]].sum()
    producers = tot[(tot["Oil"] > 0) | (tot["Water"] > 0)].index
    dropped = sorted(set(df["Well"]) - set(producers))
    if dropped:
        log.info("Wells with no oil/water production (e.g. injectors) excluded "
                 "from producer diagnostics: %s", ", ".join(dropped))
    df.attrs["injectors_only"] = dropped
    return df


def producers(df: pd.DataFrame) -> pd.DataFrame:
    """Rows for wells that produced liquid, restricted to their producing life."""
    tot = df.groupby("Well")[["Oil", "Water"]].sum()
    keep = tot[(tot["Oil"] > 0) | (tot["Water"] > 0)].index
    p = df[df["Well"].isin(keep)]
    return p[p["Prod_Months"] >= 0].reset_index(drop=True)
