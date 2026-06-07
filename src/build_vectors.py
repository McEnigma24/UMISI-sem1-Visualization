"""Buduje wektory czasowe aktywności per język (do redukcji wymiaru)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from config import PROCESSED_SHARES, PROCESSED_VECTORS, RANDOM_SEED


def build_language_vectors(shares: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray, list[str], list[str]]:
    pivot = shares.pivot(index="language", columns="month", values="share_pct").fillna(0.0)
    months = list(pivot.columns)
    languages = list(pivot.index)

    matrix = pivot.values.astype(float)
    # log1p na udziałach + standaryzacja wierszy (profil kształtu trendu)
    matrix_log = np.log1p(matrix)
    scaler = StandardScaler()
    matrix_scaled = scaler.fit_transform(matrix_log)

    vector_rows = []
    for i, lang in enumerate(languages):
        for j, month in enumerate(months):
            vector_rows.append(
                {
                    "language": lang,
                    "month": month,
                    "share_pct": matrix[i, j],
                    "feature_value": matrix_scaled[i, j],
                }
            )

    vectors_long = pd.DataFrame(vector_rows)
    return vectors_long, matrix_scaled, languages, months


def main() -> None:
    shares = pd.read_csv(PROCESSED_SHARES)
    vectors_long, _, languages, months = build_language_vectors(shares)

    meta = pd.DataFrame(
        {
            "language": languages,
            "vector_length": [len(months)] * len(languages),
            "normalization": ["log1p + StandardScaler per feature"] * len(languages),
            "random_seed": [RANDOM_SEED] * len(languages),
        }
    )
    vectors_long = vectors_long.merge(meta[["language", "vector_length"]], on="language")
    vectors_long.to_csv(PROCESSED_VECTORS, index=False)
    print(f"Saved vectors ({len(languages)} langs x {len(months)} months) -> {PROCESSED_VECTORS}")


if __name__ == "__main__":
    main()
