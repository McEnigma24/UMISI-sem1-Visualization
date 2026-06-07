# Raport: Ewolucja ekosystemów języków programowania (GitHub, 2011–2024)

Dashboard interaktywny: [index.html](index.html). Mapowanie na wymagania Grupy 1: [docs/grupa1_checklist.md](docs/grupa1_checklist.md).

## 1. Cel i zakres

Projekt analizuje zmiany popularności dwudziestu jednego głównych języków programowania na podstawie miesięcznej aktywności `PushEvent` w publicznych repozytoriach GitHub. Szczegóły zakresu: [docs/scope.md](docs/scope.md).

## 2. Przygotowanie danych

Pipeline ETL (`src/etl.py`) przetwarza eksport CSV o schemacie zgodnym z zapytaniem BigQuery ([sql/bigquery_export.sql](sql/bigquery_export.sql)):

1. Filtrowanie do 21 języków z listy (top wg aktywności na GitHubie).
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

## 6. Analiza eksploracyjna (EDA)

**Skrypt:** `src/eda.py` · **Dane:** `data/processed/eda_language_summary.csv`, `language_profiles.csv`

- Statystyki per język: średni udział, zmienność, zmiana udziału (pierwszy vs ostatni rok), nachylenie trendu.
- **Klastrowanie:** KMeans (k=3) na znormalizowanych wektorach profili czasowych — wykres `viz/clusters.vl.json` (przestrzeń PCA).
- **Obserwacje nietypowe:** języki z |z| > 1,5 dla zmiany udziału lub zmienności (np. Ruby — silny spadek; Rust/TypeScript — silny wzrost).
- **Wariancja PCA:** `viz/pca_variance.vl.json` — pierwsze składowe wyjaśniają część zmienności profili; reszta wymaga metod nieliniowych.

**Wykres zmiany udziału:** `viz/share_change.vl.json` (outliers na czerwono).

## 7. Redukcja wymiaru (PCA, UMAP, PaCMAP)

**Wykres:** `viz/dim_reduction.vl.json`

Dla każdego języka wektor ~168 wymiarów (miesięczne udziały %, `log1p` + standaryzacja). Te same wektory rzutowano na 2D trzema metodami:

| Metoda | Charakterystyka |
|--------|-----------------|
| **PCA** | Liniowa baza — dominujące kierunki zmian w czasie (odpowiednik omawianego na zajęciach) |
| **UMAP** | Silniejsze grupowanie lokalne — podobne kształty trendów blisko siebie |
| **PaCMAP** | Lepsza struktura globalna między klastrami „stabilnymi” a „rosnącymi” |

**Interpretacja:** Języki rosnące (TypeScript, Rust, Python) odróżniają się od spadających (Ruby, PHP). Java i C# leżą pośrodku jako ekosystemy enterprise.

Uwaga: embedding jest **statyczny** na pełnej historii — nie porównujemy układów osi między miesiącami.

## 8. Ograniczenia

- Dane = publiczny GitHub, nie cały rynek oprogramowania.
- Język repozytorium może być błędny lub nieaktualny.
- Przykładowy CSV symuluje trendy; dla produkcyjnej analizy użyj eksportu BigQuery.

## 9. Odtworzenie wyników

```bash
pip install -r requirements.txt
python src/run_pipeline.py
```

Otwórz `index.html` w przeglądarce. Seed: `42` (`src/config.py`).
