"""Centralna konfiguracja projektu."""

from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
VIZ_DIR = ROOT / "viz"

RANDOM_SEED = 42
START_MONTH = "2011-01"
END_MONTH = "2026-04"

# 21 najpopularniejszych jezykow wg aktywnosci PushEvent na GitHubie (GH Archive / Octoverse).
LANGUAGES = [
    "JavaScript",
    "Python",
    "Java",
    "TypeScript",
    "C#",
    "C++",
    "PHP",
    "C",
    "Go",
    "Ruby",
    "Rust",
    "Kotlin",
    "Swift",
    "Dart",
    "Scala",
    "R",
    "Objective-C",
    "Lua",
    "Haskell",
    "Julia",
    "Perl",
]

LANGUAGE_PALETTE = [
    "#4e79a7",
    "#f28e2b",
    "#e15759",
    "#76b7b2",
    "#59a14f",
    "#edc948",
    "#b07aa1",
    "#ff9da7",
    "#9c755f",
    "#bab0ac",
    "#17becf",
    "#bcbd22",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#636efa",
    "#ef553b",
    "#00cc96",
    "#ab63fa",
    "#ffa15a",
]

LANGUAGE_COLORS = {
    lang: LANGUAGE_PALETTE[i % len(LANGUAGE_PALETTE)] for i, lang in enumerate(LANGUAGES)
}

# Domyślnie eksport BigQuery (kwartalny). Syntetyczne: ustaw UMISI_USE_FAKE_SAMPLE=1 albo:
#   python src/etl.py --input data/raw/fake/monthly_activity_sample.csv
RAW_INPUT_REAL = DATA_RAW / "real" / "manyLanguages_added.csv"
RAW_INPUT_FAKE = DATA_RAW / "fake" / "monthly_activity_sample.csv"

USE_FAKE_SAMPLE_RAW = os.environ.get("UMISI_USE_FAKE_SAMPLE", "").strip().lower() in ( "1", "true", "yes",)
RAW_INPUT = RAW_INPUT_FAKE if USE_FAKE_SAMPLE_RAW else RAW_INPUT_REAL
PROCESSED_MONTHLY = DATA_PROCESSED / "monthly_activity.csv"
PROCESSED_SHARES = DATA_PROCESSED / "monthly_shares.csv"
PROCESSED_COMMUNITY = DATA_PROCESSED / "community_metrics.csv"
PROCESSED_CONCENTRATION = DATA_PROCESSED / "market_concentration.csv"
PROCESSED_VECTORS = DATA_PROCESSED / "language_vectors.csv"
PROCESSED_DIM_REDUCTION = DATA_PROCESSED / "dim_reduction.csv"
PROCESSED_DIM_REDUCTION_3D = DATA_PROCESSED / "dim_reduction_3d.csv"
PROCESSED_PCA_VARIANCE = DATA_PROCESSED / "pca_explained_variance.csv"
PROCESSED_LANGUAGE_PROFILES = DATA_PROCESSED / "language_profiles.csv"

