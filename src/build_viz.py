"""Generuje pliki Vega-Lite i index.html z danych processed."""

from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import pandas as pd

from config import (
    DATA_PROCESSED,
    PROCESSED_COMMUNITY,
    PROCESSED_CONCENTRATION,
    PROCESSED_DIM_REDUCTION,
    PROCESSED_SHARES,
    VIZ_DIR,
)

alt.data_transformers.disable_max_rows()


def _save_chart(chart: alt.Chart, path: Path) -> None:
    chart.save(str(path))
    print(f"Saved {path.name}")


def chart_trends(shares: pd.DataFrame) -> alt.Chart:
    top = (
        shares.groupby("language")["push_events"]
        .sum()
        .nlargest(8)
        .index.tolist()
    )
    data = shares[shares["language"].isin(top)].copy()
    selection = alt.selection_point(fields=["language"], bind="legend")

    return (
        alt.Chart(data)
        .mark_line(point=True)
        .encode(
            x=alt.X("month:T", title="Month"),
            y=alt.Y("push_events:Q", title="PushEvent count"),
            color=alt.Color("language:N", title="Language"),
            opacity=alt.condition(selection, alt.value(1), alt.value(0.15)),
            tooltip=["month", "language", "push_events", "share_pct"],
        )
        .add_params(selection)
        .properties(width=800, height=420, title="Activity trends (top 8 languages)")
    )


def chart_stacked_shares(shares: pd.DataFrame) -> alt.Chart:
    top = (
        shares.groupby("language")["push_events"]
        .sum()
        .nlargest(10)
        .index.tolist()
    )
    data = shares[shares["language"].isin(top)].copy()

    return (
        alt.Chart(data)
        .mark_area()
        .encode(
            x=alt.X("month:T", title="Month"),
            y=alt.Y("share_pct:Q", stack="normalize", title="Share (%)"),
            color=alt.Color("language:N", title="Language"),
            tooltip=["month", "language", alt.Tooltip("share_pct", format=".2f")],
        )
        .properties(width=800, height=420, title="Language shares over time (100% stacked)")
    )


def chart_treemap(shares: pd.DataFrame) -> alt.Chart:
    latest_month = shares["month"].max()
    data = shares[shares["month"] == latest_month].copy()
    brush = alt.selection_interval(encodings=["x"])

    return (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=alt.X("share_pct:Q", title="Share (%)"),
            y=alt.Y("language:N", sort="-x", title="Language"),
            color=alt.Color("share_pct:Q", scale=alt.Scale(scheme="blues"), title="Share %"),
            opacity=alt.condition(brush, alt.value(0.95), alt.value(0.35)),
            tooltip=["language", "share_pct", "push_events", "unique_actors"],
        )
        .add_params(brush)
        .properties(
            width=700,
            height=420,
            title=f"Market snapshot - {latest_month.strftime('%Y-%m')}",
        )
    )


def chart_bump(community: pd.DataFrame) -> alt.Chart:
    data = community.copy()
    return (
        alt.Chart(data)
        .mark_line(point=True)
        .encode(
            x=alt.X("month:T", title="Month"),
            y=alt.Y(
                "actor_rank:Q",
                title="Rank by unique actors",
                scale=alt.Scale(reverse=True),
            ),
            color=alt.Color("language:N", title="Language"),
            tooltip=["month", "language", "actor_rank", "unique_actors"],
        )
        .properties(width=800, height=420, title="Community rank over time")
    )


def chart_community(community: pd.DataFrame) -> alt.Chart:
    top = (
        community.groupby("language")["unique_actors"]
        .sum()
        .nlargest(10)
        .index.tolist()
    )
    data = community[community["language"].isin(top)].copy()
    selection = alt.selection_point(fields=["language"], bind="legend")

    bars = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=alt.X("month:T", title="Month"),
            y=alt.Y("unique_actors:Q", title="Unique actors"),
            color=alt.Color("language:N", title="Language"),
            opacity=alt.condition(selection, alt.value(0.9), alt.value(0.2)),
            tooltip=["month", "language", "unique_actors", "events_per_actor"],
        )
        .add_params(selection)
    )

    line = (
        alt.Chart(data)
        .mark_line(color="black", strokeDash=[4, 4])
        .encode(
            x="month:T",
            y=alt.Y("mean(events_per_actor):Q", title="Mean events per actor"),
        )
    )

    return (
        alt.layer(bars, line)
        .resolve_scale(y="independent")
        .properties(width=800, height=420, title="Community activity and intensity")
    )


def chart_concentration(concentration: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(concentration)
        .mark_line(point=True, color="#c44e52")
        .encode(
            x=alt.X("month:T", title="Month"),
            y=alt.Y("top3_share_pct:Q", title="Top 3 languages share (%)"),
            tooltip=["month", "top3_share_pct", "leader", "hhi"],
        )
        .properties(width=800, height=300, title="Market concentration (top 3 share)")
    )


