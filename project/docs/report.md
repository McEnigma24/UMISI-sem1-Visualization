# Raport: Ewolucja ekosystemów języków programowania (GitHub, 2011–2026)

Dashboard interaktywny: [index.html](index.html). Mapowanie na wymagania Grupy 1: [docs/grupa1_checklist.md](docs/grupa1_checklist.md).

## 1. Cel i zakres

Projekt analizuje zmiany popularności dwudziestu jednego głównych języków programowania na podstawie **miesięcznej lub kwartalnej** aktywności `PushEvent` w publicznych repozytoriach GitHub. Szczegóły zakresu: [docs/scope.md](docs/scope.md).

## 2. Przygotowanie danych

Pipeline ETL (`src/etl.py`) przetwarza eksport CSV o schemacie zgodnym z zapytaniem BigQuery ([sql/bigquery_export.sql](sql/bigquery_export.sql)):

1. Filtrowanie do 21 języków z listy (top wg aktywności na GitHubie).
2. Obliczenie udziałów w każdym okresie czasu (`share_pct`).
3. Metryki społeczności: unikalni aktorzy, intensywność (`events_per_actor`), ranking.
4. Koncentracja rynku: indeks HHI oraz udział trzech liderów.

W eksporcie BigQuery (`sql/bigquery_export.sql`) aktywność jest **ważona wieloma językami na repo**: dla każdego `PushEvent` i języka z listy stosunek `bytes(język) / suma(bytes w repo)` — suma po kwartale daje „push-równoważne” ułamki (ETL trzyma je jako float w `push_events`).

Zakres **2011 — 2026-04-01** w domyślnym pliku wejściowym (`manyLanguages_added.csv`): początek GH Archive, koniec = **ostatni kwartał w scalonym CSV** (wartość `quarter` / `month` z eksportu BQ = pierwszy dzień kwartału, tu **2026-04-01** = Q2 2026).

## 3. Popularność języków w czasie

**Wykresy:** `viz/trends_line.vl.json`, `viz/shares_stacked.vl.json`

### 3.1 Trendy aktywnosci — co mierzymy i jak czytać skoki (2015, 2021–2026)

Wykres **„Trendy aktywności”** (`chart_trends` w `src/build_viz.py`) pokazuje na osi Y **`push_events`** z tabeli udziałów — to **suma kwartalna „push-równoważnych”** przypisań do języka po **ważeniu wielojęzycznym** z eksportera BigQuery (udział bajtów danego języka w snapshotcie `github_repos.languages` w repozytorium; jeden push może rozłożyć się na kilka języków z wagami sumującymi się do co najwyżej 1 w obrębie listy analizowanych języków). To **nie** jest prosta „goła liczba PushEvent tylko z pola `repo.language`” — metryka jest spójna z resztą dashboardu (udziały, koncentracja), ale **absolutna skala** zależy od definicji wag i od tego, ile repozytoriów i zdarzeń trafia do archiwum.

**Dlaczego „wszystko rośnie” po ok. 2015 (JavaScript, Python, TypeScript itd.)**

- **Część obrazu to dynamika realna:** rosnąca baza publicznego kodu na GitHubie, adopcja Pythona (data/ML, DevOps), TypeScriptu (frontend/Node), narzędzi wokół JS — to widać także na wykresach **udziału procentowego** (`share_pct`), gdzie względna popularność jest czytelniejsza niż sama skala absolutna.
- **Część to kontekst danych:** w tym projekcie okres ok. **2012–2015** ma w backfillu miejsca z **zerową lub niespójną** liczbą unikalnych aktorów przy niezerowych pushach (patrz pipeline społecznościowy / SQL archiwalny). To nie „dowodzi”, że w 2015 świat nagle odkrył programowanie — pokazuje też **granice spójności** starszej części GH Archive i ewentualne łączenie dwóch źródeł eksportu. Po przejściu do lat z pełniejszą agregacją **poziomy absolutne** mogą wyglądać jak skok w górę względem „dziury” lub niższej jakości okresu.
- **Wniosek uczciwy:** przy prezentacji rozdziel **trend względny** (udziały, rankingi) od **trendu absolutnego** (ważone pushy) i zawsze przypominaj definicję metryki.

