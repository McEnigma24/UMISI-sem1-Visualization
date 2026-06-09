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
    required_metrics = {"language", "push_events", "unique_actors"}
    missing_metrics = required_metrics - set(df.columns)
    if missing_metrics:
        raise ValueError(f"Brakujące kolumny w pliku wejściowym: {missing_metrics}")
    if "month" not in df.columns and "quarter" in df.columns:
        df = df.rename(columns={"quarter": "month"})
    if "month" not in df.columns:
        raise ValueError(
            "Oczekiwana kolumna czasu: `month` (miesiąc) albo `quarter` (eksport kwartalny z BQ)."
        )

    df = df[df["language"].isin(LANGUAGES)].copy()
    df["month"] = df["month"].astype(str)
    # Eksport BQ z ważeniem wielojęzycznym: push_events mogą być ułamkami (suma wag ≤ liczba pushy).
    df["push_events"] = pd.to_numeric(df["push_events"], errors="coerce").astype(float)
    df["unique_actors"] = pd.to_numeric(df["unique_actors"], errors="coerce").fillna(0).astype(int)
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
    """Ranking społeczności: `actor_rank` = pozycja po `unique_actors` w obrębie kwartału (dense).

    Gdy `unique_actors` = 0 (np. artefakt eksportu BQ), `events_per_actor` jest NaN (unikamy inf),
    a ranki z samych zer rozstrzygamy po `push_events`; gdy cały kwartał ma zera — też po push.

    `actors_stack` / `events_per_actor_viz`: dla wykresu słupkowego i linii średniej, gdy brak
    licznika aktorów ale są push'e, szacujemy wielkość stosu jako push / medianę(events/actor)
    dla danego języka z okresów z poprawnym `unique_actors` (fallback: mediana globalna).
    """
    out = df.copy()
    pe = out["push_events"].astype(float)
    ua = out["unique_actors"].astype(float)
    out["events_per_actor"] = pe.div(ua).where(ua > 0)

    good = ua > 0
    epa_obs = (pe / ua).where(good)
    global_median_epa = float(epa_obs.median()) if epa_obs.notna().any() else 1.0
    if global_median_epa <= 0 or pd.isna(global_median_epa):
        global_median_epa = 1.0
    lang_median_epa = (
        out.loc[good]
        .assign(_epa=lambda d: d["push_events"].astype(float) / d["unique_actors"].astype(float))
        .groupby("language")["_epa"]
        .median()
    )
    epa_ref = out["language"].map(lang_median_epa).astype(float)
    epa_ref = epa_ref.fillna(global_median_epa)
    epa_ref = epa_ref.where(epa_ref > 0, global_median_epa)

    need_stack = (ua <= 0) & (pe > 0)
    out["actors_stack"] = ua.where(ua > 0, 0.0)
    out.loc[need_stack, "actors_stack"] = (pe.loc[need_stack] / epa_ref.loc[need_stack]).clip(lower=1.0)
    out["actors_stack"] = out["actors_stack"].round(0).astype(int)

    out["events_per_actor_viz"] = out["events_per_actor"].copy()
    fill_line = out["events_per_actor"].isna() & (pe > 0)
    out.loc[fill_line, "events_per_actor_viz"] = epa_ref.loc[fill_line]

    def _actor_rank_one_month(g: pd.DataFrame) -> pd.Series:
        pos = g["unique_actors"] > 0
        if pos.any():
            r_pos = g.loc[pos, "unique_actors"].rank(ascending=False, method="dense").astype(int)
            max_r = int(r_pos.max())
            out_s = pd.Series(max_r + 1, index=g.index, dtype=int)
            out_s.loc[pos] = r_pos
            return out_s
        return g["push_events"].rank(ascending=False, method="dense").astype(int)

    rank_parts: list[pd.Series] = []
    for _, g in out.groupby("month", sort=False):
        rank_parts.append(_actor_rank_one_month(g))
    out["actor_rank"] = pd.concat(rank_parts).sort_index()
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

    print(f"ETL done. Input: {input_path} -> {DATA_PROCESSED}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ETL aktywności języków GitHub",
        epilog="Domyślny plik: RAW_INPUT z config (eksport BigQuery). Inny: --input ścieżka.csv.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=RAW_INPUT,
        help="Surowy CSV (month|quarter, language, push_events, unique_actors); push_events mogą być float (BQ ważone)",
    )
    args = parser.parse_args()
    run_etl(args.input)


if __name__ == "__main__":
    main()
