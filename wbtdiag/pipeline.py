"""
End-to-end run: load -> metrics -> Chan -> validation -> figures + tables +
Markdown report + HTML gallery.

Output layout (``<output_dir>/``)::

    REPORT.md                  renders directly on GitHub
    index.html                 static gallery (works with GitHub Pages)
    figures/field/*.png        field-level charts
    figures/wells/*.png        one Chan + production figure per well
    tables/well_summary.csv    one row per well (metrics + Chan result)
    tables/chan_segments.csv   one row per mechanism segment
    tables/monthly_data.csv    the cleaned monthly data actually analysed
    tables/validation.csv      data-integrity checks
"""
from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import chan as chan_mod
from . import io, metrics, plots, validate
from .config import Config

log = logging.getLogger(__name__)


@dataclass
class RunResult:
    cfg: Config
    data: pd.DataFrame
    metrics: pd.DataFrame
    chan: dict
    field: dict
    checks: list
    figures: dict = field(default_factory=dict)   # section -> [(title, relpath)]
    out_dir: Path | None = None

    @property
    def all_checks_passed(self) -> bool:
        return all(c.passed for c in self.checks)


def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")


# ----------------------------------------------------------------------------
def analyse(cfg: Config) -> RunResult:
    """Pure analysis, no files written."""
    df = io.load(cfg)
    prod = io.producers(df)
    m = metrics.compute_metrics(prod, cfg.wc_thresholds, cfg.min_months)
    results = chan_mod.classify_all(prod[prod["Well"].isin(m["Well"])], cfg.chan)
    if len(m):
        chan_df = pd.DataFrame([r.summary() for r in results.values()])
        m = m.merge(chan_df, on="Well", how="left")
    fld = metrics.field_summary(df)
    checks = validate.integrity_checks(df)
    return RunResult(cfg=cfg, data=df, metrics=m, chan=results, field=fld, checks=checks)


def run(cfg: Config, out_dir: str | Path | None = None, per_well: bool = True) -> RunResult:
    """Analyse and write every output."""
    res = analyse(cfg)
    out = Path(out_dir) if out_dir else cfg.output_path
    (out / "figures" / "field").mkdir(parents=True, exist_ok=True)
    (out / "figures" / "wells").mkdir(parents=True, exist_ok=True)
    (out / "tables").mkdir(parents=True, exist_ok=True)
    res.out_dir = out
    _write_tables(res, out)
    _write_figures(res, out, per_well)
    _write_markdown(res, out)
    _write_html(res, out)
    return res


# ----------------------------------------------------------------------------
def _write_tables(res: RunResult, out: Path):
    t = out / "tables"
    res.metrics.round(6).to_csv(t / "well_summary.csv", index=False)
    chan_mod.segments_table(res.chan).to_csv(t / "chan_segments.csv", index=False)
    cols = ["Well", "Date", "Prod_Months", "Days", "Oil", "Water", "Gas", "Water_Inj",
            "Oil_Rate", "Water_Rate", "Water_Cut", "WOR", "Cum_Oil", "Cum_Water"]
    res.data[cols].to_csv(t / "monthly_data.csv", index=False, float_format="%.6g")
    pd.DataFrame([c.as_dict() for c in res.checks]).to_csv(t / "validation.csv", index=False)


# keep library/version stamps out of the image files
_NO_STAMP = {"png": {"Software": None}, "svg": {"Creator": None, "Date": None},
             "pdf": {"Creator": None, "Producer": None, "CreationDate": None}}


def _save(fig, path: Path, cfg: Config):
    fig.savefig(path, dpi=cfg.dpi, metadata=_NO_STAMP.get(cfg.fig_format))
    plt.close(fig)


