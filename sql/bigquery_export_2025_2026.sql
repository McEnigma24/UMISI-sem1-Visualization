-- Uzupełnienie kwartalne 2025–2026 (wąski skan `githubarchive.day.20*`).
-- Cel: **identyczne** kolumny i logika co [`bigquery_export.sql`](bigquery_export.sql), ale tylko:
--   `_TABLE_SUFFIX BETWEEN '250101' AND '261231'`
--   czyli 2025-01-01 … 2026-12-31 (suffix = `YYMMDD` przy wildcardzie `day.20*` — patrz komentarze w głównym pliku).
--
-- Dla roku **w toku** (np. uruchomienie w połowie 2026) archiwum zawiera tylko istniejące tabele dni —
-- zapytanie nie „wymaga” przyszłych partycji; brakujące dni po prostu nie wnoszą wierszy.
--
-- Zapis: CSV (nagłówki: `quarter`, `language`, `push_events`, `unique_actors` jak w głównym eksporcie),
--   kolumna `quarter` = pierwszy dzień kwartału (STRING z `DATE_TRUNC`).
-- Scal ręcznie z `manyLanguages_added.csv` (usuń z głównego pliku nakładające się kwartały 2025+ jeśli są,
--   posortuj po `quarter`, `language`), albo złącz w pandas.
--
-- Lokalizacja zapytania w BQ: **Processing location = US**.
-- Projekt zdarzeń: `githubarchive`, dataset `day` — NIE `bigquery-public-data.githubarchive`.

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
      _TABLE_SUFFIX BETWEEN '250101' AND '261231'
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

-- ═══ Diagnostyka (uruchom osobno; niski koszt) ═══
-- Zakres kwartałów i pushy tylko z archiwum (bez joina do languages):
/*
SELECT
  COUNT(DISTINCT _TABLE_SUFFIX) AS day_tables,
  COUNT(DISTINCT CAST(DATE_TRUNC(DATE(created_at), QUARTER) AS STRING)) AS n_quarters,
  COUNT(*) AS push_rows,
  MIN(CAST(DATE_TRUNC(DATE(created_at), QUARTER) AS STRING)) AS min_q,
  MAX(CAST(DATE_TRUNC(DATE(created_at), QUARTER) AS STRING)) AS max_q
FROM `githubarchive.day.20*`
WHERE _TABLE_SUFFIX BETWEEN '250101' AND '261231'
  AND type = 'PushEvent';
*/
