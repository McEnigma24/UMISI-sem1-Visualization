"""Centralna konfiguracja projektu."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
VIZ_DIR = ROOT / "viz"

RANDOM_SEED = 42

START_MONTH = "2011-01"
END_MONTH = "2024-12"

LANGUAGES = [
    "JavaScript",
    "Python",
    "Java",
    "TypeScript",
    "C#",
    "C++",
    "Go",
    "Ruby",
    "PHP",
    "Rust",
    "Kotlin",
    "Swift",
]

RAW_INPUT = DATA_RAW / "monthly_activity_sample.csv"
PROCESSED_MONTHLY = DATA_PROCESSED / "monthly_activity.csv"
PROCESSED_SHARES = DATA_PROCESSED / "monthly_shares.csv"
PROCESSED_COMMUNITY = DATA_PROCESSED / "community_metrics.csv"
PROCESSED_CONCENTRATION = DATA_PROCESSED / "market_concentration.csv"
PROCESSED_VECTORS = DATA_PROCESSED / "language_vectors.csv"
PROCESSED_DIM_REDUCTION = DATA_PROCESSED / "dim_reduction.csv"
