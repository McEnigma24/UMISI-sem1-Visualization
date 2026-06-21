"""Analiza eksploracyjna: statystyki, klastrowanie, obserwacje nietypowe."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from config import (
    DATA_PROCESSED,
    PROCESSED_DIM_REDUCTION,
    PROCESSED_LANGUAGE_PROFILES,
    PROCESSED_PCA_VARIANCE,
    PROCESSED_SHARES,
    RANDOM_SEED,
)
from dim_reduction import load_feature_matrix


def language_summary(shares: pd.DataFrame) -> pd.DataFrame:
    shares = shares.copy()
    shares["year"] = shares["month"].astype(str).str[:4].astype(int)
    rows: list[dict] = []

    for language, group in shares.groupby("language"):
        by_year = group.groupby("year")["share_pct"].mean()
        first_year = int(by_year.index.min())
        last_year = int(by_year.index.max())
        x = np.arange(len(group))
        slope = float(np.polyfit(x, group["share_pct"].values, 1)[0]) if len(group) > 1 else 0.0

        rows.append(
            {
                "language": language,
                "mean_share_pct": round(group["share_pct"].mean(), 4),
                "std_share_pct": round(group["share_pct"].std(), 4),
                "min_share_pct": round(group["share_pct"].min(), 4),
                "max_share_pct": round(group["share_pct"].max(), 4),
                "share_first_year": round(by_year.loc[first_year], 4),
                "share_last_year": round(by_year.loc[last_year], 4),
                "share_change_pp": round(by_year.loc[last_year] - by_year.loc[first_year], 4),
                "trend_slope": round(slope, 6),
                "first_year": first_year,
                "last_year": last_year,
            }
        )

    summary = pd.DataFrame(rows)
    vol_z = (summary["std_share_pct"] - summary["std_share_pct"].mean()) / summary[
        "std_share_pct"
    ].std(ddof=0)
    change_z = (summary["share_change_pp"] - summary["share_change_pp"].mean()) / summary[
        "share_change_pp"
    ].std(ddof=0)
    summary["volatility_z"] = vol_z.round(3)
    summary["change_z"] = change_z.round(3)
    summary["is_outlier"] = (summary["volatility_z"].abs() > 1.5) | (
        summary["change_z"].abs() > 1.5
    )
    return summary.sort_values("mean_share_pct", ascending=False)


def cluster_languages(matrix: np.ndarray, languages: list[str], k: int = 3) -> pd.DataFrame:
    labels = KMeans(n_clusters=k, random_state=RANDOM_SEED, n_init=10).fit_predict(matrix)
    return pd.DataFrame({"language": languages, "cluster": labels.astype(int)})


def pca_explained_variance(matrix: np.ndarray, n_components: int = 5) -> pd.DataFrame:
    n_components = min(n_components, matrix.shape[0], matrix.shape[1])
    model = PCA(n_components=n_components, random_state=RANDOM_SEED)
    model.fit(matrix)
    return pd.DataFrame(
        {
            "component": [f"PC{i + 1}" for i in range(n_components)],
            "explained_variance_ratio": model.explained_variance_ratio_.round(4),
            "cumulative_ratio": np.cumsum(model.explained_variance_ratio_).round(4),
        }
    )


def build_language_profiles(
    summary: pd.DataFrame, clusters: pd.DataFrame, dim: pd.DataFrame
) -> pd.DataFrame:
    profiles = summary.merge(clusters, on="language", how="left")
    pca_coords = dim[dim["method"] == "pca"][["language", "x", "y"]].rename(
        columns={"x": "pca_x", "y": "pca_y"}
    )
    return profiles.merge(pca_coords, on="language", how="left")


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    shares = pd.read_csv(PROCESSED_SHARES)
    matrix, languages = load_feature_matrix(shares)

    summary = language_summary(shares)
    clusters = cluster_languages(matrix, languages)
    variance = pca_explained_variance(matrix)
    dim = pd.read_csv(PROCESSED_DIM_REDUCTION)
    profiles = build_language_profiles(summary, clusters, dim)

    summary.to_csv(DATA_PROCESSED / "eda_language_summary.csv", index=False)
    clusters.to_csv(DATA_PROCESSED / "language_clusters.csv", index=False)
    variance.to_csv(PROCESSED_PCA_VARIANCE, index=False)
    profiles.to_csv(PROCESSED_LANGUAGE_PROFILES, index=False)

    outliers = profiles.loc[profiles["is_outlier"], "language"].tolist()
    print(f"EDA done. Outliers flagged: {', '.join(outliers) or 'none'}")
    print(f"Clusters: {profiles.groupby('cluster')['language'].apply(list).to_dict()}")


if __name__ == "__main__":
    main()
