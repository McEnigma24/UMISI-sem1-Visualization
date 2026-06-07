"""Generuje przykładowy eksport zgodny ze schematem BigQuery (do pracy offline)."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from config import DATA_RAW, END_MONTH, LANGUAGES, RANDOM_SEED, START_MONTH

# Profile inspirowane trendami GitHub (2011-2024). since = pierwszy sensowny miesiac na platformie.
LANGUAGE_PROFILES: dict[str, dict] = {
    "JavaScript": {"base": 0.18, "trend": 0.003, "season": 0.02, "since": "2011-01"},
    "Python": {"base": 0.13, "trend": 0.005, "season": 0.015, "since": "2011-01"},
    "Java": {"base": 0.14, "trend": -0.002, "season": 0.01, "since": "2011-01"},
    "TypeScript": {"base": 0.07, "trend": 0.010, "season": 0.012, "since": "2012-10"},
    "C#": {"base": 0.06, "trend": 0.0, "season": 0.008, "since": "2011-01"},
    "C++": {"base": 0.05, "trend": 0.001, "season": 0.01, "since": "2011-01"},
    "PHP": {"base": 0.09, "trend": -0.005, "season": 0.007, "since": "2011-01"},
    "C": {"base": 0.05, "trend": -0.001, "season": 0.008, "since": "2011-01"},
    "Go": {"base": 0.045, "trend": 0.004, "season": 0.006, "since": "2012-03"},
    "Ruby": {"base": 0.06, "trend": -0.006, "season": 0.005, "since": "2011-01"},
    "Rust": {"base": 0.025, "trend": 0.008, "season": 0.004, "since": "2015-05"},
    "Kotlin": {"base": 0.028, "trend": 0.003, "season": 0.005, "since": "2016-02"},
    "Swift": {"base": 0.028, "trend": 0.002, "season": 0.006, "since": "2014-09"},
    "Dart": {"base": 0.035, "trend": 0.006, "season": 0.006, "since": "2013-01"},
    "Scala": {"base": 0.035, "trend": -0.002, "season": 0.005, "since": "2011-01"},
    "R": {"base": 0.03, "trend": 0.002, "season": 0.004, "since": "2011-01"},
    "Objective-C": {"base": 0.05, "trend": -0.008, "season": 0.004, "since": "2011-01"},
    "Lua": {"base": 0.018, "trend": 0.0, "season": 0.003, "since": "2011-01"},
    "Haskell": {"base": 0.012, "trend": 0.001, "season": 0.003, "since": "2011-01"},
    "Julia": {"base": 0.018, "trend": 0.005, "season": 0.004, "since": "2014-01"},
    "Perl": {"base": 0.035, "trend": -0.006, "season": 0.004, "since": "2011-01"},
}

MONTHLY_MIN_TOTAL = 75_000
MONTHLY_MAX_TOTAL = 1_500_000
ADOPTION_RAMP_MONTHS = 36


def adoption_multiplier(month: pd.Period, since: str) -> float:
    start = pd.Period(since, freq="M")
    if month < start:
        return 0.0
    elapsed = month.ordinal - start.ordinal
    if elapsed <= 0:
        return 0.05
    return min(1.0, 0.05 + elapsed / ADOPTION_RAMP_MONTHS)


def generate_monthly_activity() -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    months = pd.period_range(START_MONTH, END_MONTH, freq="M")
    n_months = len(months)

    rows: list[dict] = []
    for i, month in enumerate(months):
        t = i / max(n_months - 1, 1)
        month_total = int(MONTHLY_MIN_TOTAL + (MONTHLY_MAX_TOTAL - MONTHLY_MIN_TOTAL) * (t**1.15))
        season = 1.0 + 0.03 * math.sin(2 * math.pi * i / 12)

        weights = []
        for lang in LANGUAGES:
            p = LANGUAGE_PROFILES.get(
                lang,
                {"base": 0.02, "trend": 0.0, "season": 0.005, "since": "2011-01"},
            )
            w = p["base"] * (1 + p["trend"] * n_months * t)
            w *= 1 + p["season"] * math.sin(2 * math.pi * i / 12 + hash(lang) % 7)
            w *= adoption_multiplier(month, p["since"])
            weights.append(max(w, 0.0))

        weights = np.array(weights)
        if weights.sum() <= 0:
            continue
        weights /= weights.sum()
        noise = rng.lognormal(mean=0.0, sigma=0.04, size=len(LANGUAGES))
        weights = weights * noise
        weights /= weights.sum()

        scaled_total = int(month_total * season)
        for lang, share in zip(LANGUAGES, weights):
            since = LANGUAGE_PROFILES.get(lang, {}).get("since", "2011-01")
            if adoption_multiplier(month, since) <= 0:
                continue
            push_events = int(scaled_total * share)
            if push_events < 1:
                continue
            intensity = {
                "JavaScript": 2.8,
                "Python": 2.5,
                "Java": 2.6,
                "TypeScript": 2.4,
                "Rust": 2.1,
            }.get(lang, 2.5)
            unique_actors = max(1, int(push_events / (intensity + rng.normal(0, 0.15))))
            rows.append(
                {
                    "month": str(month),
                    "language": lang,
                    "push_events": push_events,
                    "unique_actors": unique_actors,
                }
            )

    return pd.DataFrame(rows)


def main() -> None:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    df = generate_monthly_activity()
    out = DATA_RAW / "monthly_activity_sample.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows to {out}")


if __name__ == "__main__":
    main()
