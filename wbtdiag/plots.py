"""
Figures. Every public function returns a matplotlib Figure and has no side
effects, so they can be used from notebooks as well as from the CLI.
"""
from __future__ import annotations

import textwrap
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
import matplotlib.dates as mdates                     # noqa: E402
import numpy as np                                    # noqa: E402
import pandas as pd                                   # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, ListedColormap  # noqa: E402
from matplotlib.lines import Line2D                   # noqa: E402
from matplotlib.patches import Patch                  # noqa: E402

from .chan import ChanResult                          # noqa: E402
from .metrics import pct                              # noqa: E402

RED = "#C62828"; BLUE = "#1565C0"; GREEN = "#2E7D32"; ORANGE = "#E65100"
PURPLE = "#6A1B9A"; TEAL = "#00838F"; GRAY = "#9E9E9E"; LTGRAY = "#E0E0E0"
DRED = "#B71C1C"
_PALETTE = ["#1B5E20", "#0D47A1", "#BF360C", "#4A148C", "#E65100", "#006064",
            "#880E4F", "#33691E", "#1A237E", "#4E342E", "#263238", "#827717",
            "#B71C1C", "#00695C", "#AD1457", "#558B2F", "#283593", "#FF6F00"]

MECH_COLOR = {
    "Constant WOR": TEAL, "Normal displacement": GREEN, "Coning": BLUE,
    "Channeling": ORANGE, "Multilayer channeling": DRED,
    "Near-wellbore breakthrough": "#AD1457", "Transitional": GRAY,
    "Insufficient data": LTGRAY,
}

STYLE = {
    "figure.facecolor": "#FFFFFF", "axes.facecolor": "#FFFFFF",
    "axes.edgecolor": "#BDBDBD", "axes.grid": True, "grid.color": "#EEEEEE",
    "grid.linewidth": .5, "font.family": "sans-serif", "font.size": 10,
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.labelsize": 9,
    "legend.fontsize": 7, "savefig.bbox": "tight",
}
plt.rcParams.update(STYLE)


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
class WellColors:
    """Stable well -> colour mapping so a well looks the same in every figure."""
    def __init__(self, wells):
        self.map = {w: _PALETTE[i % len(_PALETTE)] for i, w in enumerate(sorted(wells))}

    def __call__(self, w):
        return self.map.get(w, GRAY)


def _empty(ax, msg="No data"):
    ax.text(.5, .5, msg, ha="center", va="center", transform=ax.transAxes, color=GRAY)


def _scatter(ax, data, xf, yf, xl, yl, title, colors: WellColors):
    v = data.dropna(subset=[xf, yf]) if len(data) else data
    if not len(v):
        _empty(ax)
    for _, r in v.iterrows():
        ax.scatter(r[xf], r[yf], color=colors(r["Well"]), s=60, edgecolors="black",
                   linewidth=.4, alpha=.85, zorder=3)
        ax.annotate(r["Well"], (r[xf], r[yf]), fontsize=7, xytext=(4, 3),
                    textcoords="offset points", alpha=.85)
    ax.set_xlabel(xl); ax.set_ylabel(yl); ax.set_title(title, fontsize=10)


def _hist(ax, data, xl, title, color=BLUE):
    data = data.dropna()
    if not len(data):
        _empty(ax); ax.set_title(title, fontsize=10); return
    ax.hist(data, bins=min(15, max(5, len(data))), color=color, alpha=.7,
            edgecolor="white", lw=.8)
    ax.axvline(data.median(), color=RED, ls="--", lw=1.5,
               label=f"Median: {data.median():,.1f}  (n={len(data)})")
    ax.set_xlabel(xl); ax.set_ylabel("Wells"); ax.set_title(title, fontsize=10)
    ax.legend(fontsize=7)


def _barh_by_well(ax, m, col, title, color, unit):
    v = m.dropna(subset=[col]).sort_values(col) if col in m else m.iloc[0:0]
    if not len(v):
        _empty(ax); ax.set_title(title, fontsize=10); return
    y = np.arange(len(v))
    ax.barh(y, v[col], color=color, edgecolor="white", height=.7, alpha=.85)
    ax.set_yticks(y); ax.set_yticklabels(v["Well"], fontsize=8)
    ax.set_xlabel(f"Cumulative oil ({unit})"); ax.set_title(title, fontsize=10)
    xmax = v[col].max()
    for i, val in enumerate(v[col]):
        ax.text(val + xmax * .01, i, f"{val:,.0f}", va="center", fontsize=7)
    ax.set_xlim(0, xmax * 1.18)


