-- Backfill kwartalny 2012–2015 (wąski skan githubarchive.day.*).
-- Cel: te same metryki co w bigquery_export.sql, ale:
--   • tylko `_TABLE_SUFFIX BETWEEN '120101' AND '151231'` (2012-01-01 … 2015-12-31),
--   • slug repozytorium (w tej kolejności):
--       1) `REGEXP_EXTRACT(repo.url, …)` jak w głównym eksporcie,
--       2) **`repo.name`** gdy wygląda jak `owner/repo` (jest `/`),
--       3) **`org.login` + '/' + `repo.name`** gdy `repo.name` bez `/` (typowe stare PushEvent),
--       4) JSON z `payload`: `repository.full_name`, potem `owner.login` + `/` + `repository.name`.
--
-- Jeśli nadal widzisz tylko 2012-Q1 + 2015: uruchom diagnostykę na końcu pliku (jedna tabela dnia z 2013)
-- i sprawdź, które kolumny są wypełnione (`n_url`, `n_name_slash`, `n_org_repo`).
--
-- Uwaga: wynik ma **tylko pary (quarter, language)** z JOIN-em do snapshotu `github_repos.languages`.
-- Jeśli w danym kwartale żaden push z ważonym repo nie mapuje na daną nazwę z listy IN, tego języka
-- **nie będzie w wierszu** (to samo zachowanie co główny eksport) — stąd „mniej języków” w 2012 w CSV.
-- Pełna siatka 21×kwartał z zerami wymagałaby osobnego GRID (cross join) + LEFT JOIN do agregatu.
--
-- Zapis: CSV jak w README → scal ręcznie z manyLanguages.csv (np. usuń z głównego pliku wiersze
--   2012-01-01…2015-10-01 i wklej wynik tego zapytania), albo złącz w pandas / narzędziu.
-- Lokalizacja zapytania: US.

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
raw_events AS (
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
    _TABLE_SUFFIX BETWEEN '120101' AND '151231'
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
),
events AS (
  SELECT quarter, repo_slug, actor_id
  FROM raw_events
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

-- ═══ Diagnostyka (uruchom osobno; jedna partycja, niski koszt) ═══
-- Zamień datę tabeli na dowolny dzień z 2013 lub 2014.
/*
SELECT
  COUNTIF(repo.url IS NOT NULL AND REGEXP_CONTAINS(repo.url, r'/repos/[^/]+/[^/]+')) AS n_url,
  COUNTIF(repo.name IS NOT NULL AND REGEXP_CONTAINS(TRIM(repo.name), r'^[^/]+/[^/]+$')) AS n_name_owner_repo,
  COUNTIF(
    org.login IS NOT NULL
    AND repo.name IS NOT NULL
    AND TRIM(repo.name) != ''
    AND NOT REGEXP_CONTAINS(TRIM(repo.name), r'/')
  ) AS n_org_plus_name,
  COUNT(*) AS n_push
FROM `githubarchive.day.20130915`
WHERE type = 'PushEvent';
*/