**Pik w latach 2021–2023 i relacja do COVID (2019–2020)**

Łatwo intuicyjnie łączyć wzrost aktywności z pandemią, ale **szczyt na tej krzywej nie pokrywa się z pierwszym lockdownem 2020** — u Ciebie dominuje **2021–2023**, potem wyraźny spadek. To **nie jest sprzeczność z historią pandemii**, tylko przypomnienie, że **jedna oś czasu na GitHubie agreguje wiele mechanizmów**:

1. **Opóźniona i rozciągnięta reakcja gospodarki** — decyzje o narzędziach, hiring, migracja repozytoriów i wolumen pushy mogą szczytować **rok–dwa po** pierwszym falowym przejściu na pracę zdalną, a nie w samym Q2 2020.
2. **Druga fala cyfryzacji** — utrwalenie remote, cloud, automatyzacji pipeline’ów; więcej commitów w publicznych lub półpublicznych projektach.
3. **Hype i sektory o wysokiej aktywności commitów** — np. fala projektów **web3/NFT ok. 2021–2022** (często krótkotrwała, generująca dużo mechanicznej aktywności), boom repozytoriów ML/AI przed i wokół szerokiej dostępności modeli generatywnych.
4. **Produkty i ekosystem GitHub** — m.in. **GitHub Copilot (technical preview od czerwca 2021)** i otaczająca go dyskusja/narzędzia mogły zwiększyć zarówno realną produktywność, jak i **szum** (eksperymenty, szablony, forki) widoczny w archiwum zdarzeń.
5. **Pojedynczej przyczyny „bo był COVID”** ten wykres **nie dowodzi** — sensowna narracja brzmi: **wieloczynnikowość** (makro, branża, produkty, zachowania botów i automatyzacji, jakość snapshotów języków w repo).

**Spadek po ~2023**

Możliwe czynniki **równolegle**: normalizacja po okresie przegrzania, **redukcje zatrudnienia** w tech 2022–2024, mniejsza „farmacja” commitów w niektórych trendach, przesunięcie pracy do **prywatnych** repozytoriów lub innych platform (to archiwum **nie widzi** prywatnej aktywności), zmiana nawyków (mniej drobnych pushy, większe batche). Dashboard **pokazuje kształt serii w tych danych**; przypisanie udziału procentowego każdej przyczynie wymagałoby badań poza zakresem tego repozytorium.

**Podsumowanie do slajdu**

- Trendy absolutne = **ważone PushEvent-równoważne** per kwartał i język — czytaj razem z definicją SQL.
- Wzrost **Python / TypeScript / …** widać także w **udziałach %** — to mocniejszy argument „ekosystemowy” niż sama skala Y.
- Pik **2021–2023** i spadek potem: **interpretacja ostrożna**, wieloprzyczynowa; COVID jest **jednym z tła czasowego**, nie automatycznym wyjaśnieniem szczytu w konkretnym roku na tej krzywej.

Obserwacje (na danych projektu):

- **JavaScript** utrzymuje pozycję lidera, ale udział w aktywności stopniowo maleje.
- **Python** i **TypeScript** wykazują wyraźny wzrost udziału — Python dzięki ekosystemowi data/ML, TypeScript dzięki adopcji w projektach frontendowych i full-stack.
- **Rust** rośnie z niskiej bazy — typowy profil „emerging language”.
- **Ruby** i **PHP** tracą udział — spadek widoczny w stacked area i rankingu.

## 4. Aktywność społeczności

**Wykresy:** `viz/community_comparison.vl.json`, `viz/bump_chart.vl.json`

- Liczba **unikalnych aktorów** nie jest proporcjonalna do liczby pushy — niektóre języki mają wyższą intensywność (więcej zdarzeń na osobę).
- Ranking społeczności (bump chart) pokazuje, które ekosystemy nie tylko mają dużo zdarzeń, ale też angażują szeroką bazę kontrybutorów.

