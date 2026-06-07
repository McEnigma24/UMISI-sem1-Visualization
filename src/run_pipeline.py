"""Uruchamia pełny pipeline: sample -> ETL -> wektory -> DR -> wizualizacje."""

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
    run("generate_sample_data.py")
    run("etl.py")
    run("build_vectors.py")
    run("dim_reduction.py")
    run("build_viz.py")
    print("\nPipeline done. Open index.html in a browser.")


if __name__ == "__main__":
    main()
