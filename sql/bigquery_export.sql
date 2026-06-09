-- Eksport kwartalnej aktywności PushEvent per język z GH Archive (BigQuery).
-- Kolumna `quarter` = pierwszy dzień kwartału (YYYY-MM-DD), mniej wierszy niż przy miesiącach.
-- Zapisz wynik jako CSV → data/raw/… i: python src/etl.py --input ścieżka.csv
--
-- Szacunek kosztu / „dry run” w praktyce:
--   • W BigQuery Studio **często nie ma** osobnego przełącznika „Dry run” po polsku ani po angielsku.
--     Zamiast tego edytor po chwili pokazuje **walidację + szacunek skanu** (np. „To zapytanie po
--     uruchomieniu przetworzy … GB/TB”) nad/pod edytorem albo obok ✓ — to jest właśnie estymacja
--     przed pełnym wykonaniem; **nie musisz niczego włączać**.
--   • **Więcej** (⋯) → **Ustawienia zapytania** — tam m.in. lokalizacja (US), cache, czasem limit bajtów.
--   • Pewny dry run poza przeglądarką: Google Cloud Shell lub lokalnie:
--       bq query --use_legacy_sql=false --dry_run --format=prettyjson --project_id=TWOJ_PROJEKT < plik.sql
--     **TWOJ_PROJEKT** = ID Twojego projektu GCP (ten z paska „Wybierz projekt” w konsoli — małe litery,
--     czasem z sufiksem liczb; to NIE jest `githubarchive`; `githubarchive` jest tylko w FROM w SQL).
--   W pliku .sql nie ma składni „DRY RUN” — to flaga narzędzia (`bq`, API), nie SQL.
--
-- 1) `JSON_VALUE(payload, '$.repository.full_name')` w tabelach `day.*` często jest NULL — nie polegamy na tym.
-- 2) `repo.url` ma postać https://api.github.com/repos/OWNER/REPO — wyciągamy segment po `/repos/`.
--    W latach ~2012–2014 `repo.url` bywa puste; slug `owner/repo` jest wtedy w kolumnie **`repo.name`**
--    (patrz `sql/bigquery_export_2012_2015.sql` / ewentualna poprawka głównego eksportu).
--    Uzupełnienie lat **2025–2026**: osobny wąski eksport `sql/bigquery_export_2025_2026.sql` (scal CSV ręcznie).
-- 3) Snapshot `bigquery-public-data.github_repos.languages`: **wszystkie** języki w repo z wagą
--    bytes / suma(bytes). Każdy PushEvent rozkładamy na języki (np. 0.7 + 0.3), potem SUM po kwartale.
--    To ogranicza artefakty typu „jedno monorepo = cały C#”.
--
-- WAŻNE — wildcard `githubarchive.day`:
--   NIE używaj `githubarchive.day.*` — w datasecie jest widok `yesterday` i BQ zwraca:
--   „Views cannot be queried through prefix”.
--   Użyj `githubarchive.day.20*` (tylko tabele o nazwie z prefiksem `20`, czyli lata 2000–2099).
--   Przy tym wzorcu `_TABLE_SUFFIX` = fragment dopasowany do `*` (NIE pełne YYYYMMDD):
--     tabela `20190101` → suffix `190101`  |  `20241231` → `241231`  |  `20110101` → `110101`
--   Filtr zakresu dat: porównuj suffixy, np. cały 2011–2024 → BETWEEN '110101' AND '241231'.
--   Plik `manyLanguages_added.csv` w repozytorium może być dłuższy (np. do 2026-04-01) po scaleniu z `bigquery_export_2025_2026.sql`.
--   (Pełne daty w BETWEEN przy `20*` odcinają dane — wcześniej mieliśmy 0 wierszy.)
-- `bigquery-public-data.githubarchive` NIE ISTNIEJE → błąd „Dataset … not found”.
-- Projekt zdarzeń to **`githubarchive`** (osobny publiczny projekt GCP), dataset `day`.
-- Przy błędach regionu: Query settings → **Processing location = US**.
--
-- Koszt: na test ustaw wąski zakres suffixów, np. Q4 2020:
--   `_TABLE_SUFFIX BETWEEN '201001' AND '201231'` (paź–grud 2020; patrz reguła suffixu przy `20*`).
-- Pełny 2011–2024 kwartalnie: oczekuj rzędu setek–~1100 wierszy (56 kwartałów × ≤21 języków).
-- Po zapisie CSV sprawdź w konsoli liczbę wierszy wyniku albo: SELECT MIN(quarter), MAX(quarter), COUNT(*) z zagnieżdżonym SELECT.
--
-- ─── Zapytania z COUNT(...) zwracają zawsze 1 wiersz ───
-- To jest jedna „linijka agregatu”, nie limit BigQuery. Patrz na kolumny (np. push_rows).
--
-- ─── Zawsze dokładnie 21 wierszy w eksporcie końcowym? ───
-- To znaczy: w wyniku końcowym jest dokładnie JEDEN kwartał × 21 języków z listy IN.
-- BigQuery NIE ma limitu „max 21 wierszy”. Szukaj przyczyny poniżej.
--
-- 1) W zakładce „Informacje o zadaniu” sprawdź wykonany SQL — przy `20*` filtr dat to **suffixy**
--    (np. 2011–2024: `BETWEEN '110101' AND '241231'`), nie pełne `YYYYMMDD` w jednym ciągu z nazwą tabeli.
-- 2) Wyłącz cache: Query settings → odznacz **Use cached results**, uruchom ponownie.
-- 3) W Explorerze rozwiń projekt **githubarchive** (publiczny), dataset **day** — czy widzisz
--    tysiące tabel `YYYYMMDD`? Jeśli nie, możesz mieć lustrzany / okrojony dataset w organizacji.
-- 4) Uruchom DIAGNOZĘ A (niski koszt), potem porównaj z pełnym zapytaniem.
--
-- DIAGNOZA A — tylko archiwum, bez joina (Q1 2019; suffixy `190101`–`190331`):
-- SELECT
--   COUNT(DISTINCT _TABLE_SUFFIX) AS day_tables,
--   COUNT(DISTINCT CAST(DATE_TRUNC(DATE(created_at), QUARTER) AS STRING)) AS n_quarters,
--   COUNT(*) AS push_rows
-- FROM `githubarchive.day.20*`
-- WHERE _TABLE_SUFFIX BETWEEN '190101' AND '190331'
--   AND type = 'PushEvent';
-- Oczekiwane: day_tables ≈ 90, n_quarters = 1, push_rows bardzo dużo.
-- Wynik: zawsze **1 wiersz** (agregat); jeśli push_rows = 0 → zły zakres suffixu albo region.
--
-- DIAGNOZA B — ten sam zakres, czy join z wagami zwraca kwartały (szkic; dostosuj CTE jak w eksporcie):
-- WITH repo_lang_weights AS (...),
-- ev AS ( ... )
-- SELECT COUNT(DISTINCT ev.q) AS n_quarters_after_join
-- FROM ev INNER JOIN repo_lang_weights pl ON pl.repo_slug = ev.slug;