### 4.1 „Porównanie społeczności” — co dokładnie porównujemy

Wykres łączy **dwa niezależne kanały informacji** (dwie osie Y), liczone z tego samego kwartału, ale **inne agregacje**:

1. **Słupki (lewa oś)** — suma **`actors_stack`** po **12 językach** wybranych raz na cały wykres jako te z **największą sumą `unique_actors` w całej historii** (`chart_community` w `src/build_viz.py`). Każdy segment to „**ile unikalnych aktorów przypisujemy do tego języka** w tym kwartale” (surowe `unique_actors`, a tam gdzie eksport ma zera przy pushach — **szacunek** z wolumenu pushy i typowej intensywności języka, patrz ETL).
   **Ważne:** to **nie** jest „liczba różnych ludzi na GitHubie w tym kwartale”. Ta sama osoba kontrybuująca do repo liczonych pod **JavaScript** i pod **Python** wpada do **dwóch** segmentów — **suma wysokości stosu zawyża** liczbę realnie rozróżnialnych osób. Słupki odpowiadają raczej na: „**jak rozłożyła się szerokość bazy (per język) wśród top‑12 ekosystemów**”, a nie na globalny headcount.

2. **Czarna linia (prawa oś)** — dla danego kwartału Vega-Lite liczy **`mean(events_per_actor_viz)`** po **tych samych 12 wierszach języków**, czyli **średnią arytmetyczną** z dwunastu wartości typu „pushy / aktor w tym języku” (z imputacją tam, gdzie brak aktorów w eksporcie). To **nie** jest to samo co **„suma pushy ÷ suma aktorów”** po zsumowaniu liczników przez wszystkie języki — przy takiej średniej języki z małą liczbą aktorów, ale ogromnym `push_events / actor`, podnoszą linię tak samo mocno jak duże ekosystemy.

**Czy więc odpowiadamy na pytanie „więcej osób vs te same osoby puszują więcej”?**

- **Częściowo, w intuicji:** jeśli linia rośnie przy **stabilnych lub niskich** słupkach, sugeruje to raczej wzrost **intensywności zdarzeń na jednostkę „aktora w slajcie języka”** (więcej pushy na zliczonego aktora w danym języku) niż wzrost **szerokości bazy** w tej samej skali — zgodnie z Twoją lekturą wykresu.
- **Z ostrożnością:** wzrost intensywności może wynikać z **tej samej populacji ludzi** (więcej commitów na osobę), z **botów / kont technicznych / CI** liczonych jako aktorzy, ze **zmiany sposobu agregacji** w danych, albo z **kilku języków** z ekstremalnym stosunkiem push/actor, które **podnoszą średnią z 12 wartości** nawet gdy reszta ekosystemów jest spokojna.

**Wniosek:** wykres jest **porównaniem „skali społeczności (per język, potem suma po 12)” ze „średnią intensywnością (średnia z 12 profili językowych)”** — użyteczny do rozmowy o **rozłączeniu** „ile ludzi w slajcach językowych” vs „jak gęsto pushują”, ale nie zastępuje jednej metryki typu **globalny** `COUNT DISTINCT actor` po całym archiwum.

## 5. Zmiany dominujących technologii

**Wykresy:** `viz/treemap.vl.json`, `viz/concentration.vl.json`

- **Mapa udziałów** (ostatni miesiąc) odpowiada intuicji „mapy giełdy” — pole reprezentuje wielkość ekosystemu.
- **Koncentracja (top 3)** pozostaje wysoka: rynek GitHub jest zdominowany przez kilka języków; HHI potwierdza brak pełnej dywersyfikacji.

## 6. Analiza eksploracyjna (EDA)

**Skrypt:** `src/eda.py` · **Wejście główne:** `data/processed/monthly_shares.csv` (oraz `dim_reduction.csv` z wcześniejszego kroku pipeline’u).

### 6.1 Od surowego CSV do wejścia EDA — łańcuch przetwarzania