def _write_figures(res: RunResult, out: Path, per_well: bool):
    cfg, m, u, th = res.cfg, res.metrics, res.cfg.volume_unit, res.cfg.wc_thresholds
    prod = io.producers(res.data)
    colors = plots.WellColors(prod["Well"].unique())
    ext = cfg.fig_format
    field_figs = [
        ("01_field_overview", "Field overview", lambda: plots.field_overview(res.data, u)),
        ("02_wc_heatmap", "Water-cut heatmap", lambda: plots.wc_heatmap(prod)),
        ("03_chan_mechanism_summary", "Chan: current mechanism per well",
         lambda: plots.mechanism_summary(res.chan, cfg.chan.win)),
        ("04_chan_timeline", "Chan: mechanism timeline", lambda: plots.chan_timeline(res.chan)),
        ("05_wor_vs_cumoil", "WOR vs cumulative oil", lambda: plots.wor_vs_cumoil(prod, colors, u)),
        ("06_wc_vs_cumoil", "Water cut vs cumulative oil", lambda: plots.wc_vs_cumoil(prod, colors, u)),
        ("07_ershaghi_xplot", "Ershaghi–Abdou X-plot", lambda: plots.ershaghi_xplot(prod, colors, u)),
        ("08_hist_timing", "Histograms: timing & volumes", lambda: plots.hist_timing(m, th, u)),
        ("09_hist_wc_rise", "Histograms: WC rise rate", lambda: plots.hist_wcr(m, th)),
        ("10_cumoil_at_wc", "Cum oil at WC thresholds", lambda: plots.bt_bars(m, th, u)),
        ("11_cumoil_at_wc_grouped", "Cum oil at WC thresholds (grouped)",
         lambda: plots.bt_grouped(m, th, u)),
        ("12_dwor_vs_cumoil", "WOR growth vs cum oil", lambda: plots.dwor_vs_cumoil(m, th, colors, u)),
        ("13_wc_rise_vs_timing", "WC rise rate vs timing", lambda: plots.wcr_vs_bt(m, th, colors)),
        ("14_recovery_crossplots", "Recovery ratios & BT crossplots",
         lambda: plots.recovery_crossplots(m, th, colors, u)),
        ("15_additional_crossplots", "Additional crossplots",
         lambda: plots.additional_crossplots(m, colors, u)),
    ]
    res.figures["field"] = []
    for fname, title, fn in field_figs:
        rel = f"figures/field/{fname}.{ext}"
        try:
            _save(fn(), out / rel, cfg)
            res.figures["field"].append((title, rel))
        except Exception as exc:                 # one bad plot must not kill the run
            log.warning("figure %s failed: %s", fname, exc)
            plt.close("all")

    res.figures["wells"] = []
    if per_well and len(m):
        rng = (prod["Date"].min(), prod["Date"].max())
        for _, row in m.iterrows():
            w = row["Well"]
            rel = f"figures/wells/{safe_name(w)}.{ext}"
            try:
                fig = plots.chan_well(prod[prod["Well"] == w], res.chan[w], row, u, rng)
                _save(fig, out / rel, cfg)
                res.figures["wells"].append((w, rel))
            except Exception as exc:
                log.warning("well figure %s failed: %s", w, exc)
                plt.close("all")


