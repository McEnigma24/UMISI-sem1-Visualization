# Raport: Ewolucja ekosystemów języków programowania (GitHub, 2011–2024)

## 1. Cel i zakres

Projekt analizuje zmiany popularności dwunastu głównych języków programowania na podstawie miesięcznej aktywności `PushEvent` w publicznych repozytoriach GitHub. Szczegóły zakresu: [docs/scope.md](docs/scope.md).

## 2. Przygotowanie danych

Pipeline ETL (`src/etl.py`) przetwarza eksport CSV o schemacie zgodnym z zapytaniem BigQuery ([sql/bigquery_export.sql](sql/bigquery_export.sql)):

1. Filtrowanie do 12 języków z listy.
2. Obliczenie udziałów miesięcznych (`share_pct`).
3. Metryki społeczności: unikalni aktorzy, intensywność (`events_per_actor`), ranking.
4. Koncentracja rynku: indeks HHI oraz udział trzech liderów.

W repozytorium użyto przykładowego eksportu (`data/raw/monthly_activity_sample.csv`) o realistycznych trendach — można go zastąpić wynikiem z BigQuery bez zmiany kodu.

Zakres **2011–2024** odpowiada początkowi GH Archive. W danych syntetycznych uwzględniono późniejsze wejście języków (np. Go od 2012, Swift od 2014, Rust od 2015).

## 3. Popularność języków w czasie

**Wykresy:** `viz/trends_line.vl.json`, `viz/shares_stacked.vl.json`

Obserwacje (na danych projektu):

- **JavaScript** utrzymuje pozycję lidera, ale udział w aktywności stopniowo maleje.
- **Python** i **TypeScript** wykazują wyraźny wzrost udziału — Python dzięki ekosystemowi data/ML, TypeScript dzięki adopcji w projektach frontendowych i full-stack.
- **Rust** rośnie z niskiej bazy — typowy profil „emerging language”.
- **Ruby** i **PHP** tracą udział — spadek widoczny w stacked area i rankingu.

## 4. Aktywność społeczności

**Wykresy:** `viz/community_comparison.vl.json`, `viz/bump_chart.vl.json`

- Liczba **unikalnych aktorów** nie jest proporcjonalna do liczby pushy — niektóre języki mają wyższą intensywność (więcej zdarzeń na osobę).
- Ranking społeczności (bump chart) pokazuje, które ekosystemy nie tylko mają dużo zdarzeń, ale też angażują szeroką bazę kontrybutorów.

## 5. Zmiany dominujących technologii

**Wykresy:** `viz/treemap.vl.json`, `viz/concentration.vl.json`

- **Mapa udziałów** (ostatni miesiąc) odpowiada intuicji „mapy giełdy” — pole reprezentuje wielkość ekosystemu.
- **Koncentracja (top 3)** pozostaje wysoka: rynek GitHub jest zdominowany przez kilka języków; HHI potwierdza brak pełnej dywersyfikacji.

## 6. Redukcja wymiaru (UMAP vs PaCMAP)

**Wykres:** `viz/dim_reduction.vl.json`

Dla każdego języka zbudowano wektor 72 wymiarów (miesięczne udziały %, transformacja `log1p` + standaryzacja). Te same wektory rzutowano na 2D dwiema metodami:

| Metoda | Charakterystyka |
|--------|-----------------|
| **UMAP** | Silniejsze grupowanie lokalne — języki o podobnym „kształcie” trendu blisko siebie |
| **PaCMAP** | Lepsza zachowana struktura globalna — większe odległości między klastrami „stabilnych” a „rosnących” |

**Interpretacja:** Języki rosnące (TypeScript, Rust, Python) tworzą osobny klaster od języków z stagnacją lub spadkiem (Ruby, PHP). Java i C# często leżą pośrodku jako dojrzałe ekosystemy enterprise.

Uwaga: embedding jest **statyczny** na pełnej historii — nie porównujemy układów osi między miesiącami (metody nieliniowe nie gwarantują stabilności między przeładowaniami).

## 7. Ograniczenia

- Dane = publiczny GitHub, nie cały rynek oprogramowania.
- Język repozytorium może być błędny lub nieaktualny.
- Przykładowy CSV symuluje trendy; dla produkcyjnej analizy użyj eksportu BigQuery.

## 8. Odtworzenie wyników

```bash
pip install -r requirements.txt
python src/run_pipeline.py
```

Otwórz `index.html` w przeglądarce. Seed: `42` (`src/config.py`).
