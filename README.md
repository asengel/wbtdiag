# wbtdiag — water breakthrough diagnosis

A Python tool that screens production data for
water-breakthrough behaviour and water-production mechanisms:

- **Chan (1995) WOR / WOR′ diagnostic** with a rolling-window, classifier that reports each well's *sequence* of mechanisms (constant WOR,
  normal displacement, coning, channeling, multilayer channeling, near-wellbore
  breakthrough) and its current one.
- **Breakthrough metrics** at configurable water-cut thresholds (default 5 / 50 / 90 %):
  time and cumulative oil at each threshold, WC rise rates, ΔWOR per month,
  recovery ratios.
- **Ershaghi–Abdou X-plot**, WOR and WC vs cumulative oil, WC heatmap.

It runs on any CSV or Excel production table once its columns are mapped in a
small YAML file. The example uses Equinor's public **Volve** field data.

👉 **Example output:** [`examples/volve/output/REPORT.md`](examples/volve/output/REPORT.md)

## Limitations of the Chan classifier

Treat the result as a screen and confirm with logs, production logging, well
tests and PTA.

## References

- Chan, K.S. (1995). *Water Control Diagnostic Plots.* SPE 30775.
- Ershaghi, I. & Abdou, M. (1984). *A Prediction Technique for Immiscible Processes Using Field Performance Data.* JPT.

## Licence

The code is MIT-licensed. The Volve workbook in `examples/volve/` is © Equinor
and is redistributed under the Equinor Open Data Licence, which applies to that
file and to the outputs derived from it.
