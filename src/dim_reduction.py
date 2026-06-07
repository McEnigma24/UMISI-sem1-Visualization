"""Redukcja wymiaru: UMAP vs PaCMAP na wektorach profili języków."""

from __future__ import annotations

import numpy as np
import pacmap
import pandas as pd
import umap
from sklearn.preprocessing import StandardScaler

from config import PROCESSED_DIM_REDUCTION, PROCESSED_SHARES, RANDOM_SEED


def load_feature_matrix(shares: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    pivot = shares.pivot(index="language", columns="month", values="share_pct").fillna(0.0)
    languages = list(pivot.index)
    matrix = np.log1p(pivot.values.astype(float))
    matrix = StandardScaler().fit_transform(matrix)
    return matrix, languages


def compute_embeddings(matrix: np.ndarray) -> dict[str, np.ndarray]:
    umap_emb = umap.UMAP(
        n_components=2,
        n_neighbors=min(8, len(matrix) - 1),
        min_dist=0.25,
        metric="euclidean",
        random_state=RANDOM_SEED,
    ).fit_transform(matrix)

    pacmap_emb = pacmap.PaCMAP(
        n_components=2,
        n_neighbors=min(8, len(matrix) - 1),
        MN_ratio=0.5,
        FP_ratio=2.0,
        random_state=RANDOM_SEED,
    ).fit_transform(matrix, init="pca")

    return {"umap": umap_emb, "pacmap": pacmap_emb}


def build_dim_reduction_table(
    shares: pd.DataFrame, embeddings: dict[str, np.ndarray], languages: list[str]
) -> pd.DataFrame:
    totals = shares.groupby("language", as_index=False).agg(
        total_push_events=("push_events", "sum"),
        avg_share_pct=("share_pct", "mean"),
        total_unique_actors=("unique_actors", "sum"),
    )

    rows = []
    for method, coords in embeddings.items():
        for i, lang in enumerate(languages):
            meta = totals.loc[totals["language"] == lang].iloc[0]
            rows.append(
                {
                    "language": lang,
                    "method": method,
                    "x": float(coords[i, 0]),
                    "y": float(coords[i, 1]),
                    "total_push_events": int(meta["total_push_events"]),
                    "avg_share_pct": float(meta["avg_share_pct"]),
                    "total_unique_actors": int(meta["total_unique_actors"]),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    shares = pd.read_csv(PROCESSED_SHARES)
    matrix, languages = load_feature_matrix(shares)
    embeddings = compute_embeddings(matrix)
    out = build_dim_reduction_table(shares, embeddings, languages)
    out.to_csv(PROCESSED_DIM_REDUCTION, index=False)
    print(f"Saved embeddings -> {PROCESSED_DIM_REDUCTION}")


if __name__ == "__main__":
    main()