def _suptitle(fig, text, sub=None):
    fig.suptitle(text if not sub else f"{text}\n{sub}", fontsize=13 if not sub else 12,
                 fontweight="bold")


def _field_series(df):
    f = df.groupby("Date")[["Oil", "Water", "Water_Inj", "Days"]].agg(
        {"Oil": "sum", "Water": "sum", "Water_Inj": "sum", "Days": "first"})
    f = f.reset_index().sort_values("Date")
    tot = f["Oil"] + f["Water"]
    f["WC"] = np.where(tot > 0, f["Water"] / tot * 100, np.nan)
    for c in ("Oil", "Water", "Water_Inj"):
        f[c + "_Rate"] = f[c] / f["Days"]
    return f


# ----------------------------------------------------------------------------
# field-level
# ----------------------------------------------------------------------------
def field_overview(df, unit="Sm3"):
    f = _field_series(df)
    has_inj = f["Water_Inj"].sum() > 0
    fig, axes = plt.subplots(1, 3 if has_inj else 2, figsize=(18 if has_inj else 15, 5))
    ax = axes[0]
    for c, col, lab in (("Oil_Rate", GREEN, "Oil"), ("Water_Rate", BLUE, "Water")):
        ax.fill_between(f["Date"], 0, f[c], alpha=.2, color=col)
        ax.plot(f["Date"], f[c], color=col, lw=1.2, label=lab)
    ax.set_ylabel(f"Rate ({unit}/d, calendar-day)"); ax.set_title("Field production rates")
    ax.legend(fontsize=8)
    ax = axes[1]
    ax.plot(f["Date"], f["WC"], color=BLUE, lw=1.8)
    ax.fill_between(f["Date"], 0, f["WC"], alpha=.12, color=BLUE)
    ax.set_ylim(0, 100); ax.set_ylabel("Water cut (%)"); ax.set_title("Field water cut")
    ax.axhline(50, ls=":", color=GRAY, lw=.8); ax.axhline(90, ls=":", color=RED, lw=.8)
    if has_inj:
        ax = axes[2]
        ax.plot(f["Date"], f["Water_Inj_Rate"], color=PURPLE, lw=1.2, label="Water injected")
        ax.plot(f["Date"], f["Oil_Rate"] + f["Water_Rate"], color="#555", lw=1.2,
                label="Liquid produced")
        ax.set_ylabel(f"Rate ({unit}/d)"); ax.set_title("Injection vs. liquid production")
        ax.legend(fontsize=8)
    _suptitle(fig, "FIELD OVERVIEW")
    fig.tight_layout(rect=[0, 0, 1, .94])
    return fig


def hist_timing(m, th, unit="Sm3"):
    p1, p2, p3 = map(pct, th)
    fig, axes = plt.subplots(2, 3, figsize=(17, 9))
    _hist(axes[0, 0], m["Prod_Months"], "Months", "Months on production", TEAL)
    _hist(axes[0, 1], m["Cum_Oil"], unit, "Cumulative oil", GREEN)
    _hist(axes[0, 2], m["WC_Final"] * 100, "WC (%)", "Final water cut", BLUE)
    _hist(axes[1, 0], m[f"BT_{p1}"], "Months", f"Time to {p1}% WC", GREEN)
    _hist(axes[1, 1], m[f"BT_{p2}"], "Months", f"Time to {p2}% WC", ORANGE)
    _hist(axes[1, 2], m[f"BT_{p3}"], "Months", f"Time to {p3}% WC", RED)
    _suptitle(fig, "FIELD HISTOGRAMS — timing & volumes")
    fig.tight_layout(rect=[0, 0, 1, .94])
    return fig


def hist_wcr(m, th):
    p1, p2, p3 = map(pct, th)
    fig, axes = plt.subplots(1, 3, figsize=(17, 5))
    _hist(axes[0], m[f"WCR_0_{p1}"], "%/month", f"Avg WC rise: 0→{p1}%", GREEN)
    _hist(axes[1], m[f"WCR_{p1}_{p2}"], "%/month", f"Avg WC rise: {p1}→{p2}%", ORANGE)
    _hist(axes[2], m[f"WCR_{p2}_{p3}"], "%/month", f"Avg WC rise: {p2}→{p3}%", RED)
    _suptitle(fig, "WATER-CUT RISE RATE — by WC interval")
    fig.tight_layout(rect=[0, 0, 1, .92])
    return fig


