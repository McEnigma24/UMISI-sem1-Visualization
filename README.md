# UMISI — Ewolucja ekosystemów języków programowania

Wizualizacja zmian popularności języków programowania na GitHubie (2011–2024): trendy, udziały rynku, metryki społeczności oraz porównanie redukcji wymiaru (UMAP vs PaCMAP).

## Szybki start

```bash
pip install -r requirements.txt
python src/run_pipeline.py
```

Na Windows przy błędzie SSL podczas `pip install`:

```bash
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

Następnie otwórz [`index.html`](index.html) w przeglądarce (dwuklik — specyfikacje wykresów są wbudowane w HTML).

Alternatywnie lokalny serwer (gdy przeglądarka blokuje skrypty z CDN):

```bash
.\serve.ps1
# lub: python -m http.server 8000
```

Potem wejdź na http://localhost:8000/index.html

## Struktura repozytorium

```
data/           # raw + processed CSV
docs/scope.md   # zakres, metryki, języki
sql/            # zapytanie BigQuery (opcja C)
src/            # pipeline Python
viz/            # wykresy Vega-Lite + index.html
report.md       # interpretacja wyników
```

## Pipeline

1. `generate_sample_data.py` — przykładowy eksport (offline) lub własny CSV z BQ
2. `etl.py` — agregacja, udziały, koncentracja
3. `build_vectors.py` — wektory czasowe per język
4. `dim_reduction.py` — UMAP + PaCMAP
5. `build_viz.py` — pliki Vega-Lite i HTML

Własne dane BigQuery: zapisz wynik SQL do `data/raw/`, uruchom `python src/etl.py --input ścieżka.csv` i kolejne kroki 3–5.

## Wymagania zadania

| Wymaganie | Realizacja |
|-----------|------------|
| Przygotowanie danych | `sql/`, `src/etl.py`, `data/README.md` |
| Popularność w czasie | `viz/trends_line.vl.json`, `shares_stacked.vl.json` |
| Aktywność społeczności | `viz/community_comparison.vl.json`, `bump_chart.vl.json` |
| Wykresy interaktywne | Vega-Lite + legenda, tooltips, brush |
| Dominujące technologie | `viz/treemap.vl.json`, `concentration.vl.json` |
| Redukcja wymiaru | `viz/dim_reduction.vl.json` (UMAP vs PaCMAP) |
| Interpretacja | `report.md` |

Szczegóły: [project/task.txt](project/task.txt).
