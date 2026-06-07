# Zakres projektu: Ewolucja ekosystemów języków programowania

## Hipoteza

Popularność języków programowania na GitHubie zmienia się nierównomiernie: część ekosystemów rośnie (np. TypeScript, Rust), inne tracą udział w aktywności repozytoriów (np. Ruby, PHP), a rynek pozostaje skoncentrowany wokół kilku dominujących technologii.

## Źródło danych

**Opcja C (hybryda):** jednorazowy eksport z BigQuery (publiczny dataset GH Archive) → agregacja miesięczna → pliki CSV w repozytorium.

- Dataset: `githubarchive.day.*` (zdarzenia publiczne GitHub)
- Zapytanie SQL: [`sql/bigquery_export.sql`](../sql/bigquery_export.sql)
- W repozytorium dołączony jest **przykładowy eksport** (`data/raw/monthly_activity_sample.csv`) o strukturze zgodnej z eksportem BQ, aby pipeline działał bez konta GCP.

## Okres i rozdzielczość

| Parametr | Wartość |
|----------|---------|
| Zakres dat | 2011-01 — 2024-12 (początek GH Archive) |
| Krok czasowy | miesiąc |
| Liczba języków | 21 (top wg aktywności PushEvent) |

## Języki analizowane

JavaScript, Python, Java, TypeScript, C#, C++, PHP, C, Go, Ruby, Rust, Kotlin, Swift, Dart, Scala, R, Objective-C, Lua, Haskell, Julia, Perl

## Metryka aktywności (główna)

**Liczba zdarzeń `PushEvent`** przypisanych do repozytorium z polem `repo.language` w GH Archive.

Metryki pomocnicze (porównanie społeczności):

- **unique_actors** — liczba unikalnych użytkowników (`actor.id`) wypychających zmiany w danym miesiącu i języku
- **events_per_actor** — intensywność: `push_events / unique_actors`

## Ograniczenia (do raportu)

- Dane obejmują tylko publiczną aktywność GitHub (bias w stronę open source).
- Język repozytorium pochodzi z API GitHub i może być nieaktualny lub pusty.
- PushEvent nie obejmuje całej aktywności deweloperskiej (np. prywatne repozytoria).
