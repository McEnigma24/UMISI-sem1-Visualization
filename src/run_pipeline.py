"""Uruchamia pełny pipeline: (opcjonalnie sample) -> ETL -> wektory -> DR -> wizualizacje."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent


def _use_fake_sample() -> bool:
    return os.environ.get("UMISI_USE_FAKE_SAMPLE", "").strip().lower() in ("1", "true", "yes")


def run(script: str) -> None:
    print(f"\n=== {script} ===")
    subprocess.run(
        [sys.executable, str(SRC / script)],
        check=True,
        cwd=str(SRC),
    )


def main() -> None:
    if _use_fake_sample():
        print("UMISI_USE_FAKE_SAMPLE=1 → generuję data/raw/fake/monthly_activity_sample.csv, potem ETL.")
        run("generate_sample_data.py")
    else:
        print("ETL z domyślnego pliku real (src/config.RAW_INPUT). Fake: UMISI_USE_FAKE_SAMPLE=1 lub etl.py --input …")
    run("etl.py")
    run("build_vectors.py")
    run("dim_reduction.py")
    run("eda.py")
    run("build_viz.py")
    run("build_yearly_viewer.py")
    run("build_market_snapshot_viewer.py")
    run("build_concentration_viewer.py")
    print("\nPipeline done. Open index.html in a browser.")


if __name__ == "__main__":
    main()
