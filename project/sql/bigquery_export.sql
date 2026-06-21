WITH lang_rows AS (
  SELECT
    repo_name,
    lang.name AS language,
    lang.bytes AS byte_count
  FROM `bigquery-public-data.github_repos.languages`,
    UNNEST(language) AS lang
),

-- UNNEST -> rozbija na osobne wiersze
-- repo1 - C++ - 500
-- repo1 - C   - 450

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

-- repo1 - C++ - 0.55
-- repo1 - C   - 0.45

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


-- Przy każdy commicie na repo podbijamy liczniki każdego języka
-- o jego wagę z repo na które zpushowaliśmy

-- C++ counter += 0.55
-- C   counter += 0.45
