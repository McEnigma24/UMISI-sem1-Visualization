"""Generuje pliki Vega-Lite i index.html z danych processed."""

from __future__ import annotations

import math
from pathlib import Path

import altair as alt
import circlify
import pandas as pd
import squarify

YEARLY_FACET_COLUMNS = 4
YEARLY_CELL_SIZE = 170
# Wspolna skala pola bablek (px^2) dla wszystkich lat - bez renormy per rok
MAX_BUBBLE_AREA = 2800.0

from config import (
    DATA_PROCESSED,
    LANGUAGES,
    PROCESSED_COMMUNITY,
    PROCESSED_CONCENTRATION,
    PROCESSED_DIM_REDUCTION,
    PROCESSED_LANGUAGE_PROFILES,
    PROCESSED_PCA_VARIANCE,
    PROCESSED_SHARES,
    VIZ_DIR,
)

alt.data_transformers.disable_max_rows()


def _save_chart(chart: alt.Chart, path: Path) -> None:
    chart.save(str(path))
    print(f"Saved {path.name}")


def _language_popularity_order(shares: pd.DataFrame, descending: bool = True) -> list[str]:
    """Kolejnosc jezykow wg lacznej liczby PushEvent (domyslnie: najpopularniejszy pierwszy)."""
    return (
        shares.groupby("language")["push_events"]
        .sum()
        .sort_values(ascending=not descending)
        .index.tolist()
    )


def _language_averages(
    shares: pd.DataFrame,
    period_col: str,
    period_series: pd.Series,
) -> pd.DataFrame:
    data = shares[shares["language"].isin(LANGUAGES)].copy()
    data[period_col] = period_series
    out = (
        data.groupby([period_col, "language"], as_index=False)
        .agg(
            avg_share_pct=("share_pct", "mean"),
            avg_push_events=("push_events", "mean"),
            avg_unique_actors=("unique_actors", "mean"),
        )
        .sort_values([period_col, "language"])
    )
    out["avg_share_pct"] = out["avg_share_pct"].round(4)
    return out


def yearly_language_averages(shares: pd.DataFrame) -> pd.DataFrame:
    data = shares[shares["language"].isin(LANGUAGES)].copy()
    return _language_averages(
        data,
        "year",
        data["month"].dt.year.astype(str),
    )


def quarterly_language_averages(shares: pd.DataFrame) -> pd.DataFrame:
    data = shares[shares["language"].isin(LANGUAGES)].copy()
    quarter = data["month"].dt.to_period("Q").astype(str)
    period = quarter.str.replace(r"(\d{4})Q(\d)", r"\1-Q\2", regex=True)
    return _language_averages(data, "period", period)


