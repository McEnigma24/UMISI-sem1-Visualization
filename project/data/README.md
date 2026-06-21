# Dane projektu

## Struktura

| Ścieżka | Opis |
|---------|------|
| `raw/real/manyLanguages.csv` | Surowy eksport BQ (kwartały); może mieć luki czasowe (np. brak 2013–2014) |
| `raw/real/manyLanguages_added.csv` | **Domyślne wejście ETL:** ten sam schemat po **`interpolate_quarter_gaps.py`** (wypełnienie brakujących kwartałów interpolacją liniową) |
| Surowy eksport z BQ ([`sql/bigquery_export.sql`](../sql/bigquery_export.sql)) | Możesz podmienić plik w `raw/real/` i zaktualizować `RAW_INPUT_REAL` w `src/config.py` albo użyć `etl.py --input …`. Uzupełnienia czasowe: [`sql/bigquery_export_2012_2015.sql`](../sql/bigquery_export_2012_2015.sql), [`sql/bigquery_export_2025_2026.sql`](../sql/bigquery_export_2025_2026.sql). |
| `processed/monthly_activity.csv` | Zagregowane liczniki per język (nadal jedna kolumna czasu `month` w pliku — miesiąc lub początek kwartału) |
| `processed/monthly_shares.csv` | Udziały (`share`, `share_pct`) w aktywności miesięcznej |
| `processed/yearly_shares.csv` | Średnie roczne udziały i aktywność per język (`avg_share_pct`) |
| `processed/community_metrics.csv` | Metryki społeczności: `events_per_actor`, `actor_rank`, `actors_stack` (słupki gdy brak `unique_actors`), `events_per_actor_viz` (linia średniej przy brakującym EPA) |
| `processed/market_concentration.csv` | HHI i udział top 3 języków per miesiąc |
| `processed/language_vectors.csv` | Długi format wektorów cech (profil czasowy) |
| `processed/dim_reduction_3d.csv` | Te same metody co 2D: współrzędne **x, y, z** (embedding 3D) |
| `processed/eda_language_summary.csv` | EDA: statystyki i trendy per język |
| `processed/language_profiles.csv` | Profile + klastry + flaga outlier |
| `processed/language_clusters.csv` | KMeans (k=3) na wektorach profili |
| `processed/pca_explained_variance.csv` | Wyjaśniona wariancja składowych PCA |

## Schemat surowego CSV

```text
month,language,push_events,unique_actors
2011-01,Python,8200,3400
...
```

Alternatywa z BigQuery (kwartały): pierwsza kolumna może nazywać się **`quarter`** z wartościami `YYYY-MM-DD` (pierwszy dzień kwartału, np. `2020-01-01`).

- **month** / **quarter** — oś czasu (miesiąc `YYYY-MM` albo początek kwartału); przy `quarter` ETL zapisuje dalej jako `month` w plikach processed
- **language** — nazwa języka z pola `repo.language`
- **push_events** — liczba zdarzeń `PushEvent` (**ważone** w eksporcie BQ: suma `bytes_lang / sum(bytes_repo)` na push; może być niecałkowita)
- **unique_actors** — liczba unikalnych `actor.id`

Dłuższa interpretacja **trendów absolutnych** (ważone `push_events`, skok ok. 2015, lata 2021–2026 vs narracja „COVID”): [../report.md](../report.md) (sekcja 3.1).

## Odtworzenie

```bash
pip install -r requirements.txt
python src/run_pipeline.py
```

Domyślnie ETL bierze **`data/raw/real/manyLanguages_added.csv`** (eksport BigQuery). Inny plik wejściowy: `python src/etl.py --input ścieżka.csv` i kolejne kroki pipeline’u.

Z własnym eksportem BigQuery:

```bash
python src/etl.py --input data/raw/real/twoj_eksport.csv
python src/build_vectors.py
python src/dim_reduction.py
python src/build_viz.py
```
