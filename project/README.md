# UMISI — Ewolucja ekosystemów języków programowania

Interaktywny **dashboard** (Grupa 1 UMISI): trendy, EDA, klastrowanie, redukcja wymiaru (PCA, kernel PCA, t-SNE, UMAP, TriMAP, PaCMAP, OpenTSNE) — popularność języków na GitHubie (2011–2026, ostatni kwartał w danych: 2026-04-01).

## Szybki start

```bash
pip install -r requirements.txt
python src/run_pipeline.py
```

Domyślnie ETL wczytuje **`data/raw/real/manyLanguages_added.csv`** (eksport BQ z uzupełnionymi lukami kwartalnymi — patrz niżej). Aby użyć innego eksportu: `python src/etl.py --input ścieżka.csv` i dalsze kroki pipeline’u.

**Luka 2013–2014 w surowym eksporcie:** jeśli plik z BigQuery ma skok z 2012 do 2015, to zwykle nie wynika z „braku GitHuba”, tylko z eksportu (węższy zakres `_TABLE_SUFFIX`, błąd w zapytaniu, scalenie dwóch częściowych wyników, inny dataset). W tabeli `githubarchive.day.20*` sufiksy `130*` i `140*` **powinny** wpaść w filtr `BETWEEN '110101' AND '241231'` — warto w BQ sprawdzić `INFORMATION_SCHEMA.TABLES` lub `COUNT(*)` pogrupowane po roku. Żeby wykresy nie miały dziury czasowej, można uzupełnić brakujące kwartały interpolacją liniową:

```bash
python src/interpolate_quarter_gaps.py --input data/raw/real/manyLanguages.csv --output data/raw/real/manyLanguages_added.csv
```

(albo `--input` / `--output` wskazujące na ten sam plik `_added`, jeśli edytujesz go w miejscu).

```bash
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

Następnie otwórz [`index.html`](index.html) w przeglądarce (dwuklik — specyfikacje wykresów są wbudowane w HTML).

**Interpretacja trendów aktywności** (skok ok. 2015, pik 2021–2023 vs COVID, spadek po 2023): [report.md — §3.1](report.md) („Trendy aktywnosci — co mierzymy…”).

Alternatywnie lokalny serwer (gdy przeglądarka blokuje skrypty z CDN):

```bash
.\serve.ps1
# lub: python -m http.server 8000
```

Potem wejdź na http://localhost:8000/index.html

## Jak działa pipeline (krok po kroku, high level)

Projekt **nie** trzyma gotowych wykresów w repozytorium jako jedynego źródła prawdy: **wizualizacje generujemy skryptami Python** z plików CSV w `data/processed/`. Po uruchomieniu `python src/run_pipeline.py` (albo pojedynczych kroków) powstają pliki w `viz/` oraz główny [`index.html`](index.html) (kopia leży też w `viz/index.html`).

### Przepływ danych (idea)

1. **Wejście:** aktywność per język (`push_events`, `unique_actors`) — przykładowo z [`sql/bigquery_export.sql`](sql/bigquery_export.sql) (**kwartały**) albo wbudowany generator (**miesiące**).
2. **Przetwarzanie:** filtr wybranych języków, udziały procentowe, metryki rynku i społeczności, wektory profili czasowych.
3. **Analityka:** EDA (outliery, klastry, wariancja PCA), redukcja wymiaru 2D i 3D.
4. **Wyjście wizualne:** Vega-Lite (JSON) + kilka statycznych stron HTML w **iframe** + **Plotly 3D** osadzony w tym samym `index.html` (bez iframe), scalone w dashboard.

### Kolejność skryptów (zgodna z `run_pipeline.py`)

| Krok | Skrypt | Co robi |
|------|--------|---------|
| 1 | `etl.py` | Czyta **`data/raw/real/manyLanguages_added.csv`** (eksport BQ / interpolowane kwartały); inny plik: `python src/etl.py --input ścieżka.csv`. |
| 2 | `build_vectors.py` | Buduje długi format wektorów (`language_vectors.csv`) — baza pod profile i redukcję wymiaru. |
| 3 | `dim_reduction.py` | Z macierzy profili (udziały w czasie, `log1p` + standaryzacja) liczy **siedem metod** w **2D** i **3D** → `dim_reduction.csv`, `dim_reduction_3d.csv`. |
| 4 | `eda.py` | Statystyki per język, klastry KMeans, wykładnicza wariancja PCA, `language_profiles.csv` itd. |
| 5 | `build_viz.py` | **Główny generator wykresów:** Altair → **Vega-Lite** (`*.vl.json`), Plotly → `dim_reduction_3d.spec.json` + wbudowanie 3D w `index.html` + opcjonalnie `dim_reduction_3d.html`, kopiuje CSV do `viz/data/`, składa **`index.html`** z JSON-ami Vega i iframe’ami viewerów. |
| 6 | `build_yearly_viewer.py` | Osobna strona **rocznego** podglądu (treemap / siatka), ładowana w iframe z dashboardu. |
| 7 | `build_market_snapshot_viewer.py` | Strona **mapy udziałów** (kwartalna „mapa”), iframe. |
| 8 | `build_concentration_viewer.py` | Strona **koncentracji rynku**, iframe. |

**Źródło danych:** domyślnie `data/raw/real/manyLanguages_added.csv` (eksport BigQuery).

Własny eksport BigQuery: zapisz CSV do `data/raw/real/`, ustaw ścieżkę w `src/config.py` (`RAW_INPUT_REAL`) albo `python src/etl.py --input ścieżka.csv`, potem **kroki 2–8** (albo cały `run_pipeline.py`).

### Jak dokładnie powstają wizualizacje

- **Wykresy Vega-Lite (większość dashboardu):** `build_viz.py` buduje obiekty **Altair**, zapisuje je jako `viz/*.vl.json`. W `index.html` każda specyfikacja jest w tagu `<script type="application/json">`, a **vega-embed** (ładowany z CDN) renderuje ją w `<div id="chart-…">`. Dzięki temu wykresy są interaktywne (tooltip, zoom tam gdzie zdefiniowano) bez osobnego serwera aplikacji.
- **Wykres 3D:** `build_viz.py` czyta `dim_reduction_3d.csv`, buduje figurę Plotly, zapisuje **`viz/dim_reduction_3d.spec.json`** (JSON figury) i **`viz/dim_reduction_3d.html`** (samodzielny plik z dołączonym Plotly). W **`index.html`** wykres 3D jest **renderowany w tej samej stronie** (dekodowany ze specyfikacji w base64), żeby działało też przy otwarciu `index.html` z dysku (`file://` — zagnieżdżone iframe z lokalnymi plikami bywa blokowane).
- **Trzy „viewery” HTML:** osobne skrypty (kroki 6–8) generują samodzielne strony z własnym layoutem i często **postMessage** do dopasowania wysokości iframe — to nadal **generowane pliki**, nie ręcznie pisany front produkcyjny.

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

- Dane: `etl.py` → `build_vectors.py` → `dim_reduction.py` → `eda.py`
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
