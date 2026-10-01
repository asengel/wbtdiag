"""Command-line interface:  wbtdiag run -c examples/volve/config.yaml"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter

from .config import Config


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wbtdiag",
                                description="Water breakthrough diagnosis for well-level production data.")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run the full analysis and write figures/tables/report")
    r.add_argument("-c", "--config", required=True, help="YAML config file")
    r.add_argument("-i", "--input", help="override input.path from the config")
    r.add_argument("-o", "--output", help="override output_dir from the config")
    r.add_argument("--format", choices=["png", "svg", "pdf"], help="figure format")
    r.add_argument("--no-well-figures", action="store_true", help="skip per-well figures")
    r.add_argument("--strict", action="store_true",
                   help="exit with code 2 if any validation check fails (useful in CI)")
    r.add_argument("-v", "--verbose", action="store_true")

    ins = sub.add_parser("inspect", help="list the columns of a CSV/Excel file to help write a config")
    ins.add_argument("file"); ins.add_argument("--sep", default=",")
    ins.add_argument("--sheet", default=None, help="Excel sheet name or index (default: all)")
    return p


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)

    if args.cmd == "inspect":
        import pandas as pd
        if args.file.lower().endswith((".xlsx", ".xlsm", ".xls")):
            xl = pd.ExcelFile(args.file)
            names = [args.sheet] if args.sheet is not None else xl.sheet_names
            frames = {n: pd.read_excel(xl, n, nrows=200) for n in names}
        else:
            frames = {"": pd.read_csv(args.file, sep=args.sep, nrows=200, encoding="utf-8-sig")}
        for name, df in frames.items():
            print(f"\n{'Sheet ' + repr(name) + ': ' if name else ''}{len(df.columns)} columns "
                  f"(first 200 rows sampled)")
            for c in df.columns:
                ex = df[c].dropna().astype(str).head(3).tolist()
                print(f"  {str(c)!r:40s} {str(df[c].dtype):10s} e.g. {ex}")
        print("\nMap them in the `columns:` section of your config "
              "(see config_template.yaml).")
        return 0

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="[%(levelname)s] %(message)s")
    from .pipeline import run      # heavy imports only when needed

    cfg = Config.from_yaml(args.config)
    if args.input:
        cfg.input.path = args.input
    if args.format:
        cfg.fig_format = args.format
    res = run(cfg, args.output, per_well=not args.no_well_figures)

    f = res.field
    print(f"\n  {cfg.name}: {len(res.metrics)} producing wells, "
          f"{f['first_production']} -> {f['last_production']}")
    print(f"  Cum oil {f['cum_oil']:,.0f} {cfg.volume_unit} | "
          f"cum water {f['cum_water']:,.0f} {cfg.volume_unit}")
    print("  Chan current mechanism:")
    for lab, n in Counter(r.current for r in res.chan.values()).most_common():
        print(f"    {n:>3}  {lab}")
    print("  Validation:")
    for c in res.checks:
        print(f"    [{'PASS' if c.passed else 'FAIL'}] {c.name}: {c.detail}")
    print(f"\n  Outputs in {res.out_dir}/  (open REPORT.md or index.html)\n")
    return 2 if (args.strict and not res.all_checks_passed) else 0


if __name__ == "__main__":
    sys.exit(main())
