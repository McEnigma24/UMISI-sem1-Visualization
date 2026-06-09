# Zgodnosc z wymaganiami Grupy 1 (UMISI)

Zrodlo: [project/task.txt](../project/task.txt), linie 1-6.

| Wymaganie Grupy 1 | Realizacja w projekcie |
|-------------------|------------------------|
| Interaktywna wizualizacja / dashboard | [index.html](../index.html) — Vega-Lite, legenda, tooltips, brush |
| Analiza eksploracyjna (EDA) | [src/eda.py](../src/eda.py), wykresy `share_change`, `pca_variance`, `clusters` |
| Opis zrodla i preprocessingu | [docs/scope.md](scope.md), [data/README.md](../data/README.md), [report.md](../report.md) §2 |
| Najwazniejsze wnioski | [report.md](../report.md) §3-7 |
| Reprezentacja wielowymiarowa | Wektory 168-miesieczne per jezyk ([src/build_vectors.py](../src/build_vectors.py)) |
| Redukcja wymiaru (wiele metod z zajęć) | [src/dim_reduction.py](../src/dim_reduction.py), wykres `dim_reduction.vl.json` |
| Wizualizacja 2D | Siedem paneli (PCA, kPCA, t-SNE, UMAP, TriMAP, PaCMAP, OpenTSNE) + klastry na PC1–PC2 w `clusters.vl.json` |
| Klastrowanie | KMeans k=3 na wektorach profili ([src/eda.py](../src/eda.py)) |
| Analiza trendow | Wykresy liniowe, stacked area, roczne treemapy / bubbles |
| Wykrywanie nietypowych | Flaga `is_outlier` (z-score zmiany udzialu i zmiennosci) w EDA |
