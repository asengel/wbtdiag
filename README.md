# wbtdiag — water breakthrough diagnosis

A config-driven Python tool that screens production data for
water-breakthrough behaviour and water-production mechanisms:

- **Chan (1995) WOR / WOR′ diagnostic** with a rolling-window, phase-based
  classifier that reports each well's *sequence* of mechanisms (constant WOR,
  normal displacement, coning, channeling, multilayer channeling, near-wellbore
  breakthrough) and its current one.
- **Breakthrough metrics** at configurable water-cut thresholds (default 5 / 50 / 90 %):
  time and cumulative oil at each threshold, WC rise rates, ΔWOR per month,
  recovery ratios.
- **Ershaghi–Abdou X-plot**, WOR and WC vs cumulative oil, WC heatmap with shut-ins.
- **Built-in data-integrity checks** on every run: volume conservation through
  loading and resampling, valid water cuts, consistent cumulatives.

It runs on any CSV or Excel production table once its columns are mapped in a
small YAML file. The example uses Equinor's public **Volve** field data.

👉 **Example output:** [`examples/volve/output/REPORT.md`](examples/volve/output/REPORT.md)


---

## Run the Volve example

```bash
pip install -r requirements.txt
python -m wbtdiag run -c examples/volve/config.yaml
```

This reads the **"Monthly Production Data"** sheet of the original Equinor
workbook [`examples/volve/Volve_production_data.xlsx`](examples/volve/) and
writes everything to `examples/volve/output/`:

| Path | What it is |
|---|---|
| `REPORT.md` | Report with tables and all figures — renders directly on GitHub |
| `index.html` | Static figure gallery (works as a GitHub Pages site) |
| `figures/field/*.png` | 15 field-level figures |
| `figures/wells/*.png` | One Chan + production figure per well |
| `tables/well_summary.csv` | One row per well: all metrics + Chan result |
| `tables/chan_segments.csv` | One row per mechanism segment |
| `tables/monthly_data.csv` | The cleaned monthly data that was analysed |
| `tables/validation.csv` | Result of every validation check |

Options: `--format svg` (vector figures), `--no-well-figures`, `-o other_dir`,
`-i other_file.xlsx`, `--strict` (non-zero exit code if any check fails), `-v`.

## Use your own data

1. List the columns in your file:

   ```bash
   python -m wbtdiag inspect my_field/production.csv
   ```

2. Put your data file and a copy of [`config_template.yaml`](config_template.yaml)
   in one folder and map your columns:

   ```yaml
   input:
     path: production.xlsx     # relative to this config file
     sheet: 0                  # Excel only
   columns:
     well: well name           # required
     date: Date                # required (or year + month)
     oil: CV.CDOIL             # required
     water: CV.CDWAT           # required
     water_inj: CV.CDWinj      # optional
   values_are: rate            # 'volume' per row, or per-day 'rate'
   resample: MS                # aggregate to monthly before the diagnostics
   ```

3. `python -m wbtdiag run -c my_field/config.yaml` — results land in `my_field/output/`.

CSV or Excel, a date column or separate year / month columns, daily or monthly
rows, volumes or calendar-day rates, with or without cumulative columns, and
numbers with thousands separators (`1,166`) are all handled. Wells with no oil
or water (injectors) are reported and left out of the producer diagnostics.

## Data checks

Every run checks that oil, water and injection volumes are conserved exactly
through loading and monthly resampling, that water cut stays in [0, 1], that
cumulatives never decrease and equal the sum of the period volumes, and that
there are no negative volumes or duplicate well-months. Results are written to
`tables/validation.csv` and the report; `--strict` makes a failed check stop
with a non-zero exit code. All checks pass on the Volve example.

## Limitations of the Chan classifier

Treat the result as a screen and confirm with logs, production logging, well
tests and PTA.

### Classifier parameters (`chan:` in the config)

| Key | Default | Meaning |
|---|---|---|
| `win` | 7 | rolling window, points |
| `min_log_span` | 0.0 | minimum window span in decades of time (0 = original) |
| `const_slope` | 0.10 | rolling WOR log-log slope below which a phase is "flat" |
| `worp_slope_neg` | −0.15 | WOR′ slope below which a rising phase is coning |
| `worp_steep` | 1.00 | WOR′ slope above which a rising phase is channeling |
| `departure_factor` | 3.0 | WOR > factor × early baseline marks departure |
| `nearwell_decade`, `nearwell_dt` | 1.0, 3.0 | ≥ 1 decade WOR jump within ≤ 3 months ⇒ near-wellbore |
| `nearwell_min_wor` | 0.0 | ignore jumps that land below this WOR (0 = original) |
| `min_seg` | 4 | shorter phases are merged into the previous one |

## Method notes

- All diagnostics run on **monthly** data; daily data are summed to calendar
  months first. Rates in plots are calendar-day rates (volume / days in month).
- Time on production starts at each well's **first liquid production**, offset
  by half a month so t > 0 on log-log axes.
- WOR′ is the signed time derivative of a Savitzky–Golay-smoothed (log-space) WOR.

## Project layout

```
wbtdiag/                    the code
    config.py               YAML config + parameters
    io.py                   CSV/Excel loading, column mapping, monthly resampling
    metrics.py              per-well and field metrics
    chan.py                 Chan WOR/WOR' classifier
    plots.py                one function per figure
    validate.py             data-integrity checks
    pipeline.py             runs everything and writes the outputs
    cli.py                  command line (`python -m wbtdiag ...`)
examples/volve/
    Volve_production_data.xlsx   original Equinor workbook (input)
    config.yaml                  sheet and column mapping
    output/                      results of the run
config_template.yaml        starting point for your own data
requirements.txt
```

## References

- Chan, K.S. (1995). *Water Control Diagnostic Plots.* SPE 30775.
- Ershaghi, I. & Abdou, M. (1984). *A Prediction Technique for Immiscible Processes Using Field Performance Data.* JPT.

## Licence

The code is MIT-licensed. The Volve workbook in `examples/volve/` is © Equinor
and is redistributed under the Equinor Open Data Licence, which applies to that
file and to the outputs derived from it.