WITH lang_rows AS (
  SELECT
    repo_name,
    lang.name AS language,
    lang.bytes AS byte_count
  FROM `bigquery-public-data.github_repos.languages`,
    UNNEST(language) AS lang
),
repo_byte_total AS (
  SELECT repo_name, SUM(byte_count) AS total_bytes
  FROM lang_rows
  GROUP BY repo_name
  HAVING total_bytes > 0
),
repo_lang_weights AS (
  SELECT
    LOWER(lr.repo_name) AS repo_slug,
    lr.language,
    SAFE_DIVIDE(lr.byte_count, rt.total_bytes) AS lang_fraction
  FROM lang_rows AS lr
  INNER JOIN repo_byte_total AS rt USING (repo_name)
  WHERE lr.language IN (
    'JavaScript', 'Python', 'Java', 'TypeScript', 'C#', 'C++',
    'PHP', 'C', 'Go', 'Ruby', 'Rust', 'Kotlin', 'Swift',
    'Dart', 'Scala', 'R', 'Objective-C', 'Lua',
    'Haskell', 'Julia', 'Perl'
  )
),
events AS (
  SELECT
    quarter,
    repo_slug,
    actor_id
  FROM (
    SELECT
      CAST(DATE_TRUNC(DATE(created_at), QUARTER) AS STRING) AS quarter,
      LOWER(
        TRIM(
          REGEXP_REPLACE(
            COALESCE(
              REGEXP_EXTRACT(repo.url, r'/repos/([^/]+/[^/]+)'),
              IF(
                repo.name IS NOT NULL AND REGEXP_CONTAINS(TRIM(repo.name), r'^[^/]+/[^/]+$'),
                TRIM(repo.name),
                CAST(NULL AS STRING)
              ),
              IF(
                org.login IS NOT NULL
                AND repo.name IS NOT NULL
                AND TRIM(repo.name) != ''
                AND NOT REGEXP_CONTAINS(TRIM(repo.name), r'/'),
                CONCAT(TRIM(org.login), '/', TRIM(repo.name)),
                CAST(NULL AS STRING)
              ),
              JSON_VALUE(payload, '$.repository.full_name'),
              IF(
                JSON_VALUE(payload, '$.repository.owner.login') IS NOT NULL
                AND JSON_VALUE(payload, '$.repository.name') IS NOT NULL,
                CONCAT(
                  JSON_VALUE(payload, '$.repository.owner.login'),
                  '/',
                  JSON_VALUE(payload, '$.repository.name')
                ),
                CAST(NULL AS STRING)
              )
            ),
            r'\.git$',
            ''
          )
        )
      ) AS repo_slug,
      actor.id AS actor_id
    FROM `githubarchive.day.20*`
    WHERE
      _TABLE_SUFFIX BETWEEN '110101' AND '241231'
      AND type = 'PushEvent'
      AND (
        (repo.url IS NOT NULL AND REGEXP_CONTAINS(repo.url, r'/repos/[^/]+/[^/]+'))
        OR (repo.name IS NOT NULL AND REGEXP_CONTAINS(TRIM(repo.name), r'^[^/]+/[^/]+$'))
        OR (
          org.login IS NOT NULL
          AND repo.name IS NOT NULL
          AND TRIM(repo.name) != ''
          AND NOT REGEXP_CONTAINS(TRIM(repo.name), r'/')
        )
        OR JSON_VALUE(payload, '$.repository.full_name') IS NOT NULL
        OR (
          JSON_VALUE(payload, '$.repository.owner.login') IS NOT NULL
          AND JSON_VALUE(payload, '$.repository.name') IS NOT NULL
        )
      )
  )
  WHERE repo_slug IS NOT NULL AND repo_slug != ''
)
SELECT
  e.quarter,
  pl.language AS language,
  SUM(pl.lang_fraction) AS push_events,
  COUNT(DISTINCT e.actor_id) AS unique_actors
FROM events AS e
INNER JOIN repo_lang_weights AS pl
  ON pl.repo_slug = e.repo_slug
GROUP BY e.quarter, pl.language
ORDER BY e.quarter, pl.language;

-- Diagnostyka (pojedynczo) — projekt `githubarchive`, nie bigquery-public-data:
-- SELECT COUNT(DISTINCT CAST(DATE_TRUNC(DATE(created_at), QUARTER) AS STRING)) AS n_quarters,
--   MIN(CAST(DATE_TRUNC(DATE(created_at), QUARTER) AS STRING)) AS min_q,
--   MAX(CAST(DATE_TRUNC(DATE(created_at), QUARTER) AS STRING)) AS max_q
-- FROM `githubarchive.day.20*`
-- WHERE _TABLE_SUFFIX BETWEEN '110101' AND '241231' AND type = 'PushEvent';
--
-- SELECT REGEXP_EXTRACT(repo.url, r'/repos/([^/]+/[^/]+)') AS slug, COUNT(*)
-- FROM `githubarchive.day.20200101`
-- WHERE type='PushEvent' GROUP BY 1 ORDER BY 2 DESC LIMIT 30;