def chart_dim_reduction(dim: pd.DataFrame) -> alt.Chart:
    selection = alt.selection_point(fields=["language"], bind="legend")
    return (
        alt.Chart(dim)
        .mark_circle(size=180)
        .encode(
            x=alt.X("x:Q", title="Dimension 1"),
            y=alt.Y("y:Q", title="Dimension 2"),
            color=alt.Color("language:N", title="Language"),
            facet=alt.Facet("method:N", title="Dimensionality reduction", columns=2),
            size=alt.Size("total_push_events:Q", title="Total PushEvents"),
            opacity=alt.condition(selection, alt.value(0.95), alt.value(0.25)),
            tooltip=["language", "method", "avg_share_pct", "total_unique_actors"],
        )
        .add_params(selection)
        .properties(width=320, height=320, title="UMAP vs PaCMAP - trend profile similarity")
    )


def write_index_html(viz_dir: Path) -> None:
    charts = [
        ("trends_line.vl.json", "Trendy aktywnosci"),
        ("shares_stacked.vl.json", "Udzialy w czasie"),
        ("treemap.vl.json", "Mapa udzialow (ostatni miesiac)"),
        ("bump_chart.vl.json", "Ranking spolecznosci"),
        ("community_comparison.vl.json", "Porownanie spolecznosci"),
        ("concentration.vl.json", "Koncentracja rynku"),
        ("dim_reduction.vl.json", "Redukcja wymiaru"),
    ]

    sections: list[str] = []
    embed_calls: list[str] = []
    for i, (filename, title) in enumerate(charts):
        spec_path = viz_dir / filename
        spec_json = spec_path.read_text(encoding="utf-8")
        sections.append(
            f"""
      <section>
        <h2>{title}</h2>
        <div id="chart-{i}"></div>
        <script type="application/json" id="spec-{i}">{spec_json}</script>
      </section>"""
        )
        embed_calls.append(
            f"""
    vegaEmbed('#chart-{i}', JSON.parse(document.getElementById('spec-{i}').textContent), {{actions: true}})
      .catch(err => showError('chart-{i}', err));"""
        )

    html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="utf-8" />
  <title>Ewolucja ekosystemow jezykow - wizualizacje</title>
  <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-lite@6"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 960px; }}
    section {{ margin-bottom: 3rem; border-bottom: 1px solid #ddd; padding-bottom: 2rem; }}
    h1 {{ margin-bottom: 0.25rem; }}
    p {{ color: #444; }}
    .chart-error {{ color: #b00020; font-family: monospace; white-space: pre-wrap; }}
  </style>
</head>
<body>
  <h1>Ewolucja ekosystemow jezykow programowania</h1>
  <p>Interaktywne wykresy Vega-Lite (legenda, tooltips, brush). Dane: miesieczna aktywnosc PushEvent na GitHubie (2011-2024).</p>
  {''.join(sections)}
  <script>
    function showError(chartId, err) {{
      const el = document.getElementById(chartId);
      const box = document.createElement('pre');
      box.className = 'chart-error';
      box.textContent = 'Blad renderowania wykresu: ' + err;
      el.replaceWith(box);
    }}
    document.addEventListener('DOMContentLoaded', function() {{
      {''.join(embed_calls)}
    }});
  </script>
</body>
</html>
"""
    for target in (viz_dir / "index.html", viz_dir.parent / "index.html"):
        target.write_text(html, encoding="utf-8")
    print("Saved index.html")


def export_data_for_vl() -> None:
    """Kopiuje CSV do viz/data dla łatwego podglądu offline (opcjonalnie)."""
    out = VIZ_DIR / "data"
    out.mkdir(parents=True, exist_ok=True)
    for name in [
        "monthly_shares.csv",
        "community_metrics.csv",
        "market_concentration.csv",
        "dim_reduction.csv",
    ]:
        src = DATA_PROCESSED / name
        if src.exists():
            pd.read_csv(src).to_csv(out / name, index=False)


def main() -> None:
    VIZ_DIR.mkdir(parents=True, exist_ok=True)
    shares = pd.read_csv(PROCESSED_SHARES)
    community = pd.read_csv(PROCESSED_COMMUNITY)
    concentration = pd.read_csv(PROCESSED_CONCENTRATION)
    dim = pd.read_csv(PROCESSED_DIM_REDUCTION)

    shares["month"] = pd.to_datetime(shares["month"])
    community["month"] = pd.to_datetime(community["month"])
    concentration["month"] = pd.to_datetime(concentration["month"])

    _save_chart(chart_trends(shares), VIZ_DIR / "trends_line.vl.json")
    _save_chart(chart_stacked_shares(shares), VIZ_DIR / "shares_stacked.vl.json")
    _save_chart(chart_treemap(shares), VIZ_DIR / "treemap.vl.json")
    _save_chart(chart_bump(community), VIZ_DIR / "bump_chart.vl.json")
    _save_chart(chart_community(community), VIZ_DIR / "community_comparison.vl.json")
    _save_chart(chart_concentration(concentration), VIZ_DIR / "concentration.vl.json")
    _save_chart(chart_dim_reduction(dim), VIZ_DIR / "dim_reduction.vl.json")

    export_data_for_vl()
    write_index_html(VIZ_DIR)


if __name__ == "__main__":
    main()
