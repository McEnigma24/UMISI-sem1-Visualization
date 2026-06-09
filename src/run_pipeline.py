"""Uruchamia pełny pipeline: ETL -> wektory -> DR -> EDA -> wizualizacje."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent


def run(script: str) -> None:
    print(f"\n=== {script} ===")
    subprocess.run(
        [sys.executable, str(SRC / script)],
        check=True,
        cwd=str(SRC),
    )


def main() -> None:
    print("ETL z domyślnego pliku wejściowego (src/config.RAW_INPUT). Inny plik: etl.py --input …")
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