def bt_bars(m, th, unit="Sm3"):
    p1, p2, p3 = map(pct, th)
    fig, axes = plt.subplots(1, 3, figsize=(17, max(4.5, len(m) * .45)))
    _barh_by_well(axes[0], m, f"CumOil_{p1}", f"Cum oil at {p1}% WC", GREEN, unit)
    _barh_by_well(axes[1], m, f"CumOil_{p2}", f"Cum oil at {p2}% WC", ORANGE, unit)
    _barh_by_well(axes[2], m, f"CumOil_{p3}", f"Cum oil at {p3}% WC", RED, unit)
    _suptitle(fig, "CUMULATIVE OIL AT WC THRESHOLDS")
    fig.tight_layout(rect=[0, 0, 1, .92])
    return fig


def bt_grouped(m, th, unit="Sm3"):
    p1, p2, p3 = map(pct, th)
    fig, ax = plt.subplots(figsize=(13, max(4.5, len(m) * .55)))
    v = m.dropna(subset=[f"CumOil_{p1}"]).sort_values(f"CumOil_{p1}")
    if not len(v):
        _empty(ax); return fig
    y = np.arange(len(v)); bw = .26
    for off, p, col in ((-bw, p1, GREEN), (0, p2, ORANGE), (bw, p3, RED)):
        ax.barh(y + off, v[f"CumOil_{p}"].fillna(0), height=bw, color=col,
                edgecolor="white", label=f"At {p}% WC")
    ax.barh(y, v["Cum_Oil"], height=bw * 3.2, color="none",
            edgecolor="#424242", lw=.8, ls="--", label="Current cum oil")
    ax.set_yticks(y); ax.set_yticklabels(v["Well"], fontsize=9); ax.legend(fontsize=8)
    ax.set_xlabel(f"Cumulative oil ({unit})")
    ax.set_title(f"Cum oil at {p1}% / {p2}% / {p3}% WC vs. current cum oil")
    fig.tight_layout()
    return fig


def dwor_vs_cumoil(m, th, colors, unit="Sm3"):
    p1, p2, p3 = map(pct, th)
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.5))
    for ax, (a, b) in zip(axes, (("0", p1), (p1, p2), (p2, p3))):
        _scatter(ax, m, f"CumOil_{b}", f"DWOR_{a}_{b}", f"Cum oil at {b}% WC ({unit})",
                 f"ΔWOR / month ({a}→{b}%)", f"ΔWOR per month: {a}→{b}% WC", colors)
        ax.axhline(0, color=LTGRAY, lw=.8)
    _suptitle(fig, "WOR GROWTH RATE vs. CUM OIL — by WC interval")
    fig.tight_layout(rect=[0, 0, 1, .92])
    return fig


def wcr_vs_bt(m, th, colors):
    p1, p2, p3 = map(pct, th)
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.5))
    for ax, (a, b) in zip(axes, (("0", p1), (p1, p2), (p2, p3))):
        _scatter(ax, m, f"BT_{b}", f"WCR_{a}_{b}", f"Months to {b}% WC",
                 f"WC rise (%/mo, {a}→{b}%)", f"WC rise rate vs timing: {a}→{b}%", colors)
    _suptitle(fig, "WC RISE RATE vs. TIMING",
              "Upper-left in each panel = earliest and fastest water: worst behaviour for that stage")
    fig.tight_layout(rect=[0, 0, 1, .90])
    return fig


