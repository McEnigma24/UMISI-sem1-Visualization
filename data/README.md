# Dane projektu

## Struktura

| Ścieżka | Opis |
|---------|------|
| `raw/monthly_activity_sample.csv` | Surowy eksport (schemat jak BigQuery): `month`, `language`, `push_events`, `unique_actors` |
| `processed/monthly_activity.csv` | Odfiltrowane miesięczne liczniki per język |
| `processed/monthly_shares.csv` | Udziały (`share`, `share_pct`) w aktywności miesięcznej |
| `processed/community_metrics.csv` | Metryki społeczności: `events_per_actor`, `actor_rank` |
| `processed/market_concentration.csv` | HHI i udział top 3 języków per miesiąc |
| `processed/language_vectors.csv` | Długi format wektorów cech (profil czasowy) |
| `processed/dim_reduction.csv` | Współrzędne 2D: UMAP i PaCMAP |

## Schemat surowego CSV

```text
month,language,push_events,unique_actors
2011-01,Python,8200,3400
...
```

- **month** — `YYYY-MM`
- **language** — nazwa języka z pola `repo.language`
- **push_events** — liczba zdarzeń `PushEvent`
- **unique_actors** — liczba unikalnych `actor.id`

## Odtworzenie

```bash
pip install -r requirements.txt
python src/run_pipeline.py
```

Z własnym eksportem BigQuery:

```bash
python src/etl.py --input data/raw/monthly_activity_bq.csv
python src/build_vectors.py
python src/dim_reduction.py
python src/build_viz.py
```