def layout_yearly_treemap(yearly: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    w = h = YEARLY_CELL_SIZE
    for year, group in yearly.groupby("year", sort=True):
        group = group.sort_values("avg_share_pct", ascending=False)
        sizes = group["avg_share_pct"].tolist()
        if sum(sizes) <= 0:
            continue
        normed = squarify.normalize_sizes(sizes, w, h)
        for (_, row), rect in zip(
            group.iterrows(), squarify.squarify(normed, 0, 0, w, h)
        ):
            rows.append(
                {
                    "year": year,
                    "language": row["language"],
                    "avg_share_pct": row["avg_share_pct"],
                    "avg_push_events": row["avg_push_events"],
                    "x": rect["x"],
                    "x2": rect["x"] + rect["dx"],
                    # squarify: y rosnie w dol; Vega-Lite: y rosnie w gore
                    "y": h - (rect["y"] + rect["dy"]),
                    "y2": h - rect["y"],
                }
            )
    return pd.DataFrame(rows)


def layout_yearly_packed_bubbles(yearly: pd.DataFrame) -> pd.DataFrame:
    """Uklady pozycji z circlify; rozmiar = udzial % ze wspolnej skali (porownywalny miedzy latami)."""
    rows: list[dict] = []
    w = h = YEARLY_CELL_SIZE
    max_share = yearly["avg_share_pct"].max()
    enclosure = circlify.Circle(x=w / 2, y=h / 2, r=min(w, h) / 2 - 4)

    for year, group in yearly.groupby("year", sort=True):
        group = group.sort_values("avg_share_pct", ascending=False)
        values = group["avg_share_pct"].tolist()
        circles = circlify.circlify(
            values,
            show_enclosure=False,
            target_enclosure=enclosure,
        )
        for (_, row), circle in zip(group.iterrows(), circles):
            share = row["avg_share_pct"]
            rows.append(
                {
                    "year": year,
                    "language": row["language"],
                    "avg_share_pct": share,
                    "avg_push_events": row["avg_push_events"],
                    "x": circle.x,
                    "y": circle.y,
                    "bubble_area": (share / max_share) * MAX_BUBBLE_AREA,
                }
            )
    return pd.DataFrame(rows)


def chart_yearly_treemap(layout: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(layout)
        .mark_rect(stroke="white", strokeWidth=1)
        .encode(
            x=alt.X("x:Q", axis=None, scale=alt.Scale(domain=[0, YEARLY_CELL_SIZE])),
            x2="x2:Q",
            y=alt.Y("y:Q", axis=None, scale=alt.Scale(domain=[0, YEARLY_CELL_SIZE])),
            y2="y2:Q",
            color=alt.Color("language:N", title="Language"),
            facet=alt.Facet(
                "year:O",
                columns=YEARLY_FACET_COLUMNS,
                title="Year (yearly average)",
            ),
            tooltip=[
                "year",
                "language",
                alt.Tooltip("avg_share_pct", format=".2f"),
                alt.Tooltip("avg_push_events", format=",.0f"),
            ],
        )
        .properties(
            width=YEARLY_CELL_SIZE,
            height=YEARLY_CELL_SIZE,
            title="Yearly market map (treemap, average share per year)",
        )
    )


def chart_yearly_packed_bubbles(layout: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(layout)
        .mark_circle(stroke="white", strokeWidth=1)
        .encode(
            x=alt.X("x:Q", axis=None, scale=alt.Scale(domain=[0, YEARLY_CELL_SIZE])),
            y=alt.Y("y:Q", axis=None, scale=alt.Scale(domain=[0, YEARLY_CELL_SIZE])),
            size=alt.Size(
                "bubble_area:Q",
                legend=None,
                scale=alt.Scale(
                    domain=[0, MAX_BUBBLE_AREA],
                    range=[0, MAX_BUBBLE_AREA],
                    zero=True,
                ),
            ),
            color=alt.Color("language:N", title="Language"),
            facet=alt.Facet(
                "year:O",
                columns=YEARLY_FACET_COLUMNS,
                title="Year (yearly average)",
            ),
            tooltip=[
                "year",
                "language",
                alt.Tooltip("avg_share_pct", format=".2f"),
                alt.Tooltip("avg_push_events", format=",.0f"),
            ],
        )
        .properties(
            width=YEARLY_CELL_SIZE,
            height=YEARLY_CELL_SIZE,
            title="Yearly packed bubbles (average share per year)",
        )
    )


def _trend_line_labels(data: pd.DataFrame) -> pd.DataFrame:
    last_month = data["month"].max()
    return data[data["month"] == last_month].copy()


def chart_trends(shares: pd.DataFrame, top_n: int = 12) -> alt.Chart:
    order = _language_popularity_order(shares)
    top = order[:top_n]
    data = shares[shares["language"].isin(top)].copy()
    labels = _trend_line_labels(data)
    selection = alt.selection_point(fields=["language"], bind="legend")
    n_langs = shares["language"].nunique()

    color_enc = alt.Color("language:N", sort=top, title="Language")
    opacity_enc = alt.condition(selection, alt.value(1), alt.value(0.15))
    lines = (
        alt.Chart(data)
        .mark_line(point=True)
        .encode(
            x=alt.X("month:T", title="Month"),
            y=alt.Y("push_events:Q", title="PushEvent count"),
            color=color_enc,
            opacity=opacity_enc,
            tooltip=["month", "language", "push_events", "share_pct"],
        )
        .add_params(selection)
    )
    text = (
        alt.Chart(labels)
        .mark_text(align="left", dx=6, fontSize=10, fontWeight="bold")
        .encode(
            x=alt.X("month:T"),
            y=alt.Y("push_events:Q"),
            text="language:N",
            color=alt.Color("language:N", sort=top, legend=None),
            opacity=opacity_enc,
        )
    )
    return alt.layer(lines, text).properties(
        width=860,
        height=420,
        title=f"Activity trends (top {top_n} of {n_langs} languages)",
    )


def _stacked_area_labels(data: pd.DataFrame, min_band_pct: float = 2.8) -> pd.DataFrame:
    """Srodek pasma na srodkowym miesiacu osi czasu (etykiety na wykresie, nie na koncu)."""
    months = sorted(data["month"].unique())
    label_month = months[len(months) // 2]
    month = data[data["month"] == label_month].copy()
    # Zgodnie z order=pop_rank descending: najpierw kladzione sa wieksze ranki (dno stosu).
    month = month.sort_values("pop_rank", ascending=False)
    cum = 0.0
    rows: list[dict] = []
    for _, row in month.iterrows():
        share = float(row["share_pct"])
        y0, y1 = cum, cum + share
        if y1 - y0 >= min_band_pct:
            rows.append(
                {
                    "month": row["month"],
                    "language": row["language"],
                    "y_center": (y0 + y1) / 2.0,
                }
            )
        cum += share
    return pd.DataFrame(rows)


def chart_stacked_shares(shares: pd.DataFrame) -> alt.Chart:
    data = shares[shares["language"].isin(LANGUAGES)].copy()
    legend_order = _language_popularity_order(data)
    totals = data.groupby("language")["push_events"].sum()
    pop_rank = totals.rank(ascending=False, method="first")
    data = data.assign(pop_rank=data["language"].map(pop_rank))
    labels = _stacked_area_labels(data)
    pct_scale = alt.Scale(domain=[0, 100], nice=False)

    areas = (
        alt.Chart(data)
        .mark_area()
        .encode(
            x=alt.X("month:T", title="Month"),
            y=alt.Y(
                "share_pct:Q",
                stack="zero",
                title="Share (%)",
                scale=pct_scale,
            ),
            order=alt.Order("pop_rank:Q", sort="descending"),
            color=alt.Color("language:N", sort=legend_order, title="Language"),
            tooltip=["month", "language", alt.Tooltip("share_pct", format=".2f")],
        )
    )
    text = (
        alt.Chart(labels)
        .mark_text(
            align="center",
            baseline="middle",
            fontSize=9,
            fontWeight="bold",
        )
        .encode(
            x=alt.X("month:T", title="Month"),
            y=alt.Y("y_center:Q", scale=pct_scale, axis=None),
            text="language:N",
            color=alt.value("#111111"),
        )
    )
    return (
        alt.layer(areas, text)
        .resolve_scale(x="shared", y="shared")
        .properties(
            width=860,
            height=420,
            title=(
                f"Language shares over time — {len(LANGUAGES)} languages "
                "(100% stacked, largest share on top)"
            ),
        )
    )


def chart_treemap(shares: pd.DataFrame) -> alt.Chart:
    data = shares[shares["language"].isin(LANGUAGES)].copy()
    months = sorted(data["month"].unique())
    month_to_idx = {m: i for i, m in enumerate(months)}
    data["month_idx"] = data["month"].map(month_to_idx).astype(int)
    data["month_label"] = data["month"].dt.strftime("%Y-%m")

    n_months = len(months)
    last_idx = n_months - 1
    chart_h = max(420, data["language"].nunique() * 22)
    first_label = pd.Timestamp(months[0]).strftime("%Y-%m")
    last_label = pd.Timestamp(months[-1]).strftime("%Y-%m")

    month_slider = alt.param(
        name="month_idx",
        value=last_idx,
        bind=alt.BindRange(
            input="range",
            min=0,
            max=last_idx,
            step=1,
            name=f"Miesiac ({first_label} - {last_label})",
        ),
    )

    return (
        alt.Chart(data)
        .transform_filter(alt.datum.month_idx == month_slider)
        .mark_bar()
        .encode(
            x=alt.X("share_pct:Q", title="Share (%)"),
            y=alt.Y("language:N", sort="-x", title="Language"),
            color=alt.Color("share_pct:Q", scale=alt.Scale(scheme="blues"), title="Share %"),
            tooltip=[
                "month_label",
                "language",
                "share_pct",
                "push_events",
                "unique_actors",
            ],
        )
        .add_params(month_slider)
        .properties(
            width=700,
            height=chart_h,
            title=f"Market snapshot ({len(LANGUAGES)} languages) — suwak miesiaca",
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


def chart_community(community: pd.DataFrame, top_n: int = 12) -> alt.Chart:
    top = (
        community.groupby("language")["unique_actors"]
        .sum()
        .nlargest(top_n)
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


def build_topn_concentration(shares: pd.DataFrame) -> pd.DataFrame:
    data = shares[shares["language"].isin(LANGUAGES)].copy()
    max_n = len(LANGUAGES)
    rows: list[dict] = []
    for month, group in data.groupby("month"):
        top_shares = group.sort_values("share_pct", ascending=False)["share_pct"].tolist()
        for n in range(1, max_n + 1):
            rows.append(
                {
                    "month": month,
                    "top_n": n,
                    "top_n_share_pct": round(sum(top_shares[:n]), 2),
                }
            )
    return pd.DataFrame(rows)


def chart_concentration(shares: pd.DataFrame) -> alt.Chart:
    data = build_topn_concentration(shares)
    max_n = len(LANGUAGES)
    top_n_param = alt.param(
        name="top_n",
        value=3,
        bind=alt.BindRange(
            input="range",
            min=1,
            max=max_n,
            step=1,
            name="Top N jezykow",
        ),
    )
    return (
        alt.Chart(data)
        .transform_filter(alt.datum.top_n == top_n_param)
        .mark_line(point=True, color="#c44e52")
        .encode(
            x=alt.X("month:T", title="Month"),
            y=alt.Y("top_n_share_pct:Q", title="Laczny udzial top N (%)"),
            tooltip=[
                "month",
                alt.Tooltip("top_n", title="Top N"),
                alt.Tooltip("top_n_share_pct", format=".2f", title="Share (%)"),
            ],
        )
        .add_params(top_n_param)
        .properties(
            width=800,
            height=320,
            title=f"Koncentracja rynku — laczny udzial top N jezykow (1-{max_n})",
        )
    )


def chart_dim_reduction(dim: pd.DataFrame) -> alt.Chart:
    selection = alt.selection_point(fields=["language"], bind="legend")
    method_order = ["pca", "umap", "pacmap"]
    data = dim.copy()
    data["method"] = pd.Categorical(data["method"], categories=method_order, ordered=True)
    return (
        alt.Chart(data)
        .mark_circle(size=180)
        .encode(
            x=alt.X("x:Q", title="Dimension 1"),
            y=alt.Y("y:Q", title="Dimension 2"),
            color=alt.Color("language:N", title="Language"),
            facet=alt.Facet("method:N", title="Dimensionality reduction", columns=3),
            size=alt.Size("total_push_events:Q", title="Total PushEvents"),
            opacity=alt.condition(selection, alt.value(0.95), alt.value(0.25)),
            tooltip=["language", "method", "avg_share_pct", "total_unique_actors"],
        )
        .add_params(selection)
        .properties(width=260, height=260, title="PCA vs UMAP vs PaCMAP - language trend profiles")
    )


def chart_pca_variance(variance: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(variance)
        .mark_bar(color="#4c78a8")
        .encode(
            x=alt.X("component:N", title="Principal component", sort=None),
            y=alt.Y("explained_variance_ratio:Q", title="Explained variance ratio"),
            tooltip=["component", "explained_variance_ratio", "cumulative_ratio"],
        )
        .properties(width=500, height=280, title="PCA explained variance (language profile vectors)")
    )


def chart_share_change(profiles: pd.DataFrame) -> alt.Chart:
    data = profiles.sort_values("share_change_pp")
    return (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=alt.X("share_change_pp:Q", title="Share change (pp, first vs last year)"),
            y=alt.Y("language:N", sort="-x", title="Language"),
            color=alt.condition(
                alt.datum.is_outlier,
                alt.value("#e45756"),
                alt.value("#72b7b2"),
            ),
            tooltip=[
                "language",
                "share_first_year",
                "share_last_year",
                "share_change_pp",
                "is_outlier",
            ],
        )
        .properties(width=700, height=360, title="EDA: share change 2011-2024 (outliers in red)")
    )


def chart_clusters(dim: pd.DataFrame, profiles: pd.DataFrame) -> alt.Chart:
    pca = dim[dim["method"] == "pca"].merge(
        profiles[["language", "cluster", "is_outlier"]], on="language", how="left"
    )
    selection = alt.selection_point(fields=["cluster"], bind="legend")
    enc = dict(
        x=alt.X("x:Q", title="PC1"),
        y=alt.Y("y:Q", title="PC2"),
        opacity=alt.condition(selection, alt.value(0.95), alt.value(0.3)),
    )
    points = (
        alt.Chart(pca)
        .mark_circle(size=220, stroke="white", strokeWidth=1)
        .encode(
            **enc,
            color=alt.Color("cluster:N", title="KMeans cluster"),
            shape=alt.condition(alt.datum.is_outlier, alt.value("diamond"), alt.value("circle")),
            tooltip=["language", "cluster", "is_outlier", "avg_share_pct"],
        )
        .add_params(selection)
    )
    labels = (
        alt.Chart(pca)
        .mark_text(dy=-14, fontSize=10, align="center", color="#222")
        .encode(
            **enc,
            text="language:N",
        )
    )
    return alt.layer(points, labels).properties(
        width=520,
        height=420,
        title="EDA: k-means clusters on PCA space (k=3)",
    )


def write_index_html(viz_dir: Path) -> None:
    charts = [
        ("trends_line.vl.json", "Trendy aktywnosci", False),
        ("shares_stacked.vl.json", "Udzialy w czasie", False),
        ("concentration.vl.json", "Koncentracja rynku", False),
        ("bump_chart.vl.json", "Ranking spolecznosci", False),
        ("community_comparison.vl.json", "Porownanie spolecznosci", False),
        ("share_change.vl.json", "EDA: zmiana udzialu (2011-2024)", False),
        ("pca_variance.vl.json", "EDA: wariancja PCA", False),
        ("clusters.vl.json", "EDA: klastrowanie (k-means)", False),
        ("dim_reduction.vl.json", "Redukcja wymiaru (PCA, UMAP, PaCMAP)", True),
    ]

    market_snapshot_section = """
      <section class="chart-section">
        <h2>Mapa udzialow (slideshow kwartalny)</h2>
        <div class="chart-host snapshot-iframe-host">
          <iframe id="market-snapshot-viewer" title="Mapa udzialow kwartalnych" loading="lazy" scrolling="no"></iframe>
        </div>
      </section>"""

    yearly_viewer_section = """
      <section class="chart-section wide yearly-viewer-section">
        <h2>Kwartalny przeglad: treemap stabilny i niestabilny</h2>
        <div class="chart-host yearly-iframe-host">
          <iframe id="yearly-viewer" title="Kwartalny przeglad rynku" loading="lazy" scrolling="no"></iframe>
        </div>
      </section>"""

    concentration_section = """
      <section class="chart-section">
        <h2>Koncentracja rynku (slideshow kwartalny)</h2>
        <div class="chart-host concentration-iframe-host">
          <iframe id="concentration-viewer" title="Koncentracja rynku kwartalna" loading="lazy" scrolling="no"></iframe>
        </div>
      </section>"""

    sections: list[str] = []
    embed_calls: list[str] = []
    chart_idx = 0
    for filename, title, wide in charts:
        if filename == "concentration.vl.json":
            sections.append(concentration_section)
            continue
        spec_path = viz_dir / filename
        spec_json = spec_path.read_text(encoding="utf-8")
        section_class = "wide" if wide else ""
        sections.append(
            f"""
      <section class="chart-section {section_class}">
        <h2>{title}</h2>
        <div class="chart-host" id="chart-{chart_idx}"></div>
        <script type="application/json" id="spec-{chart_idx}">{spec_json}</script>
      </section>"""
        )
        embed_calls.append(
            f"""
    vegaEmbed('#chart-{chart_idx}', JSON.parse(document.getElementById('spec-{chart_idx}').textContent), {{
        actions: true,
        renderer: 'svg',
        tooltip: {{ theme: 'light' }}
      }})
      .then(fitChartToHost)
      .catch(err => showError('chart-{chart_idx}', err));"""
        )
        chart_idx += 1
        if filename == "shares_stacked.vl.json":
            sections.append(market_snapshot_section)
            sections.append(yearly_viewer_section)

    html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Ewolucja ekosystemow jezykow - wizualizacje</title>
  <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-lite@6"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    html {{ -webkit-text-size-adjust: 100%; }}
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      background: #f4f5f7;
      color: #111;
      line-height: 1.5;
    }}
    .page {{
      width: min(1120px, 100%);
      margin: 0 auto;
      padding: clamp(1rem, 3vw, 2.5rem);
    }}
    .page-header {{
      text-align: center;
      margin-bottom: 2rem;
    }}
    .page-header h1 {{
      margin: 0 0 0.5rem;
      font-size: clamp(1.35rem, 2.5vw, 1.85rem);
    }}
    .page-header p {{
      margin: 0 auto;
      max-width: 52rem;
      color: #444;
      font-size: clamp(0.9rem, 1.8vw, 1rem);
    }}
    .chart-section {{
      background: #fff;
      border-radius: 10px;
      padding: clamp(1rem, 2vw, 1.5rem);
      margin-bottom: 1.5rem;
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
    }}
    .chart-section h2 {{
      margin: 0 0 1rem;
      font-size: clamp(1rem, 2vw, 1.2rem);
      text-align: center;
    }}
    .chart-host {{
      width: 100%;
      display: flex;
      justify-content: center;
      overflow-x: auto;
      overflow-y: hidden;
      padding-bottom: 0.25rem;
    }}
    .chart-section.wide .chart-host {{
      justify-content: flex-start;
    }}
    .vega-embed {{
      margin: 0 auto;
      max-width: 100%;
    }}
    .vega-embed svg {{
      display: block;
      max-width: 100%;
      height: auto;
      shape-rendering: geometricPrecision;
      text-rendering: geometricPrecision;
    }}
    .chart-error {{
      color: #b00020;
      font-family: monospace;
      white-space: pre-wrap;
      text-align: left;
    }}
    .yearly-viewer-desc {{
      text-align: center;
      color: #555;
      font-size: 0.9rem;
      margin: 0 0 1rem;
      max-width: 42rem;
      margin-left: auto;
      margin-right: auto;
    }}
    .yearly-iframe-host {{
      height: 820px;
      min-height: 0;
      overflow: hidden;
      justify-content: center !important;
    }}
    .yearly-iframe-host iframe {{
      width: 100%;
      max-width: 960px;
      height: 820px;
      border: none;
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
    }}
    .snapshot-iframe-host {{
      height: 600px;
      min-height: 0;
      overflow: hidden;
      justify-content: center !important;
    }}
    .snapshot-iframe-host iframe {{
      width: 100%;
      max-width: 780px;
      height: 600px;
      border: none;
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
    }}
    .concentration-iframe-host {{
      height: 520px;
      min-height: 0;
      overflow: hidden;
      justify-content: center !important;
    }}
    .concentration-iframe-host iframe {{
      width: 100%;
      max-width: 920px;
      height: 520px;
      border: none;
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
    }}
    @media (max-width: 720px) {{
      .chart-section {{
        padding: 0.85rem;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <header class="page-header">
      <h1>Ewolucja ekosystemow jezykow programowania</h1>
    </header>
    {''.join(sections)}
  </main>
  <script>
    function showError(chartId, err) {{
      const el = document.getElementById(chartId);
      const box = document.createElement('pre');
      box.className = 'chart-error';
      box.textContent = 'Blad renderowania wykresu: ' + err;
      el.replaceWith(box);
    }}
    function fitChartToHost(result) {{
      if (!result || !result.view) return result;
      const embed = result.view.container();
      if (embed) embed.__view = result.view;
      const parent = embed && embed.parentElement;
      if (!parent) return result;
      const available = parent.clientWidth;
      const chartWidth = result.view.width();
      if (available > 0 && chartWidth > available) {{
        result.view.width(available).run();
      }}
      return result;
    }}

    window.addEventListener('resize', function() {{
      document.querySelectorAll('.chart-host .vega-embed').forEach(function(embed) {{
        const view = embed.__view;
        if (!view || !embed.parentElement) return;
        const available = embed.parentElement.clientWidth;
        if (available > 0 && view.width() > available) {{
          view.width(available).run();
        }}
      }});
    }});

    document.addEventListener('DOMContentLoaded', function() {{
      const p = location.pathname.replace(/\\\\/g, '/');
      const inViz = p.includes('/viz/');
      const msv = document.getElementById('market-snapshot-viewer');
      if (msv) {{
        msv.src = inViz ? 'market_snapshot_viewer.html' : 'viz/market_snapshot_viewer.html';
      }}
      const yv = document.getElementById('yearly-viewer');
      if (yv) {{
        yv.src = inViz ? 'yearly_viewer.html' : 'viz/yearly_viewer.html';
      }}
      const cv = document.getElementById('concentration-viewer');
      if (cv) {{
        cv.src = inViz ? 'concentration_viewer.html' : 'viz/concentration_viewer.html';
      }}
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
        "yearly_shares.csv",
        "quarterly_shares.csv",
        "community_metrics.csv",
        "market_concentration.csv",
        "dim_reduction.csv",
        "language_profiles.csv",
        "pca_explained_variance.csv",
        "eda_language_summary.csv",
        "language_clusters.csv",
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
    profiles = pd.read_csv(PROCESSED_LANGUAGE_PROFILES)
    variance = pd.read_csv(PROCESSED_PCA_VARIANCE)

    shares["month"] = pd.to_datetime(shares["month"])
    community["month"] = pd.to_datetime(community["month"])
    concentration["month"] = pd.to_datetime(concentration["month"])

    _save_chart(chart_trends(shares), VIZ_DIR / "trends_line.vl.json")
    _save_chart(chart_stacked_shares(shares), VIZ_DIR / "shares_stacked.vl.json")

    yearly = yearly_language_averages(shares)
    yearly.to_csv(DATA_PROCESSED / "yearly_shares.csv", index=False)
    quarterly = quarterly_language_averages(shares)
    quarterly.to_csv(DATA_PROCESSED / "quarterly_shares.csv", index=False)

    _save_chart(chart_concentration(shares), VIZ_DIR / "concentration.vl.json")
    _save_chart(chart_bump(community), VIZ_DIR / "bump_chart.vl.json")
    _save_chart(chart_community(community), VIZ_DIR / "community_comparison.vl.json")
    _save_chart(chart_share_change(profiles), VIZ_DIR / "share_change.vl.json")
    _save_chart(chart_pca_variance(variance), VIZ_DIR / "pca_variance.vl.json")
    _save_chart(chart_clusters(dim, profiles), VIZ_DIR / "clusters.vl.json")
    _save_chart(chart_dim_reduction(dim), VIZ_DIR / "dim_reduction.vl.json")

    export_data_for_vl()
    write_index_html(VIZ_DIR)


if __name__ == "__main__":
    main()