def recovery_crossplots(m, th, colors, unit="Sm3"):
    p1, p2, p3 = map(pct, th)
    fig, axes = plt.subplots(2, 3, figsize=(17, 10))
    for ax, (a, b) in zip(axes[0], ((p2, p1), (p3, p1), (p3, p2))):
        _scatter(ax, m, "Cum_Oil", f"RR_{a}_{b}", f"Cum oil ({unit})",
                 f"CumOil@{a}% / CumOil@{b}%", f"Recovery ratio {a}% / {b}% WC", colors)
    for ax, (a, b) in zip(axes[1], ((p1, p2), (p2, p3), (p1, p3))):
        _scatter(ax, m, f"BT_{a}", f"BT_{b}", f"Months to {a}% WC", f"Months to {b}% WC",
                 f"Time to {b}% vs time to {a}% WC", colors)
        v = m[[f"BT_{a}", f"BT_{b}"]].dropna()
        if len(v) > 1:
            lim = max(v.max().max() * 1.1, 1)
            ax.plot([0, lim], [0, lim], "--", color=LTGRAY, lw=.9, zorder=1)
    _suptitle(fig, "RECOVERY RATIOS & BREAKTHROUGH-TIME CROSSPLOTS")
    fig.tight_layout(rect=[0, 0, 1, .94])
    return fig


def additional_crossplots(m, colors, unit="Sm3"):
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.5))
    _scatter(axes[0], m, "Cum_Oil", "XFw_Last", f"Cum oil ({unit})",
             "X(fw) = 1/fw + ln[fw/(1-fw)]", "Ershaghi X(fw) vs cum oil", colors)
    m2 = m.assign(WC_Pct=m["WC_Final"] * 100)
    _scatter(axes[1], m2, "Cum_Oil", "WC_Pct", f"Cum oil ({unit})", "Final WC (%)",
             "Final WC vs cum oil", colors)
    _scatter(axes[2], m, "Cum_Oil", "WOR_Slope_CumOil", f"Cum oil ({unit})",
             f"d log10(WOR) / dNp  (1/{unit})", "WOR steepness vs cum oil", colors)
    axes[2].axhline(0, color=LTGRAY, lw=.8)
    _suptitle(fig, "ADDITIONAL DIAGNOSTIC CROSSPLOTS")
    fig.tight_layout(rect=[0, 0, 1, .92])
    return fig


def wor_vs_cumoil(df, colors, unit="Sm3"):
    fig, ax = plt.subplots(figsize=(11, 7))
    for w, g in df[df["Total_Liquid"] > 0].groupby("Well"):
        g = g[g["WOR"] > 0].sort_values("Date")
        if len(g) < 2:
            continue
        ax.semilogy(g["Cum_Oil"], g["WOR"], color=colors(w), lw=1.2, alpha=.8)
        ax.annotate(w, (g["Cum_Oil"].iloc[-1], g["WOR"].iloc[-1]), fontsize=7,
                    color=colors(w), xytext=(4, 4), textcoords="offset points")
    for y, c, lab in ((1, GRAY, "WOR 1 (50% WC)"), (9, ORANGE, "WOR 9 (90%)"),
                      (49, RED, "WOR 49 (98%)")):
        ax.axhline(y, color=c, ls=":", lw=.9)
        ax.text(0.995, y, f"{lab} ", color=c, fontsize=7, ha="right",
                va="bottom", transform=ax.get_yaxis_transform())
    ax.set_xlabel(f"Cumulative oil, Np ({unit})"); ax.set_ylabel("WOR (log)")
    ax.set_title("WOR vs cumulative oil — all wells")
    fig.tight_layout()
    return fig


def ershaghi_xplot(df, colors, unit="Sm3"):
    fig, ax = plt.subplots(figsize=(11, 7))
    n = 0
    for w, g in df[df["Total_Liquid"] > 0].groupby("Well"):
        g = g.sort_values("Date")
        xd = g[(g["Water_Cut"] > .50) & (g["Water_Cut"] < .995)]
        if len(xd) < 3:
            continue
        fw = xd["Water_Cut"].to_numpy(); Np = xd["Cum_Oil"].to_numpy()
        X = 1. / fw + np.log(fw / (1. - fw))
        ok = np.isfinite(X) & (Np > 0)
        if ok.sum() < 3:
            continue
        ax.plot(Np[ok], X[ok], "o-", ms=2.5, color=colors(w), lw=1, alpha=.8)
        ax.annotate(w, (Np[ok][-1], X[ok][-1]), fontsize=7, color=colors(w),
                    xytext=(4, 4), textcoords="offset points")
        n += 1
    if not n:
        _empty(ax, "No well exceeded 50% WC")
    ax.set_xlabel(f"Cumulative oil, Np ({unit})")
    ax.set_ylabel("X(fw) = 1/fw + ln[fw/(1-fw)]")
    ax.set_title("Ershaghi–Abdou X-plot (fw > 0.5) — straight line ⇒ Buckley-Leverett-like displacement")
    fig.tight_layout()
    return fig


