# UMISI — Ewolucja ekosystemów języków programowania

Interaktywny **dashboard** (Grupa 1 UMISI): trendy, EDA, klastrowanie, redukcja wymiaru (PCA, kernel PCA, t-SNE, UMAP, TriMAP, PaCMAP, OpenTSNE) — popularność języków na GitHubie (2011–2024).

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

## Jak działa pipeline (krok po kroku, high level)

Projekt **nie** trzyma gotowych wykresów w repozytorium jako jedynego źródła prawdy: **wizualizacje generujemy skryptami Python** z plików CSV w `data/processed/`. Po uruchomieniu `python src/run_pipeline.py` (albo pojedynczych kroków) powstają pliki w `viz/` oraz główny [`index.html`](index.html) (kopia leży też w `viz/index.html`).

### Przepływ danych (idea)

1. **Wejście:** miesięczna aktywność per język (`push_events`, `unique_actors`) — przykładowo z [`sql/bigquery_export.sql`](sql/bigquery_export.sql) albo wbudowany generator.
2. **Przetwarzanie:** filtr wybranych języków, udziały procentowe, metryki rynku i społeczności, wektory profili czasowych.
3. **Analityka:** EDA (outliery, klastry, wariancja PCA), redukcja wymiaru 2D i 3D.
4. **Wyjście wizualne:** Vega-Lite (JSON) + kilka statycznych stron HTML w **iframe** + **Plotly 3D** osadzony w tym samym `index.html` (bez iframe), scalone w dashboard.

### Kolejność skryptów (zgodna z `run_pipeline.py`)

| Krok | Skrypt | Co robi |
|------|--------|---------|
| 1 | `generate_sample_data.py` | Zapisuje **przykładowy** `data/raw/monthly_activity_sample.csv` (offline, deterministyczny seed). Przy każdym uruchomieniu **nadpisuje** ten plik. Dane z BQ wczytuj przez `etl.py --input …` albo podmień plik w `data/raw/` zgodnie z [`data/README.md`](data/README.md). |
| 2 | `etl.py` | Czyta raw, zapisuje m.in. `monthly_activity.csv`, `monthly_shares.csv`, `community_metrics.csv`, `market_concentration.csv` w `data/processed/`. |
| 3 | `build_vectors.py` | Buduje długi format wektorów (`language_vectors.csv`) — baza pod profile i redukcję wymiaru. |
| 4 | `dim_reduction.py` | Z macierzy profili (udziały w czasie, `log1p` + standaryzacja) liczy **siedem metod** w **2D** i **3D** → `dim_reduction.csv`, `dim_reduction_3d.csv`. |
| 5 | `eda.py` | Statystyki per język, klastry KMeans, wykładnicza wariancja PCA, `language_profiles.csv` itd. |
| 6 | `build_viz.py` | **Główny generator wykresów:** Altair → **Vega-Lite** (`*.vl.json`), Plotly → `dim_reduction_3d.spec.json` + wbudowanie 3D w `index.html` + opcjonalnie `dim_reduction_3d.html`, kopiuje CSV do `viz/data/`, składa **`index.html`** z JSON-ami Vega i iframe’ami viewerów. |
| 7 | `build_yearly_viewer.py` | Osobna strona **rocznego** podglądu (treemap / siatka), ładowana w iframe z dashboardu. |
| 8 | `build_market_snapshot_viewer.py` | Strona **mapy udziałów** (kwartalna „mapa”), iframe. |
| 9 | `build_concentration_viewer.py` | Strona **koncentracji rynku**, iframe. |

Własne dane z BigQuery: zapisz eksport do `data/raw/`, potem `python src/etl.py --input ścieżka.csv` i **kroki 3–9** (albo cały `run_pipeline.py` po podmianie pliku raw).

### Jak dokładnie powstają wizualizacje

- **Wykresy Vega-Lite (większość dashboardu):** `build_viz.py` buduje obiekty **Altair**, zapisuje je jako `viz/*.vl.json`. W `index.html` każda specyfikacja jest w tagu `<script type="application/json">`, a **vega-embed** (ładowany z CDN) renderuje ją w `<div id="chart-…">`. Dzięki temu wykresy są interaktywne (tooltip, zoom tam gdzie zdefiniowano) bez osobnego serwera aplikacji.
- **Wykres 3D:** `build_viz.py` czyta `dim_reduction_3d.csv`, buduje figurę Plotly, zapisuje **`viz/dim_reduction_3d.spec.json`** (JSON figury) i **`viz/dim_reduction_3d.html`** (samodzielny plik z dołączonym Plotly). W **`index.html`** wykres 3D jest **renderowany w tej samej stronie** (dekodowany ze specyfikacji w base64), żeby działało też przy otwarciu `index.html` z dysku (`file://` — zagnieżdżone iframe z lokalnymi plikami bywa blokowane).
- **Trzy „viewery” HTML:** osobne skrypty (kroki 7–9) generują samodzielne strony z własnym layoutem i często **postMessage** do dopasowania wysokości iframe — to nadal **generowane pliki**, nie ręcznie pisany front produkcyjny.

Jeśli zmienisz wyłącznie kod wykresów w `build_viz.py` / viewerach, wystarczy ponownie uruchomić **`build_viz.py`** (i ewentualnie pojedyncze `build_*_viewer.py`). Jeśli zmieniłeś **`dim_reduction.py`** lub dane wejściowe do embeddingów, uruchom ponownie **`dim_reduction.py`**, potem **`eda.py`** (profile używają współrzędnych PCA z CSV) i na końcu **`build_viz.py`** oraz buildery viewerów.

## Struktura repozytorium

```
data/           # raw + processed CSV
docs/scope.md   # zakres, metryki, języki
sql/            # zapytanie BigQuery (opcja C)
src/            # pipeline Python
viz/            # wykresy Vega-Lite + index.html + viewery + Plotly 3D
report.md       # interpretacja wyników
```

## Skrót: same pliki skryptów

- Dane: `generate_sample_data.py` → `etl.py` → `build_vectors.py` → `dim_reduction.py` → `eda.py`
- Widok: `build_viz.py` + `build_yearly_viewer.py` + `build_market_snapshot_viewer.py` + `build_concentration_viewer.py`

## Wymagania zadania

| Wymaganie | Realizacja |
|-----------|------------|
| Dashboard interaktywny | `index.html` |
| EDA + wnioski | `src/eda.py`, `report.md`, `viz/share_change.vl.json` |
| Źródło i preprocessing | `docs/scope.md`, `sql/`, `src/etl.py` |
| Przygotowanie danych | `data/README.md` |
| Popularność w czasie | `viz/trends_line.vl.json`, `shares_stacked.vl.json` |
| Aktywność społeczności | `viz/community_comparison.vl.json`, `bump_chart.vl.json` |
| Dominujące technologie | `viz/treemap.vl.json`, roczne treemapy / bubbles |
| Redukcja wymiaru | `viz/dim_reduction.vl.json` (panel pod panelem, etykiety na punktach) |
| Klastrowanie / outliers | `viz/clusters.vl.json`, `language_profiles.csv` |
| Grupa 1 — checklist | `docs/grupa1_checklist.md` |

Szczegóły: [project/task.txt](project/task.txt).