1. **Surowy plik** (`data/raw/real/…`) — wiersze: okres (`month` lub `quarter`), `language`, `push_events`, `unique_actors` (zgodnie z eksportem BQ).
2. **ETL** (`src/etl.py`) — filtr do 21 języków, typy numeryczne, **`monthly_shares.csv`**: dla każdej pary (okres, język) m.in. `share_pct` (udział ważonych pushy w sumie kwartalu), oraz pozostałe tabele processed (`community_metrics.csv` itd.). **EDA nie korzysta bezpośrednio z surowego CSV** — operuje na już policzonych udziałach.
3. **Macierz cech pod klastry / PCA / (spójnie z) DR** — funkcja `load_feature_matrix` w `src/dim_reduction.py`, importowana także w `eda.py`:
   - **Pivot:** wiersze = języki, kolumny = kolejne wartości `month`, komórka = `share_pct`, braki → **0**.
   - **`log1p`** na całej macierzy — łagodzenie skali małych udziałów.
   - **`StandardScaler`** z scikit-learn (**per kolumna**, czyli per okres czasu): w każdym kwartale udziały wszystkich języków mają średnią ~0 i odchylenie ~1. To porównuje **względny profil** „kto ile miał w tym slocie czasu”, a nie standaryzację „jeden język wzdłuż własnej osi czasu”.
   - Wynik: macierz o wymiarach **21 × T**, gdzie **T** = liczba unikalnych `month` w `monthly_shares` (w bieżącym eksporcie **T = 62** kwartały); **jeden wiersz** = jeden język jako punkt w **ℝ^T**.

4. **`language_summary(shares)`** (w `eda.py`) — **osobna ścieżka**: statystyki liczone na **oryginalnych `share_pct`** (bez `log1p` i bez skalera), m.in. średnia, odchylenie standardowe, min/max, średni udział w pierwszym i ostatnim roku kalendarzowym, różnica (pp), **nachylenie** trendu z regresji liniowej `polyfit` po indeksach kolejnych obserwacji. **Outliery** (`is_outlier`): z-score zmienności (`std_share_pct`) i zmiany udziału (`share_change_pp`) względem rozkładu po wszystkich językach, próg **|z| > 1.5**.

5. **`cluster_languages(matrix, …)`** — **KMeans** (`k=3`, `random_state=42`, `n_init=10`) na **tej samej** macierzy co w pkt. 3 — etykieta klastra per język zapisana w `language_clusters.csv`.

6. **`pca_explained_variance(matrix)`** — PCA na tej samej macierzy (do 5 składowych lub mniej, jeśli wymiar jest mniejszy); wynik w `pca_explained_variance.csv` dla wykresu wariancji.

7. **`build_language_profiles`** — złączenie podsumowania, klastrów oraz **współrzędnych PCA 2D** z już wygenerowanego **`dim_reduction.csv`** (metoda `pca` → kolumny `pca_x`, `pca_y` w `language_profiles.csv`). Kolejność w `run_pipeline.py`: **`dim_reduction.py` przed `eda.py`** — EDA czyta embeddingi z dysku, nie liczy PCA do mapy ponownie.

8. **Wizualizacja** (`src/build_viz.py`) — w zakładce EDA m.in. wykres zmiany udziału (`share_change.vl.json`) z `language_profiles`, klastry na płaszczyźnie PCA (`clusters.vl.json`), panel metod DR (`dim_reduction.vl.json`), wariancja PCA (`pca_variance.vl.json`).

### 6.2 Skrót wyników (co widać na wykresach)

- Statystyki per język: średni udział, zmienność, zmiana udziału (pierwszy vs ostatni rok), nachylenie trendu.
- **Klastrowanie:** KMeans (k=3) na znormalizowanych wektorach profili czasowych — wykres `viz/clusters.vl.json` (punkty w przestrzeni **pierwszych dwóch składowych PCA** z `dim_reduction.csv`, kolory = klastry z KMeans na pełnej macierzy cech).
- **Obserwacje nietypowe:** języki z |z| > 1,5 dla zmiany udziału lub zmienności (np. Ruby — silny spadek; Rust/TypeScript — silny wzrost).
- **Wariancja PCA:** `viz/pca_variance.vl.json` — pierwsze składowe wyjaśniają część zmienności profili; reszta wymaga metod nieliniowych.