# ----------------------------------------------------------------------------
def _md_table(df: pd.DataFrame) -> str:
    def fmt(v):
        if isinstance(v, (float, np.floating)):
            if not np.isfinite(v):
                return "–"
            return f"{v:,.0f}" if abs(v) >= 100 else f"{v:,.2f}"
        return str(v).replace("|", "\\|")
    head = "| " + " | ".join(df.columns) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    rows = ["| " + " | ".join(fmt(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([head, sep, *rows])


def _write_markdown(res: RunResult, out: Path):
    cfg, f, u = res.cfg, res.field, res.cfg.volume_unit
    p1, p2, p3 = map(metrics.pct, cfg.wc_thresholds)
    L = [f"# Water breakthrough diagnosis — {cfg.name}", "",
         f"_Generated {datetime.now():%Y-%m-%d %H:%M} with wbtdiag._", ""]

    L += ["## Field summary", "",
          "| Item | Value |", "|---|---|",
          f"| Producing wells analysed | {len(res.metrics)} |",
          f"| Production period | {f['first_production']} → {f['last_production']} |",
          f"| Cumulative oil | {f['cum_oil']:,.0f} {u} |",
          f"| Cumulative water | {f['cum_water']:,.0f} {u} |",
          f"| Cumulative water injected | {f['cum_water_injected']:,.0f} {u} |",
          f"| Cumulative WOR | {f['cum_wor']:.2f} |" if f["cum_wor"] is not None else None,
          f"| Field water cut, last month | {f['field_wc_final'] * 100:.1f}% |"
          if f["field_wc_final"] is not None else None, ""]
    inj = res.data.attrs.get("injectors_only", [])
    if inj:
        L += [f"Injector-only wells (excluded from producer diagnostics): {', '.join(inj)}.", ""]

    n_ok = sum(c.passed for c in res.checks)
    L += ["## Validation", "",
          f"**{n_ok} / {len(res.checks)} checks passed.**", "",
          "| Result | Kind | Check | Detail |", "|---|---|---|---|"]
    for c in res.checks:
        L.append(f"| {'✅' if c.passed else '❌'} | {c.kind} | {c.name} | {c.detail} |")
    L.append("")

    if len(res.metrics):
        L += ["## Chan diagnostic by well", "",
              "Screening interpretation after Chan (SPE 30775). WOR' increasing with time → "
              "channeling, decreasing → coning. Confirm with logs, PLT, well tests and PTA.", ""]
        cols = ["Well", "Chan_Current", "Chan_Dominant", "Chan_Departure_Mo", "Chan_Sequence"]
        L += [_md_table(res.metrics[cols].rename(columns={
            "Chan_Current": "Current", "Chan_Dominant": "Dominant",
            "Chan_Departure_Mo": "WOR departure (mo)", "Chan_Sequence": "Sequence"})), ""]

        L += ["## Key metrics by well", ""]
        kc = ["Well", "Prod_Months", "Cum_Oil", "Cum_Water", "WC_Final",
              f"BT_{p1}", f"BT_{p2}", f"BT_{p3}", f"CumOil_{p1}", f"CumOil_{p2}", f"CumOil_{p3}"]
        km = res.metrics[kc].copy(); km["WC_Final"] = km["WC_Final"] * 100
        km = km.rename(columns={"Prod_Months": "Months", "Cum_Oil": f"Cum oil ({u})",
                                "Cum_Water": f"Cum water ({u})", "WC_Final": "Final WC %",
                                f"BT_{p1}": f"Mo→{p1}%", f"BT_{p2}": f"Mo→{p2}%",
                                f"BT_{p3}": f"Mo→{p3}%",
                                f"CumOil_{p1}": f"Np@{p1}%", f"CumOil_{p2}": f"Np@{p2}%",
                                f"CumOil_{p3}": f"Np@{p3}%"})
        L += [_md_table(km), "", "Full table: [`tables/well_summary.csv`](tables/well_summary.csv)", ""]

    L += ["## Field figures", ""]
    for title, rel in res.figures.get("field", []):
        L += [f"### {title}", "", f"![{title}]({rel})", ""]
    if res.figures.get("wells"):
        L += ["## Per-well figures", ""]
        for w, rel in res.figures["wells"]:
            L += [f"### {w}", "", f"![{w}]({rel})", ""]
    (out / "REPORT.md").write_text("\n".join(x for x in L if x is not None), encoding="utf-8")


def _write_html(res: RunResult, out: Path):
    cfg = res.cfg
    cards = []
    for sec, items in (("Field", res.figures.get("field", [])),
                       ("Wells", res.figures.get("wells", []))):
        if not items:
            continue
        cards.append(f"<h2>{sec}</h2><div class='grid'>")
        for title, rel in items:
            t = html.escape(title)
            cards.append(f"<figure><a href='{rel}'><img loading='lazy' src='{rel}' alt='{t}'></a>"
                         f"<figcaption>{t}</figcaption></figure>")
        cards.append("</div>")
    n_ok = sum(c.passed for c in res.checks)
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Water breakthrough diagnosis — {html.escape(cfg.name)}</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0 auto;max-width:1400px;padding:24px;color:#222;background:#fafafa}}
h1{{margin-bottom:4px}} .sub{{color:#666;margin-top:0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:18px}}
figure{{margin:0;background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:10px}}
img{{width:100%;height:auto;display:block}} figcaption{{font-size:14px;color:#444;margin-top:6px}}
a.btn{{display:inline-block;margin-right:12px;color:#1565C0}}
</style></head><body>
<h1>Water breakthrough diagnosis — {html.escape(cfg.name)}</h1>
<p class="sub">{len(res.metrics)} producing wells · {res.field['first_production']} → {res.field['last_production']} ·
validation {n_ok}/{len(res.checks)} passed</p>
<p><a class="btn" href="REPORT.md">REPORT.md</a><a class="btn" href="tables/well_summary.csv">well_summary.csv</a>
<a class="btn" href="tables/chan_segments.csv">chan_segments.csv</a><a class="btn" href="tables/validation.csv">validation.csv</a></p>
{''.join(cards)}
</body></html>"""
    (out / "index.html").write_text(doc, encoding="utf-8")
