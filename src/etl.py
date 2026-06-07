"""ETL: surowy eksport CSV -> tabele processed."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from config import (
    DATA_PROCESSED,
    LANGUAGES,
    PROCESSED_COMMUNITY,
    PROCESSED_CONCENTRATION,
    PROCESSED_MONTHLY,
    PROCESSED_SHARES,
    RAW_INPUT,
)


def load_raw(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"month", "language", "push_events", "unique_actors"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Brakujące kolumny w pliku wejściowym: {missing}")

    df = df[df["language"].isin(LANGUAGES)].copy()
    df["month"] = df["month"].astype(str)
    df["push_events"] = df["push_events"].astype(int)
    df["unique_actors"] = df["unique_actors"].astype(int)
    return df.sort_values(["month", "language"]).reset_index(drop=True)


def build_shares(df: pd.DataFrame) -> pd.DataFrame:
    totals = df.groupby("month", as_index=False)["push_events"].sum().rename(
        columns={"push_events": "month_total"}
    )
    shares = df.merge(totals, on="month")
    shares["share"] = shares["push_events"] / shares["month_total"]
    shares["share_pct"] = shares["share"] * 100
    return shares


def build_community_metrics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["events_per_actor"] = out["push_events"] / out["unique_actors"]
    month_rank = (
        out.groupby("month")["unique_actors"]
        .rank(ascending=False, method="dense")
        .astype(int)
    )
    out["actor_rank"] = month_rank
    return out


def build_concentration(shares: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for month, group in shares.groupby("month"):
        hhi = (group["share"] ** 2).sum()
        top3 = group.nlargest(3, "share")["share"].sum()
        top_lang = group.loc[group["share"].idxmax(), "language"]
        rows.append(
            {
                "month": month,
                "hhi": round(hhi, 6),
                "top3_share": round(top3, 6),
                "top3_share_pct": round(top3 * 100, 2),
                "leader": top_lang,
            }
        )
    return pd.DataFrame(rows)


def run_etl(input_path: Path = RAW_INPUT) -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    df = load_raw(input_path)
    shares = build_shares(df)
    community = build_community_metrics(df)
    concentration = build_concentration(shares)

    df.to_csv(PROCESSED_MONTHLY, index=False)
    shares.to_csv(PROCESSED_SHARES, index=False)
    community.to_csv(PROCESSED_COMMUNITY, index=False)
    concentration.to_csv(PROCESSED_CONCENTRATION, index=False)

    print(f"ETL done. Output: {DATA_PROCESSED}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ETL aktywności języków GitHub")
    parser.add_argument(
        "--input",
        type=Path,
        default=RAW_INPUT,
        help="Ścieżka do surowego CSV (eksport BigQuery)",
    )
    args = parser.parse_args()
    run_etl(args.input)


if __name__ == "__main__":
    main()
