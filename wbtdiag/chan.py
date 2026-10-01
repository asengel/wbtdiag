"""
Chan diagnostic interpretation (after K.S. Chan, SPE 30775, 1995).

Core rule: on a log-log plot of WOR and its time derivative WOR' = d(WOR)/dt
vs time, the TREND of WOR' separates the mechanisms

    WOR' INCREASING with time (positive log-log slope) -> channeling
                                       (high-perm layer / thief zone / fracture)
    WOR' DECREASING with time (negative log-log slope) -> bottom-water coning

In this classifier, a rising-WOR phase is labelled coning when the WOR'
log-log slope is below `worp_slope_neg` (-0.15), channeling when it is above
`worp_steep` (1.0), and normal displacement in between.

A well normally passes through several regimes over its life, so a single
label per well is misleading.

Caveat from the literature: the classes overlap (sub-linear normal
displacement and coning both give a falling WOR'), so this is a SCREEN;
confirm with logs, production logging, well tests and PTA.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

from .config import ChanParams

MECHANISMS = [
    "Constant WOR", "Normal displacement", "Coning", "Channeling",
    "Multilayer channeling", "Near-wellbore breakthrough", "Transitional",
    "Insufficient data",
]
_NOT_MECH = ("Insufficient data", "Transitional", "Constant WOR")


@dataclass
class ChanResult:
    well: str
    t: np.ndarray = field(default_factory=lambda: np.array([]))
    wor_raw: np.ndarray = field(default_factory=lambda: np.array([]))
    wor_s: np.ndarray = field(default_factory=lambda: np.array([]))
    tm: np.ndarray = field(default_factory=lambda: np.array([]))
    dw: np.ndarray = field(default_factory=lambda: np.array([]))
    labels: np.ndarray = field(default_factory=lambda: np.array([], dtype=object))
    segments: list = field(default_factory=list)   # (label, t0, t1, n_pts)
    current: str = "Insufficient data"
    dominant: str = "Insufficient data"
    departure_mo: float = np.nan
    wor_slope: float = np.nan
    worp_slope: float = np.nan
    worp_peak: float = np.nan
    multi_pattern: bool = False
    notes: str = ""

    @property
    def sequence_str(self) -> str:
        return "  ->  ".join(f"{lab} ({a:.0f}-{b:.0f} mo)" for lab, a, b, _ in self.segments)

    def summary(self) -> dict:
        return {"Well": self.well, "Chan_Current": self.current,
                "Chan_Dominant": self.dominant, "Chan_Sequence": self.sequence_str,
                "Chan_MultiPattern": self.multi_pattern,
                "Chan_Departure_Mo": self.departure_mo,
                "Chan_WOR_Slope": self.wor_slope, "Chan_WORp_Slope": self.worp_slope,
                "Chan_WORp_Peak": self.worp_peak, "Chan_Notes": self.notes}


# ----------------------------------------------------------------------------
# numerical helpers
# ----------------------------------------------------------------------------
def ll_slope(x, y) -> float:
    """Slope of log10(y) vs log10(x); NaN if fewer than 3 valid points."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    v = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
    if v.sum() < 3:
        return np.nan
    return float(np.polyfit(np.log10(x[v]), np.log10(y[v]), 1)[0])


