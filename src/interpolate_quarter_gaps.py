"""Wypełnia brakujące kwartały w CSV (linear) — np. luki 2013–2014 w eksporcie BQ."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from config import DATA_RAW


def quarter_starts_between(qmin: pd.Timestamp, qmax: pd.Timestamp) -> pd.DatetimeIndex:
    """Kolejne początki kwartałów kalendarzowych (sty/kwi/lip/paź), jak w eksporcie BQ."""
    return pd.date_range(qmin, qmax, freq="QS-JAN")


def interpolate_language(sub: pd.DataFrame, full_idx: pd.DatetimeIndex) -> pd.DataFrame:
    sub = sub.copy()
    sub = sub.set_index("q")[["push_events", "unique_actors"]].sort_index()
    sub = sub.reindex(full_idx)
    sub["push_events"] = sub["push_events"].interpolate(method="linear", limit_direction="both")
    sub["unique_actors"] = sub["unique_actors"].interpolate(method="linear", limit_direction="both")
    sub["unique_actors"] = sub["unique_actors"].round().clip(lower=1).astype(int)
    sub.index.name = "q"
    sub = sub.reset_index()
    return sub


def run(input_path: Path, output_path: Path) -> None:
    df = pd.read_csv(input_path)
    if "quarter" not in df.columns:
        raise ValueError("Oczekiwana kolumna `quarter`")
    df["q"] = pd.to_datetime(df["quarter"])
    qmin, qmax = df["q"].min(), df["q"].max()
    full_idx = quarter_starts_between(qmin, qmax)

    parts = []
    for lang in sorted(df["language"].unique()):
        sub = df[df["language"] == lang][["q", "push_events", "unique_actors"]]
        filled = interpolate_language(sub, full_idx)
        filled["language"] = lang
        parts.append(filled)

    out = pd.concat(parts, ignore_index=True)
    out["quarter"] = out["q"].dt.strftime("%Y-%m-%d")
    out = out[["quarter", "language", "push_events", "unique_actors"]]
    out = out.sort_values(["quarter", "language"]).reset_index(drop=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    n_in = len(df)
    n_out = len(out)
    print(f"Wrote {output_path} ({n_in} -> {n_out} rows). Quarters: {full_idx[0].date()} .. {full_idx[-1].date()} ({len(full_idx)} steps).")


def main() -> None:
    default_in = DATA_RAW / "real" / "manyLanguages.csv"
    default_out = DATA_RAW / "real" / "manyLanguages_added.csv"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=default_in, help="CSV z quarter,language,…")
    parser.add_argument("--output", type=Path, default=default_out, help="Wyjście z wypełnionymi lukami")
    args = parser.parse_args()
    run(args.input, args.output)


if __name__ == "__main__":
    main()
