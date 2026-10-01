# Water breakthrough diagnosis — Volve (Equinor, NCS) — monthly

_Generated 2026-10-01 09:19 with wbtdiag._

## Field summary

| Item | Value |
|---|---|
| Producing wells analysed | 6 |
| Production period | 2008-02-01 → 2016-09-01 |
| Cumulative oil | 10,037,081 Sm3 |
| Cumulative water | 15,318,578 Sm3 |
| Cumulative water injected | 30,330,134 Sm3 |
| Cumulative WOR | 1.53 |
| Field water cut, last month | 84.5% |

Injector-only wells (excluded from producer diagnostics): 15/9-F-4.

## Validation

**8 / 8 checks passed.**

| Result | Kind | Check | Detail |
|---|---|---|---|
| ✅ | integrity | Oil volume conserved through resampling | input 10,037,081 vs processed 10,037,081 |
| ✅ | integrity | Water volume conserved through resampling | input 15,318,578 vs processed 15,318,578 |
| ✅ | integrity | Water_Inj volume conserved through resampling | input 30,330,134 vs processed 30,330,134 |
| ✅ | integrity | Water cut within [0, 1] | min 0.000, max 0.967 |
| ✅ | integrity | Cumulative oil non-decreasing in every well | ok |
| ✅ | integrity | Final cumulative oil equals sum of oil volumes | ok |
| ✅ | integrity | No negative volumes after cleaning | 0 negative |
| ✅ | integrity | One row per well and period | 0 duplicates |

## Chan diagnostic by well

Screening interpretation after Chan (SPE 30775). WOR' increasing with time → channeling, decreasing → coning. Confirm with logs, PLT, well tests and PTA.

| Well | Current | Dominant | WOR departure (mo) | Sequence |
|---|---|---|---|---|
| 15/9-F-1 C | Normal displacement | Normal displacement | 4.52 | Normal displacement (1-25 mo) |
| 15/9-F-11 | Channeling | Channeling | 16.53 | Channeling (2-39 mo) |
| 15/9-F-12 | Multilayer channeling | Multilayer channeling | 16.46 | Normal displacement (0-1 mo)  ->  Near-wellbore breakthrough (2-4 mo)  ->  Constant WOR (5-7 mo)  ->  Multilayer channeling (8-102 mo) |
| 15/9-F-14 | Near-wellbore breakthrough | Near-wellbore breakthrough | 11.50 | Constant WOR (1-4 mo)  ->  Multilayer channeling (5-6 mo)  ->  Near-wellbore breakthrough (7-8 mo)  ->  Multilayer channeling (9-9 mo)  ->  Near-wellbore breakthrough (10-97 mo) |
| 15/9-F-15 D | Channeling | Channeling | 18.45 | Channeling (9-30 mo) |
| 15/9-F-5 | Insufficient data | Insufficient data | – |  |

## Key metrics by well

| Well | Months | Cum oil (Sm3) | Cum water (Sm3) | Final WC % | Mo→5% | Mo→50% | Mo→90% | Np@5% | Np@50% | Np@90% |
|---|---|---|---|---|---|---|---|---|---|---|
| 15/9-F-1 C | 24.51 | 177,709 | 207,302 | 72.65 | 2.50 | 6.52 | – | 55,662 | 96,355 | – |
| 15/9-F-11 | 38.54 | 1,147,849 | 1,090,806 | 84.46 | 2.53 | 25.51 | – | 53,194 | 850,648 | – |
| 15/9-F-12 | 102 | 4,579,610 | 6,833,320 | 88.35 | 3.47 | 28.45 | 61.45 | 332,463 | 3,283,228 | 4,174,157 |
| 15/9-F-14 | 96.51 | 3,942,233 | 7,121,250 | 96.62 | 11.50 | 23.49 | 73.51 | 1,200,800 | 2,200,238 | 3,801,059 |
| 15/9-F-15 D | 30.47 | 148,519 | 52,366 | 58.59 | 13.47 | 23.47 | – | 78,693 | 123,235 | – |
| 15/9-F-5 | 4.52 | 41,161 | 13,533 | 20.99 | 0.49 | – | – | 3,401 | – | – |

Full table: [`tables/well_summary.csv`](tables/well_summary.csv)

## Field figures

### Field overview

![Field overview](figures/field/01_field_overview.png)

### Water-cut heatmap

![Water-cut heatmap](figures/field/02_wc_heatmap.png)

### Chan: current mechanism per well

![Chan: current mechanism per well](figures/field/03_chan_mechanism_summary.png)

### Chan: mechanism timeline

![Chan: mechanism timeline](figures/field/04_chan_timeline.png)

### WOR vs cumulative oil

![WOR vs cumulative oil](figures/field/05_wor_vs_cumoil.png)

### Water cut vs cumulative oil

![Water cut vs cumulative oil](figures/field/06_wc_vs_cumoil.png)

### Ershaghi–Abdou X-plot

![Ershaghi–Abdou X-plot](figures/field/07_ershaghi_xplot.png)

### Histograms: timing & volumes

![Histograms: timing & volumes](figures/field/08_hist_timing.png)

### Histograms: WC rise rate

![Histograms: WC rise rate](figures/field/09_hist_wc_rise.png)

### Cum oil at WC thresholds

![Cum oil at WC thresholds](figures/field/10_cumoil_at_wc.png)

### Cum oil at WC thresholds (grouped)

![Cum oil at WC thresholds (grouped)](figures/field/11_cumoil_at_wc_grouped.png)

### WOR growth vs cum oil

![WOR growth vs cum oil](figures/field/12_dwor_vs_cumoil.png)

### WC rise rate vs timing

![WC rise rate vs timing](figures/field/13_wc_rise_vs_timing.png)

### Recovery ratios & BT crossplots

![Recovery ratios & BT crossplots](figures/field/14_recovery_crossplots.png)

### Additional crossplots

![Additional crossplots](figures/field/15_additional_crossplots.png)

## Per-well figures

### 15/9-F-1 C

![15/9-F-1 C](figures/wells/15_9-F-1_C.png)

### 15/9-F-11

![15/9-F-11](figures/wells/15_9-F-11.png)

### 15/9-F-12

![15/9-F-12](figures/wells/15_9-F-12.png)

### 15/9-F-14

![15/9-F-14](figures/wells/15_9-F-14.png)

### 15/9-F-15 D

![15/9-F-15 D](figures/wells/15_9-F-15_D.png)

### 15/9-F-5

![15/9-F-5](figures/wells/15_9-F-5.png)