def wc_vs_cumoil(df, colors, unit="Sm3"):
    fig, ax = plt.subplots(figsize=(11, 7))
    for w, g in df[df["Total_Liquid"] > 0].groupby("Well"):
        g = g.sort_values("Date")
        if len(g) < 2:
            continue
        ax.plot(g["Cum_Oil"], g["Water_Cut"] * 100, color=colors(w), lw=1.2, alpha=.8)
        ax.annotate(w, (g["Cum_Oil"].iloc[-1], g["Water_Cut"].iloc[-1] * 100), fontsize=7,
                    color=colors(w), xytext=(4, 4), textcoords="offset points")
    ax.axhline(50, ls=":", color=GRAY, lw=.8); ax.axhline(90, ls=":", color=RED, lw=.8)
    ax.set_xlabel(f"Cumulative oil ({unit})"); ax.set_ylabel("Water cut (%)")
    ax.set_ylim(-2, 102); ax.set_title("Water cut vs cumulative oil — all wells")
    fig.tight_layout()
    return fig


def wc_heatmap(df):
    """Monthly WC per well; gray = shut in during the well's producing life."""
    wells = sorted(df["Well"].unique())
    months = pd.date_range(df["Date"].min().to_period("M").to_timestamp(),
                           df["Date"].max(), freq="MS")
    wc = np.full((len(wells), len(months)), np.nan)
    shut = np.zeros_like(wc, dtype=bool)
    for i, w in enumerate(wells):
        g = df[df["Well"] == w].copy()
        g["M"] = g["Date"].dt.to_period("M").dt.to_timestamp()
        mon = g.groupby("M").agg(O=("Oil", "sum"), W=("Water", "sum"))
        live = mon[(mon["O"] + mon["W"]) > 0]
        if not len(live):
            continue
        a, b = live.index.min(), live.index.max()
        for j, mth in enumerate(months):
            if mth < a or mth > b:
                continue
            if mth in live.index:
                r = live.loc[mth]; wc[i, j] = r["W"] / (r["O"] + r["W"])
            else:
                shut[i, j] = True
    fig, ax = plt.subplots(figsize=(max(12, len(months) * .09), max(3.5, len(wells) * .5)))
    cmap = LinearSegmentedColormap.from_list("wc", ["#E3F2FD", "#64B5F6", "#1565C0",
                                                    "#E65100", "#B71C1C"])
    cmap.set_bad("white")
    im = ax.imshow(np.ma.masked_invalid(wc), aspect="auto", cmap=cmap, vmin=0, vmax=1,
                   interpolation="nearest")
    ax.imshow(np.ma.masked_where(~shut, shut.astype(float)), aspect="auto",
              cmap=ListedColormap(["#9E9E9E"]), vmin=0, vmax=1, interpolation="nearest")
    ax.set_yticks(range(len(wells))); ax.set_yticklabels(wells, fontsize=8)
    step = max(1, len(months) // 16)
    ax.set_xticks(range(0, len(months), step))
    ax.set_xticklabels([mm.strftime("%Y-%m") for mm in months[::step]], fontsize=7,
                       rotation=45, ha="right")
    ax.grid(False)
    ax.legend(handles=[Patch(facecolor="#9E9E9E", label="Shut in (within producing life)"),
                       Patch(facecolor="white", edgecolor="#BDBDBD",
                             label="Before / after producing life")],
              loc="upper left", bbox_to_anchor=(0, -0.28), ncol=2, fontsize=7, frameon=False)
    fig.colorbar(im, ax=ax, label="Water cut (fraction)", shrink=.85, pad=.01)
    ax.set_title("Monthly water-cut heatmap — all wells")
    fig.tight_layout()
    return fig


# ----------------------------------------------------------------------------
# Chan
# ----------------------------------------------------------------------------
def mechanism_summary(results: dict[str, ChanResult], win: int = 7):
    labels = [r.current for r in results.values()]
    if not labels:
        fig, ax = plt.subplots(); _empty(ax); return fig
    cnt = Counter(labels)
    order = sorted(cnt.items(), key=lambda kv: kv[1])
    names = [k for k, _ in order]; vals = [v for _, v in order]
    nmulti = sum(r.multi_pattern for r in results.values())
    fig, ax = plt.subplots(figsize=(12, max(3.5, len(names) * .8 + 1.5)))
    y = np.arange(len(names))
    ax.barh(y, vals, color=[MECH_COLOR.get(k, GRAY) for k in names], edgecolor="white",
            alpha=.9, height=.65)
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=10)
    for i, v in enumerate(vals):
        ax.text(v + max(vals) * .01, i, str(v), va="center", fontsize=9)
    ax.set_xlabel("Number of wells"); ax.set_xlim(0, max(vals) * 1.2)
    ax.xaxis.get_major_locator().set_params(integer=True)
    ax.set_title("Chan diagnostic — CURRENT (latest) mechanism per well")
    fig.text(.99, .01,
             f"Rolling-window read of the WOR' slope (Chan, SPE 30775; window = {win} points). "
             f"WOR' increasing with time → channeling, decreasing → coning.\n"
             f"{nmulti} of {len(labels)} wells passed through more than one mechanism "
             f"(see the timeline). Screening only — confirm with logs, PLT, well tests and PTA.",
             ha="right", va="bottom", fontsize=7.5, style="italic", color="#666")
    fig.tight_layout(rect=[0, .08, 1, 1])
    return fig


