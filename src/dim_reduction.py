"""Redukcja wymiaru: PCA, kernel PCA, t-SNE, UMAP, TriMAP, PaCMAP, OpenTSNE (klasa FIt-SNE)."""

from __future__ import annotations

import numpy as np
import pacmap
import pandas as pd
import trimap
import umap
from openTSNE import TSNE as OpenTSNE
from sklearn.decomposition import PCA, KernelPCA
from sklearn.manifold import TSNE as SklearnTSNE
from sklearn.preprocessing import StandardScaler

from config import (
    PROCESSED_DIM_REDUCTION,
    PROCESSED_DIM_REDUCTION_3D,
    PROCESSED_SHARES,
    RANDOM_SEED,
)

# Kolejnosc wykresow (od gory) + etykiety w wizualizacji
METHOD_ORDER: list[tuple[str, str]] = [
    ("pca", "PCA"),
    ("kpca", "Kernel PCA (RBF)"),
    ("tsne", "t-SNE (sklearn)"),
    ("umap", "UMAP"),
    ("trimap", "TriMAP"),
    ("pacmap", "PaCMAP"),
    ("opentsne", "OpenTSNE (t-SNE / FIt-SNE class)"),
]

METHOD_LABELS: dict[str, str] = dict(METHOD_ORDER)


def load_feature_matrix(shares: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    pivot = shares.pivot(index="language", columns="month", values="share_pct").fillna(0.0)
    languages = list(pivot.index)
    matrix = np.log1p(pivot.values.astype(float))
    matrix = StandardScaler().fit_transform(matrix)
    return matrix, languages


def compute_embeddings(matrix: np.ndarray, n_components: int) -> dict[str, np.ndarray]:
    """Oblicza embeddingi 2D (n_components=2) lub 3D (n_components=3) dla wszystkich metod."""
    if n_components not in (2, 3):
        raise ValueError("n_components must be 2 or 3")
    n = matrix.shape[0]
    if n < 3:
        raise ValueError("Need at least 3 languages for t-SNE / neighbors-based methods.")

    n_neighbors = max(5, min(15, n - 1))
    perp_tsne = max(2, min(10, n - 1))
    perp_ot = max(2, min(8, (n - 1) // 3))

    embeddings: dict[str, np.ndarray] = {}

    embeddings["pca"] = PCA(n_components=n_components, random_state=RANDOM_SEED).fit_transform(matrix)

    embeddings["kpca"] = KernelPCA(
        n_components=n_components,
        kernel="rbf",
        gamma=None,
        random_state=RANDOM_SEED,
        eigen_solver="arpack",
    ).fit_transform(matrix)

    embeddings["tsne"] = SklearnTSNE(
        n_components=n_components,
        perplexity=perp_tsne,
        max_iter=2000,
        init="pca",
        learning_rate="auto",
        random_state=RANDOM_SEED,
    ).fit_transform(matrix)

    embeddings["umap"] = umap.UMAP(
        n_components=n_components,
        n_neighbors=n_neighbors,
        min_dist=0.12,
        spread=1.0,
        metric="euclidean",
        random_state=RANDOM_SEED,
    ).fit_transform(matrix)

    tri = trimap.TRIMAP(
        n_dims=n_components,
        n_inliers=min(12, n - 1),
        n_outliers=min(4, max(1, n // 5)),
        n_random=min(3, max(1, n // 7)),
        n_iters=450,
        apply_pca=True,
        verbose=False,
    )
    embeddings["trimap"] = tri.fit_transform(matrix)

    pac_neighbors = max(5, min(10, n - 1))
    embeddings["pacmap"] = pacmap.PaCMAP(
        n_components=n_components,
        n_neighbors=pac_neighbors,
        MN_ratio=0.5,
        FP_ratio=2.0,
        random_state=RANDOM_SEED,
    ).fit_transform(matrix, init="pca")

    ot = OpenTSNE(
        n_components=n_components,
        perplexity=float(perp_ot),
        random_state=RANDOM_SEED,
        n_jobs=1,
        n_iter=500,
    )
    emb_ot = ot.fit(matrix)
    embeddings["opentsne"] = np.asarray(emb_ot, dtype=np.float64)

    return embeddings


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
        label = METHOD_LABELS.get(method, method)
        for i, lang in enumerate(languages):
            meta = totals.loc[totals["language"] == lang].iloc[0]
            row: dict = {
                "language": lang,
                "method": method,
                "method_label": label,
                "x": float(coords[i, 0]),
                "y": float(coords[i, 1]),
                "total_push_events": int(meta["total_push_events"]),
                "avg_share_pct": float(meta["avg_share_pct"]),
                "total_unique_actors": int(meta["total_unique_actors"]),
            }
            if coords.shape[1] >= 3:
                row["z"] = float(coords[i, 2])
            rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    shares = pd.read_csv(PROCESSED_SHARES)
    matrix, languages = load_feature_matrix(shares)

    emb2 = compute_embeddings(matrix, 2)
    out2 = build_dim_reduction_table(shares, emb2, languages)
    out2.to_csv(PROCESSED_DIM_REDUCTION, index=False)

    emb3 = compute_embeddings(matrix, 3)
    out3 = build_dim_reduction_table(shares, emb3, languages)
    out3.to_csv(PROCESSED_DIM_REDUCTION_3D, index=False)

    names = ", ".join(dict(METHOD_ORDER).keys())
    print(f"Saved 2D embeddings ({names}) -> {PROCESSED_DIM_REDUCTION}")
    print(f"Saved 3D embeddings ({names}) -> {PROCESSED_DIM_REDUCTION_3D}")


if __name__ == "__main__":
    main()
