"""Konwersja wykresow SVG -> PDF i kopiowanie zrzutow PNG do figures/."""
import shutil
from pathlib import Path
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

HERE = Path(__file__).resolve().parent
PICKS = HERE.parent / "picks"
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)

svg_map = {
    "visualization (1).svg": "trends_line.pdf",
    "visualization (2).svg": "shares_stacked.pdf",
    "visualization (3).svg": "community_comparison.pdf",
    "visualization (4).svg": "share_change.pdf",
    "visualization (5).svg": "clusters.pdf",
    "visualization (6).svg": "dim_reduction.pdf",
}

png_map = {
    "Screenshot 2026-06-09 214905.png": "market_snapshot.png",
    "Screenshot 2026-06-09 214912.png": "treemap.png",
}

for src, dst in svg_map.items():
    drawing = svg2rlg(str(PICKS / src))
    renderPDF.drawToFile(drawing, str(OUT / dst))
    print("PDF:", dst)

for src, dst in png_map.items():
    shutil.copyfile(PICKS / src, OUT / dst)
    print("PNG:", dst)

print("DONE")