def chan_timeline(results: dict[str, ChanResult]):
    """Gantt-style view of every well's mechanism sequence (months on production)."""
    wells = [w for w, r in sorted(results.items()) if r.segments]
    fig, ax = plt.subplots(figsize=(14, max(3, len(wells) * .55 + 1.5)))
    if not wells:
        _empty(ax, "No wells with enough WOR data"); return fig
    used = []
    for i, w in enumerate(wells):
        segs = results[w].segments
        step = np.median(np.diff(results[w].t)) if len(results[w].t) > 1 else 1.0
        for k, (lab, a, b, _) in enumerate(segs):
            # draw each segment up to the start of the next one (no gaps)
            end = segs[k + 1][1] if k + 1 < len(segs) else b + step
            left = a - step / 2 if k == 0 else a
            ax.barh(i, end - left, left=left, color=MECH_COLOR.get(lab, GRAY),
                    edgecolor="white", linewidth=.5, height=.6)
            used.append(lab)
        dep = results[w].departure_mo
        if np.isfinite(dep):
            ax.plot(dep, i, marker="v", color="black", ms=6, zorder=4)
    ax.set_yticks(range(len(wells))); ax.set_yticklabels(wells, fontsize=9)
    ax.invert_yaxis(); ax.set_xlabel("Months on production")
    h = [Patch(color=MECH_COLOR[k], label=k) for k in MECH_COLOR if k in used]
    h.append(Line2D([], [], marker="v", ls="", color="black", label="WOR departure"))
    ax.legend(handles=h, loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8)
    ax.set_title("Chan mechanism timeline — all wells")
    fig.tight_layout()
    return fig