**Wykres zmiany udziału:** `viz/share_change.vl.json` (outliers na czerwono).

## 7. Redukcja wymiaru (zestaw metod z zajęć)

**Wykres:** `viz/dim_reduction.vl.json` — **pionowy układ** (jedna metoda pod drugą), **etykiety języków na punktach** (bez legendy kolorów), wspólna paleta jak w reszcie dashboardu.

Dodatkowo **interaktywna scena 3D** w `index.html`: specyfikacja z `viz/dim_reduction_3d.spec.json` (generowana razem z wykresem), **osadzenie w tej samej stronie** (bez iframe — działa przy `file://`), biblioteka Plotly z CDN; osobno można otworzyć **`viz/dim_reduction_3d.html`** (Plotly dołączony do pliku, np. offline).

Dla każdego języka wektor ma **T** wymiarów (**T** = liczba unikalnych okresów `month` w `monthly_shares.csv`, po pivotcie jedna współrzędna na kwartał/miesiąc; w bieżących danych projektu **T = 62**). Transformacja przed embeddingami: **`share_pct` → `log1p` → `StandardScaler` per kolumna** (jak w `src/dim_reduction.py`, funkcja `load_feature_matrix`). Te same wektory rzutowano na 2D następującymi metodami:

| Metoda | Charakterystyka |
|--------|-----------------|
| **PCA** | Liniowa baza — dominujące kierunki zmian w czasie |
| **Kernel PCA (RBF)** | Nieliniowe odwzorowanie w przestrzeń cech, potem 2D (kernel z omówień) |
| **t-SNE (sklearn)** | Klasyczny t-SNE (Barnes–Hut) — lokalne sąsiedztwa w przestrzeni wysokowymiarowej |
| **UMAP** | Zachowanie struktury lokalnej i części globalnej (n_neighbors dopasowany do ~21 języków) |
| **TriMAP** | Niska wymiarowość z naciskiem na zachowanie tripletów odległości |
| **PaCMAP** | Balans lokalny / „daleki” (MN + FP) — czytelniejsza separacja klastrów przy małej próbce |
| **OpenTSNE** | Implementacja z rodziny szybkiego t-SNE (FFT / optymalizacja z literatury bliskiej **FIt-SNE**) |

**Interpretacja:** Języki rosnące (TypeScript, Rust, Python) odróżniają się od spadających (Ruby, PHP). Java i C# leżą pośrodku jako ekosystemy enterprise. Poszczególne panele mają **niezależne osie** (`resolve_scale`), więc nie porównujemy liczbowo współrzędnych między metodami — tylko względne sąsiedztwa w obrębie jednego panelu.

Uwaga: embedding jest **statyczny** na pełnej historii — nie porównujemy układów osi między miesiącami.

## 8. Ograniczenia

- Zakres czasu w **domyślnym** `manyLanguages_added.csv` kończy się na **2026-04-01** (ostatni kwartał w pipeline). Pojedynczy szablon [`sql/bigquery_export.sql`](sql/bigquery_export.sql) nadal dokumentuje skan do **2024-12-31** (`_TABLE_SUFFIX` … `241231`); lata **2025+** doklejasz osobnym zapytaniem ([`sql/bigquery_export_2025_2026.sql`](sql/bigquery_export_2025_2026.sql)) lub podnosząc sufiks — patrz [docs/scope.md](docs/scope.md).
- Dane = publiczny GitHub, nie cały rynek oprogramowania.
- Język repozytorium może być błędny lub nieaktualny.
- Przykładowy CSV symuluje trendy; dla produkcyjnej analizy użyj eksportu BigQuery.

## 9. Odtworzenie wyników

```bash
pip install -r requirements.txt
python src/run_pipeline.py
```

Otwórz `index.html` w przeglądarce. Seed: `42` (`src/config.py`).
