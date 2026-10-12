
# wbtdiag — water production surveillance

A Jupyter Notebook for analysing oil and water production data and investigating water-breakthrough behaviour including:

- **Chan (1995) WOR / WOR′ diagnostic** with smoothed WOR and WOR′ curves for visual interpretation.
- **Field and well-level production analysis** including oil and water production rates, water cut, and cumulative production.
- **Ershaghi–Abdou X-plot**, WOR and water cut vs cumulative oil, and water-cut heatmap.

The notebook uses Equinor's public **Volve** field data as an example. Open `water_breakthrough_analysis.ipynb` in Jupyter or VS Code and run the cells sequentially. The resulting figures are saved in `results/`.

**Example output:** [`results/figures/`](results/figures/)

## References

- Chan, K. S. (1995). *Water Control Diagnostic Plots.* SPE 30775.
- Ershaghi, I., & Abdou, M. (1984). *A Prediction Technique for Immiscible Processes Using Field Performance Data.* Journal of Petroleum Technology.