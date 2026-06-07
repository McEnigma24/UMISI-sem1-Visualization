-- Eksport miesięcznej aktywności PushEvent per język z GH Archive (BigQuery).
-- Uruchom w konsoli BigQuery, zapisz wynik jako CSV do data/raw/monthly_activity_bq.csv
-- i ustaw ścieżkę w src/etl.py (RAW_INPUT) lub skopiuj pod nazwą monthly_activity_sample.csv.
--
-- Uwaga: ogranicz zakres dat przed pierwszym uruchomieniem (koszt skanowania).
-- Przykład poniżej: 2011-01-01 .. 2024-12-31 (początek GH Archive).

SELECT
  FORMAT_TIMESTAMP('%Y-%m', created_at) AS month,
  JSON_VALUE(repo, '$.language') AS language,
  COUNT(*) AS push_events,
  COUNT(DISTINCT actor.id) AS unique_actors
FROM `githubarchive.day.20*`
WHERE
  _TABLE_SUFFIX BETWEEN '110101' AND '241231'
  AND type = 'PushEvent'
  AND JSON_VALUE(repo, '$.language') IS NOT NULL
  AND JSON_VALUE(repo, '$.language') IN (
    'JavaScript', 'Python', 'Java', 'TypeScript', 'C#', 'C++',
    'PHP', 'C', 'Go', 'Ruby', 'Rust', 'Kotlin', 'Swift',
    'Dart', 'Scala', 'R', 'Objective-C', 'Lua',
    'Haskell', 'Julia', 'Perl'
  )
GROUP BY month, language
ORDER BY month, language;
