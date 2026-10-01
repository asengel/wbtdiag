"""
Per-well water-production metrics (breakthrough timing, WC rise rates, WOR
growth, recovery ratios, Ershaghi X(fw)).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def pct(th: float) -> str:
    """0.05 -> '5', 0.5 -> '50'."""
    return f"{th * 100:g}"


def _at_threshold(g: pd.DataFrame, th: float):
    """(cum oil, oil volume, WOR, producing months) at first WC >= th."""
    mask = g["Water_Cut"] >= th
    if not mask.any():
        return (np.nan,) * 4
    r = g.loc[mask.idxmax()]
    return r["Cum_Oil"], r["Oil"], r["WOR"], r["Prod_Months"]


def _safe_div(a, b):
    return a / b if pd.notna(a) and pd.notna(b) and b > 0 else np.nan


def well_metrics(g: pd.DataFrame, thresholds=(0.05, 0.50, 0.90)) -> dict | None:
    g = g.sort_values("Date")
    ga = g[g["Total_Liquid"] > 0]
    if len(ga) == 0:
        return None
    t1, t2, t3 = thresholds
    p1, p2, p3 = pct(t1), pct(t2), pct(t3)

    cum_oil = g["Cum_Oil"].iloc[-1]; cum_wat = g["Cum_Water"].iloc[-1]
    wc_final = ga["Water_Cut"].iloc[-1]
    prod_months = ga["Prod_Months"].iloc[-1]

    wv = ga[ga["WOR"].notna() & (ga["WOR"] > 0)]
    wor_final = wv["WOR"].iloc[-1] if len(wv) else 0.0

    # WOR steepness: slope of log10(WOR) vs Np, per unit Np
    wor_slope_cum = np.nan
    wp = wv[wv["Cum_Oil"] > 0]
    if len(wp) > 4:
        wor_slope_cum = np.polyfit(wp["Cum_Oil"], np.log10(wp["WOR"]), 1)[0]

    tail = ga.tail(max(3, len(ga) // 3))
    wc_accel = (np.polyfit(tail["Prod_Months"], tail["Water_Cut"] * 100, 1)[0]
                if len(tail) > 2 else np.nan)

    co1, or1, wor1, bt1 = _at_threshold(ga, t1)
    co2, or2, wor2, bt2 = _at_threshold(ga, t2)
    co3, or3, wor3, bt3 = _at_threshold(ga, t3)

    xfw = np.nan
    gp = ga[(ga["Water_Cut"] > 0.50) & (ga["Water_Cut"] < 0.995)]
    if len(gp):
        fw = gp["Water_Cut"].iloc[-1]
        xfw = 1.0 / fw + np.log(fw / (1.0 - fw))

    return {
        "Well": g["Well"].iloc[0],
        "First_Prod": ga["Date"].iloc[0].date(), "Last_Prod": ga["Date"].iloc[-1].date(),
        "Prod_Months": prod_months, "Producing_Periods": len(ga),
        "Cum_Oil": cum_oil, "Cum_Water": cum_wat,
        "Cum_WOR": _safe_div(cum_wat, cum_oil),
        "Peak_Oil_Rate": ga["Oil_Rate"].max(),
        "WC_Final": wc_final, "WOR_Final": wor_final,
        "WOR_Slope_CumOil": wor_slope_cum, "WC_Accel": wc_accel,
        "WC_Per_Month": _safe_div(wc_final * 100, prod_months),
        f"CumOil_{p1}": co1, f"CumOil_{p2}": co2, f"CumOil_{p3}": co3,
        f"WOR_{p1}": wor1, f"WOR_{p2}": wor2, f"WOR_{p3}": wor3,
        f"BT_{p1}": bt1, f"BT_{p2}": bt2, f"BT_{p3}": bt3,
        # average WC rise rate over each interval (% per month)
        f"WCR_0_{p1}": _safe_div(t1 * 100, bt1),
        f"WCR_{p1}_{p2}": _safe_div((t2 - t1) * 100, bt2 - bt1),
        f"WCR_{p2}_{p3}": _safe_div((t3 - t2) * 100, bt3 - bt2),
        # average WOR increase per month over each interval
        f"DWOR_0_{p1}": _safe_div(wor1, bt1),
        f"DWOR_{p1}_{p2}": _safe_div(wor2 - wor1, bt2 - bt1),
        f"DWOR_{p2}_{p3}": _safe_div(wor3 - wor2, bt3 - bt2),
        # recovery ratios
        f"RR_{p2}_{p1}": _safe_div(co2, co1),
        f"RR_{p3}_{p1}": _safe_div(co3, co1),
        f"RR_{p3}_{p2}": _safe_div(co3, co2),
        "XFw_Last": xfw,
    }


def compute_metrics(df: pd.DataFrame, thresholds=(0.05, 0.50, 0.90),
                    min_months: int = 3) -> pd.DataFrame:
    rows = []
    for _, g in df.groupby("Well", sort=True):
        if (g["Total_Liquid"] > 0).sum() < min_months:
            continue
        r = well_metrics(g, thresholds)
        if r is not None:
            rows.append(r)
    return pd.DataFrame(rows)


def field_summary(df: pd.DataFrame) -> dict:
    ga = df[df["Total_Liquid"] > 0]
    oil, wat = df["Oil"].sum(), df["Water"].sum()
    return {
        "wells_producing": int(ga["Well"].nunique()),
        "first_production": str(ga["Date"].min().date()) if len(ga) else None,
        "last_production": str(ga["Date"].max().date()) if len(ga) else None,
        "cum_oil": float(oil), "cum_water": float(wat),
        "cum_gas": float(df["Gas"].sum()), "cum_water_injected": float(df["Water_Inj"].sum()),
        "cum_wor": float(wat / oil) if oil > 0 else None,
        "field_wc_final": float(ga.groupby("Date")[["Oil", "Water"]].sum()
                                .pipe(lambda x: x["Water"] / (x["Oil"] + x["Water"])).iloc[-1])
        if len(ga) else None,
    }