def rolling_ll_slope(x, y, win: int, min_log_span: float = 0.0) -> np.ndarray:
    """Centred rolling log-log slope; leading/trailing NaNs edge-filled.

    With ``min_log_span > 0`` the window is widened (symmetrically) until it
    covers at least that many decades of x. A fixed point count spans ever
    fewer decades at late time (7 months at t=90 mo is only 0.03 decades), which
    makes the slope very sensitive to noise; a log-span floor keeps the
    resolution roughly constant on the log-log plot."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    n = len(x); s = np.full(n, np.nan)
    lx = np.where(x > 0, np.log10(np.where(x > 0, x, 1.0)), np.nan)
    ly = np.where(y > 0, np.log10(np.where(y > 0, y, 1.0)), np.nan)
    h0 = win // 2
    for i in range(n):
        h = h0
        lo, hi = max(0, i - h), min(n, i + h + 1)
        while (min_log_span > 0 and (lo > 0 or hi < n)
               and np.nanmax(lx[lo:hi]) - np.nanmin(lx[lo:hi]) < min_log_span):
            h += 1
            lo, hi = max(0, i - h), min(n, i + h + 1)
        xx, yy = lx[lo:hi], ly[lo:hi]
        v = np.isfinite(xx) & np.isfinite(yy)
        if v.sum() >= 3:
            s[i] = np.polyfit(xx[v], yy[v], 1)[0]
    idx = np.where(np.isfinite(s))[0]
    if len(idx):
        s[:idx[0]] = s[idx[0]]; s[idx[-1] + 1:] = s[idx[-1]]
    return s


def rle_merge(arr, min_len: int):
    """Run-length encode, absorb runs shorter than min_len into the previous
    run, then re-merge identical neighbours -> [[value, i0, i1], ...]."""
    n = len(arr); rle = []; i = 0
    while i < n:
        j = i
        while j < n and arr[j] == arr[i]:
            j += 1
        rle.append([arr[i], i, j - 1]); i = j
    merged = []
    for v, a, b in rle:
        if merged and (b - a + 1) < min_len:
            merged[-1][2] = b
        else:
            merged.append([v, a, b])
    out = []
    for v, a, b in merged:
        if out and out[-1][0] == v:
            out[-1][2] = b
        else:
            out.append([v, a, b])
    return out


# ----------------------------------------------------------------------------
# WOR derivative
# ----------------------------------------------------------------------------
def wor_derivative(g: pd.DataFrame):
    """Return (t, wor_raw, wor_smoothed, t_mid, dWOR/dt) for producing periods
    with WOR > 0, or None when there are fewer than 6 points."""
    gv = g[(g["Total_Liquid"] > 0) & g["WOR"].notna() & (g["WOR"] > 0)]
    gv = gv.sort_values("Prod_Months")
    if len(gv) < 6:
        return None
    t = gv["Prod_Months"].to_numpy(float)
    wor = gv["WOR"].to_numpy(float)
    if len(wor) >= 7:
        win = min(7, len(wor) // 2 * 2 + 1)
        ws = np.exp(savgol_filter(np.log(wor), win, 2))    # smooth in log space
    else:
        ws = wor.copy()
    dt = np.diff(t); dt = np.where(dt == 0, 0.01, dt)
    dw = np.diff(ws) / dt
    tm = (t[:-1] + t[1:]) / 2
    return t, wor, ws, tm, dw


# ----------------------------------------------------------------------------
# classifier
# ----------------------------------------------------------------------------
def classify_well(g: pd.DataFrame, well: str = "", p: ChanParams | None = None) -> ChanResult:
    """Phase-based Chan classification for one well's monthly data."""
    p = p or ChanParams()
    res = ChanResult(well=well, notes=f"Fewer than {p.min_points} WOR points.")
    d = wor_derivative(g)
    if d is None:
        return res
    t, wr, ws, tm, dw = d
    res.t, res.wor_raw, res.wor_s, res.tm, res.dw = t, wr, ws, tm, dw
    n = len(ws)
    if n < p.min_points:
        res.labels = np.array(["Insufficient data"] * n, dtype=object)
        return res
    worp = np.interp(t, tm, dw)

    base = np.nanmedian(ws[:max(3, n // 5)])
    dep_level = max(1e-2, base * p.departure_factor)
    sW = rolling_ll_slope(t, ws, p.win, p.min_log_span)

    # sustained near-wellbore jumps on RAW WOR (>=1 decade within a few months
    # that stays elevated, e.g. casing leak / cement failure)
    near = np.zeros(n, bool)
    dj = np.diff(np.log10(np.clip(wr, 1e-12, None))); dtm = np.diff(t)
    jumps = (dj >= p.nearwell_decade) & (dtm <= p.nearwell_dt) & (wr[1:] >= p.nearwell_min_wor)
    for k in np.where(jumps)[0]:
        kk = min(k + 3, n - 1)
        if wr[kk] >= 0.5 * wr[k + 1]:
            lvl = 0.5 * wr[k + 1]; j = k + 1
            while j < n and wr[j] >= lvl:
                near[j] = True; j += 1

    # coarse phases by the stable rolling WOR slope
    ptype = np.where(sW >= p.const_slope, "rise", "flat")
    phases = rle_merge(list(ptype), p.min_seg)

    def phase_trend(i0, i1):
        wp = worp[i0:i1 + 1]; m = np.isfinite(wp) & (wp > 0)
        return ll_slope(t[i0:i1 + 1][m], wp[m]) if m.sum() >= 3 else np.nan

    # pass 1: Chan's WOR'-slope rule applied once per phase
    pl = []
    for typ, i0, i1 in phases:
        high = np.nanmedian(ws[i0:i1 + 1]) > dep_level
        tr = phase_trend(i0, i1)
        if typ == "flat":
            pl.append("Constant WOR" if not high else ("FLATHIGH", tr))
        elif np.isfinite(tr) and tr < p.worp_slope_neg:
            pl.append("Coning")
        elif np.isfinite(tr) and tr > p.worp_steep:
            pl.append("Channeling")
        else:
            pl.append("Normal displacement")

    # pass 2: resolve high plateaus from the preceding mechanism
    for i, lab in enumerate(pl):
        if isinstance(lab, tuple):
            prev = pl[i - 1] if i > 0 else None; tr = lab[1]
            if prev in ("Channeling", "Multilayer channeling"):
                pl[i] = prev                       # post-breakthrough plateau
            elif prev == "Coning" or (np.isfinite(tr) and tr < p.worp_slope_neg):
                pl[i] = "Coning"                   # stabilised cone
            else:
                pl[i] = "Transitional"

    # multilayer: two or more separate channeling RISES
    nrise = sum(1 for (typ, _, _), lab in zip(phases, pl) if typ == "rise" and lab == "Channeling")
    if nrise >= 2:
        pl = ["Multilayer channeling" if x == "Channeling" else x for x in pl]

    labels = np.empty(n, dtype=object)
    for (_, i0, i1), lab in zip(phases, pl):
        labels[i0:i1 + 1] = lab
    labels[near] = "Near-wellbore breakthrough"
    res.labels = labels
    res.segments = [(v, float(t[a]), float(t[b]), b - a + 1)
                    for v, a, b in rle_merge(list(labels), 1)]

    above = np.where(ws > base * p.departure_factor)[0] if base > 0 else []
    res.departure_mo = float(t[above[0]]) if len(above) else np.nan

    real = [s for s in res.segments if s[0] not in _NOT_MECH]
    if real:
        res.current = real[-1][0]
        res.dominant = max(real, key=lambda s: s[3])[0]
    elif res.segments:
        res.current = res.dominant = res.segments[-1][0]
    res.multi_pattern = len({s[0] for s in real}) >= 2

    res.wor_slope = ll_slope(t, ws)
    pos = dw > 0
    res.worp_slope = ll_slope(tm[pos], dw[pos])
    res.worp_peak = float(np.nanmax(dw)) if len(dw) else np.nan
    res.notes = (f"current={res.current}; dominant={res.dominant}; "
                 f"{len(res.segments)} segment(s); WOR' slope={res.worp_slope:+.2f}")
    return res


def classify_all(df: pd.DataFrame, p: ChanParams | None = None) -> dict[str, ChanResult]:
    return {w: classify_well(g, w, p) for w, g in df.groupby("Well", sort=True)}


def segments_table(results: dict[str, ChanResult]) -> pd.DataFrame:
    """Tidy one-row-per-segment table (good for BI tools / further analysis)."""
    rows = []
    for w, r in results.items():
        for i, (lab, a, b, n) in enumerate(r.segments):
            rows.append({"Well": w, "Segment": i + 1, "Mechanism": lab,
                         "Start_Mo": round(a, 2), "End_Mo": round(b, 2), "N_Points": n})
    return pd.DataFrame(rows, columns=["Well", "Segment", "Mechanism",
                                       "Start_Mo", "End_Mo", "N_Points"])