def smooth_log(x, y, win=9):
    """Centred rolling mean of log10(y): a trend line for noisy positive data
    plotted on log axes. Returns None when there are too few points."""
    y = np.asarray(y, float)
    if len(y) < 5:
        return None
    w = min(win, len(y) if len(y) % 2 else len(y) - 1)
    ly = pd.Series(np.log10(y)).rolling(w, center=True, min_periods=max(2, w // 2)).mean()
    return 10 ** ly.to_numpy()


def chan_well(df_well, r: ChanResult, mrow=None, unit="Sm3", date_range=None):
    """Per-well figure: Chan log-log diagnostic (top) + production history (bottom)."""
    well = r.well
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(10.5, 10), gridspec_kw={"height_ratios": [1.15, 1]})

    if len(r.t) >= 2:
        t, wor, tm, dw = r.t, r.wor_raw, r.tm, r.dw
        labels = r.labels if len(r.labels) == len(t) else None
        if labels is not None:
            for mech in dict.fromkeys(labels):
                s = labels == mech
                ax.loglog(t[s], wor[s], "o", ms=4.2, alpha=.8, color=MECH_COLOR.get(mech, GRAY),
                          markeredgewidth=0, zorder=2)
        else:
            ax.loglog(t, wor, "o", color=RED, ms=4, alpha=.5)
        ax.loglog(t, r.wor_s, "-", color="#424242", lw=1.5, alpha=.8, zorder=3)
        # WOR' shown as one series (magnitude, since log axes cannot show sign)
        aw = np.abs(dw); ok = aw > 0
        ax.loglog(tm[ok], aw[ok], "^", color=BLUE, ms=3.5, alpha=.45, markeredgewidth=0,
                  zorder=2)
        wsm = smooth_log(tm[ok], aw[ok])
        if wsm is not None:
            ax.loglog(tm[ok], wsm, "-", color=BLUE, lw=1.8, alpha=.9, zorder=3)
        if np.isfinite(r.departure_mo) and r.departure_mo > 0:
            ax.axvline(r.departure_mo, ls="--", color="#999", lw=1, zorder=1)
        hs = [Line2D([], [], marker="o", ls="", ms=6, color=MECH_COLOR.get(k, GRAY), label=k)
              for k in (dict.fromkeys(labels) if labels is not None else [])]
        hs += [Line2D([], [], color="#424242", lw=1.5, label="WOR (smoothed)"),
               Line2D([], [], marker="^", ls="", color=BLUE, alpha=.6, label="WOR'"),
               Line2D([], [], color=BLUE, lw=1.8, label="WOR' (smoothed)")]
        ax.legend(handles=hs, loc="upper left", fontsize=7, framealpha=.9)
        if r.segments:
            txt = "\n".join(textwrap.wrap("Sequence: " + r.sequence_str, width=62))
            ax.text(.98, .03, txt, transform=ax.transAxes, fontsize=6.8, ha="right",
                    va="bottom", color="#333",
                    bbox=dict(boxstyle="round,pad=.4", fc="#FFFDE7",
                              ec=MECH_COLOR.get(r.current, GRAY), lw=1.2, alpha=.95))
        vals = np.concatenate([wor[wor > 0], np.abs(dw[dw != 0])])
        if len(vals):
            lo = 10 ** np.floor(np.log10(max(np.nanmin(vals), 1e-7)))
            hi = 10 ** np.ceil(np.log10(np.nanmax(vals)) + .3)
            ax.set_ylim(lo, hi)
        ax.set_xlim(10 ** np.floor(np.log10(max(t.min(), .1))),
                    10 ** np.ceil(np.log10(t.max())))
    else:
        _empty(ax, "Insufficient WOR data")
        ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Time on production (months)"); ax.set_ylabel("WOR  and  WOR' (1/month)")
    cur = r.current
    ax.set_title(f"Chan diagnostic — {well}" + (f"   [current: {cur}]" if cur != "Insufficient data" else ""),
                 color=MECH_COLOR.get(cur, "#222") if cur != "Insufficient data" else "#222")

    g = df_well.sort_values("Date")
    ax2.plot(g["Date"], g["Oil_Rate"], color=GREEN, lw=1.2, label="Oil")
    ax2.fill_between(g["Date"], 0, g["Oil_Rate"], alpha=.15, color=GREEN)
    ax2.plot(g["Date"], g["Water_Rate"], color=BLUE, lw=1.2, label="Water")
    ax2.fill_between(g["Date"], 0, g["Water_Rate"], alpha=.15, color=BLUE)
    ax2.set_ylabel(f"Rate ({unit}/d, calendar-day)"); ax2.set_title(f"Production — {well}")
    if date_range is not None:
        ax2.set_xlim(*date_range)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax3 = ax2.twinx()
    ax3.plot(g["Date"], g["Water_Cut"] * 100, "--", color=RED, lw=1.2, alpha=.8, label="WC %")
    ax3.set_ylabel("Water cut (%)", color=RED); ax3.set_ylim(-2, 102)
    ax3.tick_params(axis="y", labelcolor=RED); ax3.grid(False)
    h2, l2 = ax2.get_legend_handles_labels(); h3, l3 = ax3.get_legend_handles_labels()
    ax2.legend(h2 + h3, l2 + l3, loc="upper right", fontsize=7)
    if mrow is not None:
        ax2.text(.02, .97, f"Cum oil: {mrow['Cum_Oil']:,.0f} {unit}\n"
                           f"Final WC: {mrow['WC_Final'] * 100:.0f}%",
                 transform=ax2.transAxes, fontsize=8, va="top", family="monospace",
                 bbox=dict(boxstyle="round,pad=.3", fc="white", ec=LTGRAY, alpha=.9))
    fig.tight_layout()
    return fig
