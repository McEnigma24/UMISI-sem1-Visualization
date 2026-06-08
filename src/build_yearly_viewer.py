"""Interaktywny przeglad kwartalny: treemap stabilny i niestabilny (slideshow)."""

from __future__ import annotations

import json
import math
import re

import pandas as pd
import squarify

from build_viz import quarterly_language_averages
from config import LANGUAGE_COLORS, PROCESSED_SHARES, VIZ_DIR

VIEW_SIZE = 640
ANIM_MS = 450

def _sort_periods(periods: list[str]) -> list[str]:
    def key(p: str) -> tuple[int, int]:
        m = re.match(r"(\d{4})-Q(\d)", p)
        if not m:
            return 0, 0
        return int(m.group(1)), int(m.group(2))

    return sorted(periods, key=key)


def _language_order(periods_df: pd.DataFrame) -> list[str]:
    return (
        periods_df.groupby("language")["avg_share_pct"]
        .mean()
        .sort_values(ascending=False)
        .index.tolist()
    )


def _rect_items(
    langs: list[str],
    shares: list[float],
    rects: list[dict],
) -> list[dict]:
    items: list[dict] = []
    for lang, share, rect in zip(langs, shares, rects):
        items.append(
            {
                "language": lang,
                "x": round(rect["x"], 1),
                "y": round(rect["y"], 1),
                "w": round(rect["dx"], 1),
                "h": round(rect["dy"], 1),
                "share": round(float(share), 2),
            }
        )
    return items


def build_stable_treemap(periods_df: pd.DataFrame, size: int = VIEW_SIZE) -> dict[str, list[dict]]:
    order = _language_order(periods_df)
    mean = periods_df.groupby("language")["avg_share_pct"].mean()
    normed = squarify.normalize_sizes([mean[l] for l in order], size, size)
    base = {
        lang: rect
        for lang, rect in zip(order, squarify.squarify(normed, 0, 0, size, size))
    }

    periods: dict[str, list[dict]] = {}
    for period, group in periods_df.groupby("period", sort=True):
        items: list[dict] = []
        for lang in order:
            row = group[group["language"] == lang]
            if row.empty:
                continue
            share = float(row.iloc[0]["avg_share_pct"])
            if share <= 0:
                continue
            b = base[lang]
            m = float(mean[lang])
            scale = math.sqrt(share / m) if m > 0 else 0.2
            scale = min(max(scale, 0.2), 2.0)
            bw, bh = b["dx"] * scale, b["dy"] * scale
            cx = b["x"] + b["dx"] / 2
            cy = b["y"] + b["dy"] / 2
            x = max(0, min(cx - bw / 2, size - bw))
            y = max(0, min(cy - bh / 2, size - bh))
            items.append(
                {
                    "language": lang,
                    "x": round(x, 1),
                    "y": round(y, 1),
                    "w": round(bw, 1),
                    "h": round(bh, 1),
                    "share": round(share, 2),
                }
            )
        periods[str(period)] = items
    return periods


def build_unstable_treemap(periods_df: pd.DataFrame, size: int = VIEW_SIZE) -> dict[str, list[dict]]:
    periods: dict[str, list[dict]] = {}
    for period, group in periods_df.groupby("period", sort=True):
        group = group.sort_values("avg_share_pct", ascending=False)
        sizes = group["avg_share_pct"].tolist()
        if sum(sizes) <= 0:
            continue
        langs = group["language"].tolist()
        shares = group["avg_share_pct"].tolist()
        normed = squarify.normalize_sizes(sizes, size, size)
        rects = squarify.squarify(normed, 0, 0, size, size)
        periods[str(period)] = _rect_items(langs, shares, rects)
    return periods


def build_share_series(periods_df: pd.DataFrame) -> dict[str, dict[str, float]]:
    period_list = _sort_periods(periods_df["period"].unique().tolist())
    series: dict[str, dict[str, float]] = {}
    for lang, group in periods_df.groupby("language"):
        by_period = group.set_index("period")["avg_share_pct"]
        series[str(lang)] = {
            p: round(float(by_period[p]), 4) for p in period_list if p in by_period.index
        }
    return series


def build_payload(periods_df: pd.DataFrame) -> dict:
    period_list = _sort_periods(periods_df["period"].unique().tolist())
    return {
        "size": VIEW_SIZE,
        "periods": period_list,
        "colors": LANGUAGE_COLORS,
        "share_series": build_share_series(periods_df),
        "treemap_stable": build_stable_treemap(periods_df),
        "treemap_unstable": build_unstable_treemap(periods_df),
    }


def render_html(payload: dict) -> str:
    data_json = json.dumps(payload, ensure_ascii=True)
    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Kwartalny przeglad rynku</title>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      overflow-x: hidden;
      overflow-y: visible;
    }}
    body {{
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      background: #fff;
      color: #111;
    }}
    .viewer {{
      max-width: 920px;
      margin: 0 auto;
      padding: 0.5rem 1rem 1.25rem;
    }}
    .viewer.grid-mode {{
      max-width: 920px;
      margin: 0 auto;
      width: 100%;
      padding: 0.5rem 1rem 1.25rem;
    }}
    .toolbar {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem 1rem;
      align-items: center;
      justify-content: center;
      margin-bottom: 0.5rem;
    }}
    .tabs.toolbar {{
      gap: 0.5rem 0.85rem;
    }}
    .toolbar label {{ font-size: 0.9rem; color: #333; }}
    .toolbar label.toggle {{
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      cursor: pointer;
      user-select: none;
    }}
    .toolbar select, .toolbar input[type="range"] {{ vertical-align: middle; }}
    .tabs button, .toolbar button, .slideshow-rows button {{
      border: 1px solid #ccc;
      background: #f8f8f8;
      border-radius: 6px;
      padding: 0.4rem 0.75rem;
      cursor: pointer;
      font-size: 0.9rem;
    }}
    .tabs button.active, .toolbar button.active {{
      background: #1a56db;
      color: #fff;
      border-color: #1a56db;
    }}
    .stage-wrap {{
      display: flex;
      justify-content: center;
      align-items: flex-start;
      overflow: visible;
    }}
    .viewer.grid-mode .stage-wrap {{
      overflow: visible;
      max-height: none;
      justify-content: center;
      width: auto;
    }}
    #stage svg {{
      display: block;
      border: 1px solid #e2e2e2;
      border-radius: 8px;
      background: #fafafa;
      max-width: 100%;
      height: auto;
    }}
    .grid-view {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 0.4rem 0.5rem;
      width: 100%;
      align-items: start;
      justify-items: center;
    }}
    @media (max-width: 1024px) {{
      .grid-view {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
    }}
    @media (max-width: 680px) {{
      .grid-view {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 380px) {{
      .grid-view {{ grid-template-columns: 1fr; }}
    }}
    .grid-cell {{
      text-align: center;
      font-size: clamp(0.55rem, 0.9vw, 0.72rem);
      cursor: pointer;
      border-radius: 5px;
      padding: 0.15rem;
      outline: none;
      width: 100%;
      max-width: 130px;
      min-width: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      transition: box-shadow 0.15s ease, background 0.15s ease;
    }}
    .grid-cell:hover, .grid-cell:focus-visible {{
      background: #f1f5f9;
      box-shadow: 0 0 0 2px #1a56db;
    }}
    .grid-cell .grid-period-label {{
      font-weight: 600;
      margin-bottom: 0.12rem;
      color: #334155;
      font-size: clamp(0.52rem, 0.85vw, 0.68rem);
      line-height: 1.15;
    }}
    .grid-cell svg {{
      width: auto;
      height: auto;
      max-width: min(100%, 112px);
      display: block;
      border: 1px solid #e5e7eb;
      border-radius: 4px;
      background: #fafafa;
    }}
    .grid-modal {{
      position: fixed;
      inset: 0;
      z-index: 1000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1rem;
    }}
    .grid-modal[hidden] {{ display: none !important; }}
    .grid-modal-backdrop {{
      position: absolute;
      inset: 0;
      background: rgba(15, 23, 42, 0.55);
      cursor: pointer;
    }}
    .grid-modal-dialog {{
      position: relative;
      z-index: 1;
      max-width: min(96vw, 920px);
      max-height: min(92vh, 920px);
      overflow: auto;
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 25px 50px rgba(0,0,0,0.25);
      padding: 0.75rem 1rem 1rem;
    }}
    .grid-modal-close {{
      position: absolute;
      top: 0.4rem;
      right: 0.5rem;
      border: none;
      background: transparent;
      font-size: 1.75rem;
      line-height: 1;
      cursor: pointer;
      color: #475569;
      padding: 0.25rem 0.5rem;
      border-radius: 6px;
    }}
    .grid-modal-close:hover {{ background: #f1f5f9; color: #111; }}
    .grid-modal-title {{
      font-size: 1.1rem;
      font-weight: 700;
      margin: 0 2rem 0.5rem 0;
      color: #0f172a;
    }}
    .grid-modal-body svg {{
      width: 100%;
      height: auto;
      max-height: min(78vh, 820px);
      display: block;
      border-radius: 8px;
      border: 1px solid #e2e8f0;
    }}
    .slideshow-controls-host {{
      display: flex;
      flex-direction: column;
      align-items: center;
      margin-bottom: 0.5rem;
      width: 100%;
    }}
    .slideshow-rows {{
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
      align-items: stretch;
      width: 100%;
      max-width: 920px;
    }}
    .slideshow-row.slideshow-toolbar-line {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: center;
      gap: 0.65rem 1rem;
      width: 100%;
    }}
    .nav-cluster {{
      display: inline-flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 0.4rem 0.55rem;
    }}
    .speed-cluster label {{
      display: inline-flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 0.3rem 0.55rem;
      font-size: 0.9rem;
      color: #333;
    }}
    button.btn-play-icon {{
      min-width: 2.65rem;
      width: 2.65rem;
      height: 2.65rem;
      padding: 0;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: #1f2937;
    }}
    button.btn-play-icon svg {{ display: block; flex-shrink: 0; }}
    button.btn-play-icon.is-playing {{
      background: #1a56db;
      color: #fff;
      border-color: #1a56db;
    }}
    button.btn-loop {{
      min-width: 2.65rem;
      width: 2.65rem;
      height: 2.65rem;
      padding: 0;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: #1f2937;
    }}
    button.btn-loop svg {{ display: block; flex-shrink: 0; }}
    button.btn-loop.active {{
      background: #1a56db;
      color: #fff;
      border-color: #1a56db;
    }}
    .speed-step-hint {{ font-size: 0.8rem; color: #64748b; }}
  </style>
</head>
<body>
  <div class="viewer">
    <div class="tabs toolbar" id="typeTabs">
      <button type="button" data-type="stable" class="active">Treemap stabilny</button>
      <button type="button" data-type="unstable">Treemap niestabilny</button>
      <label class="toggle">
        <input type="checkbox" id="gridToggle" />
        Siatka wszystkich kwartalow
      </label>
    </div>
    <div class="slideshow-controls-host" id="singleControls">
      <div class="slideshow-rows">
        <div class="slideshow-row slideshow-toolbar-line">
          <div class="nav-cluster">
            <button type="button" id="btnFirst" title="Pierwszy kwartal">&#9198;</button>
            <button type="button" id="btnPrev" title="Poprzedni kwartal">&#9664;</button>
            <select id="periodSelect" aria-label="Kwartal" title="Wybor kwartalu"></select>
            <button type="button" id="btnNext" title="Nastepny kwartal">&#9654;</button>
            <button type="button" id="btnLast" title="Ostatni kwartal">&#9197;</button>
          </div>
          <div class="speed-cluster">
            <label>
              Predkosc (ms)
              <input type="range" id="speedRange" min="100" max="4000" step="50" value="300" />
              <span id="speedVal">300</span>
              <span class="speed-step-hint" id="speedStepHint"></span>
            </label>
          </div>
          <button type="button" id="btnPlay" class="btn-play-icon" title="Odtwarzaj" aria-label="Odtwarzaj slideshow"><svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M8 5v14l11-7z"/></svg></button>
          <button type="button" id="btnLoop" class="btn-loop active" aria-pressed="true" title="Zapetlanie wlaczone" aria-label="Wlacz i wylacz zapetlanie slajdowa"><svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg></button>
        </div>
      </div>
    </div>
    <div class="toolbar" id="analysisControls">
      <label>
        Top udzial rynku (%)
        <input type="range" id="marketThreshold" min="0" max="100" step="5" value="0" />
        <span id="marketThresholdVal">wyl.</span>
      </label>
      <label>
        Wygładzanie QoQ
        <select id="maWindow">
          <option value="1" selected>Brak</option>
          <option value="3">MA 3 kw.</option>
          <option value="5">MA 5 kw.</option>
        </select>
      </label>
      <label class="toggle">
        <input type="checkbox" id="showQoQ" />
        Zmiana QoQ (%)
      </label>
      <label class="toggle">
        <input type="checkbox" id="stockPalette" />
        Paleta gieldowa
      </label>
    </div>
    <div class="stage-wrap">
      <div id="stage"></div>
    </div>
    <div id="gridModal" class="grid-modal" hidden>
      <div class="grid-modal-backdrop" id="gridModalBackdrop"></div>
      <div class="grid-modal-dialog" role="dialog" aria-modal="true" aria-labelledby="gridModalTitle">
        <button type="button" class="grid-modal-close" id="gridModalClose" aria-label="Zamknij">&times;</button>
        <div class="grid-modal-title" id="gridModalTitle"></div>
        <div class="grid-modal-body" id="gridModalBody"></div>
      </div>
    </div>
  </div>
  <script>
    const DATA = {data_json};
    const SIZE = DATA.size;
    const PERIODS = DATA.periods;
    const COLORS = DATA.colors;
    const SHARE_SERIES = DATA.share_series || {{}};

    let viewType = "stable";
    let gridMode = false;
    let loopEnabled = true;
    let periodIndex = 0;
    let timer = null;
    let animToken = 0;
    let marketThreshold = 0;
    let maWindow = 1;
    let showQoQ = false;
    let stockPalette = false;
    const QOQ_GROW = 1.5;
    const QOQ_DECLINE = -1.5;
    const TILE_BG = "#e3e3e3";
    const TILE_BG_TEXT = "#9a9a9a";
    const STOCK_UP = "#22c55e";
    const STOCK_DOWN = "#ef4444";
    const STOCK_FLAT = "#94a3b8";

    const stage = document.getElementById("stage");
    const periodSelect = document.getElementById("periodSelect");
    const speedRange = document.getElementById("speedRange");
    const speedVal = document.getElementById("speedVal");
    const gridToggle = document.getElementById("gridToggle");
    const singleControls = document.getElementById("singleControls");
    const analysisControls = document.getElementById("analysisControls");
    const marketThresholdRange = document.getElementById("marketThreshold");
    const marketThresholdVal = document.getElementById("marketThresholdVal");
    const maWindowSelect = document.getElementById("maWindow");
    const showQoQToggle = document.getElementById("showQoQ");
    const stockPaletteToggle = document.getElementById("stockPalette");
    const viewerEl = document.querySelector(".viewer");
    const gridModal = document.getElementById("gridModal");
    const gridModalBackdrop = document.getElementById("gridModalBackdrop");
    const gridModalClose = document.getElementById("gridModalClose");

    let _vhRaf = null;
    let _lastPostedH = -1;
    function postViewerHeight() {{
      if (_vhRaf) cancelAnimationFrame(_vhRaf);
      _vhRaf = requestAnimationFrame(() => {{
        _vhRaf = null;
        try {{
          const root = document.querySelector(".viewer");
          if (!root) return;
          const h = Math.ceil(Math.max(root.scrollHeight, root.getBoundingClientRect().height));
          if (_lastPostedH >= 0 && Math.abs(h - _lastPostedH) < 4) return;
          _lastPostedH = h;
          if (window.parent && window.parent !== window) {{
            window.parent.postMessage({{ type: "umisi-viewer-resize", source: "yearly-viewer", height: h }}, "*");
          }}
        }} catch (e) {{}}
      }});
    }}

    PERIODS.forEach((p, i) => {{
      const opt = document.createElement("option");
      opt.value = String(i);
      opt.textContent = p;
      periodSelect.appendChild(opt);
    }});

    const PLAY_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M8 5v14l11-7z"/></svg>';
    const PAUSE_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M6 5h4v14H6V5zm8 0h4v14h-4V5z"/></svg>';

    function syncPlayIcon(playing) {{
      const b = document.getElementById("btnPlay");
      if (!b) return;
      b.classList.toggle("is-playing", playing);
      b.innerHTML = playing ? PAUSE_ICON : PLAY_ICON;
      b.title = playing ? "Pauza" : "Odtwarzaj";
      b.setAttribute("aria-label", playing ? "Pauza" : "Odtwarzaj slideshow");
    }}

    function syncLoopButton() {{
      const b = document.getElementById("btnLoop");
      if (!b) return;
      b.classList.toggle("active", loopEnabled);
      b.setAttribute("aria-pressed", loopEnabled ? "true" : "false");
      b.title = loopEnabled ? "Zapetlanie wlaczone" : "Zapetlanie wylaczone";
      b.setAttribute("aria-label", loopEnabled ? "Wylacz zapetlanie" : "Wlacz zapetlanie");
    }}
    function syncSpeedStepHint() {{
      const r = document.getElementById("speedRange");
      const h = document.getElementById("speedStepHint");
      if (r && h) h.textContent = "(krok " + r.step + " ms)";
    }}
    syncLoopButton();
    syncSpeedStepHint();
    syncPlayIcon(false);

    function currentPeriod() {{ return PERIODS[periodIndex]; }}

    function treemapKey() {{
      return viewType === "stable" ? "treemap_stable" : "treemap_unstable";
    }}

    function itemsFor(period) {{
      return DATA[treemapKey()][period] || [];
    }}

    function periodIdx(period) {{
      return PERIODS.indexOf(period);
    }}

    function shareSeriesFor(lang) {{
      const m = SHARE_SERIES[lang] || {{}};
      return PERIODS.map(p => (p in m ? m[p] : null));
    }}

    function movingAverage(series, window, idx) {{
      if (window <= 1) return series[idx];
      const start = Math.max(0, idx - window + 1);
      const slice = series.slice(start, idx + 1).filter(v => v != null);
      if (!slice.length) return null;
      return slice.reduce((a, b) => a + b, 0) / slice.length;
    }}

    function smoothedShare(lang, idx) {{
      return movingAverage(shareSeriesFor(lang), maWindow, idx);
    }}

    function qoqChange(lang, idx) {{
      if (idx <= 0) return null;
      const cur = smoothedShare(lang, idx);
      const prev = smoothedShare(lang, idx - 1);
      if (cur == null || prev == null || prev === 0) return null;
      return ((cur - prev) / prev) * 100;
    }}

    function qoqDisplay(pct) {{
      if (pct == null) return {{ text: "", color: TILE_BG_TEXT }};
      const text = (pct >= 0 ? "+" : "") + pct.toFixed(1) + "%";
      let color = STOCK_FLAT;
      if (pct > QOQ_GROW) color = STOCK_UP;
      else if (pct < QOQ_DECLINE) color = STOCK_DOWN;
      return {{ text, color }};
    }}

    function qoqCategory(lang, idx) {{
      const pct = qoqChange(lang, idx);
      if (pct == null) return "flat";
      if (pct > QOQ_GROW) return "up";
      if (pct < QOQ_DECLINE) return "down";
      return "flat";
    }}

    function cumulativeTopSet(items) {{
      if (marketThreshold <= 0) return null;
      const sorted = [...items].sort((a, b) => b.share - a.share);
      let cum = 0;
      const set = new Set();
      for (const d of sorted) {{
        set.add(d.language);
        cum += d.share;
        if (cum >= marketThreshold) break;
      }}
      return set;
    }}

    function isInTop(lang, highlightSet) {{
      return highlightSet === null || highlightSet.has(lang);
    }}

    function tileStyle(lang, idx, highlightSet) {{
      const inTop = isInTop(lang, highlightSet);
      const dimmed = highlightSet !== null && !inTop;

      if (dimmed) {{
        return {{
          fill: TILE_BG,
          stroke: "#d0d0d0",
          strokeWidth: 1,
          textFill: TILE_BG_TEXT,
        }};
      }}

      if (stockPalette) {{
        const cat = qoqCategory(lang, idx);
        if (cat === "up") {{
          return {{ fill: STOCK_UP, stroke: "#15803d", strokeWidth: 2, textFill: "#fff" }};
        }}
        if (cat === "down") {{
          return {{ fill: STOCK_DOWN, stroke: "#b91c1c", strokeWidth: 2, textFill: "#fff" }};
        }}
        return {{ fill: STOCK_FLAT, stroke: "#64748b", strokeWidth: 2, textFill: "#fff" }};
      }}

      const stroke = highlightSet !== null ? "#f5a623" : "#fff";
      const strokeWidth = highlightSet !== null ? 3 : 1.5;
      return {{
        fill: COLORS[lang] || "#999",
        stroke,
        strokeWidth,
        textFill: "#111",
      }};
    }}

    function labelMarkup(d, idx, x, y, w, h, highlightSet) {{
      const fs = Math.max(9, Math.min(13, h / 3.5));
      const show = w > 28 && h > 22;
      if (!show) return "";
      const cx = x + w / 2;
      const style = tileStyle(d.language, idx, highlightSet);
      const qoq = qoqDisplay(qoqChange(d.language, idx));
      const qoqColor = stockPalette ? "#fff" : qoq.color;
      const qoqLine = showQoQ && qoq.text
        ? `<tspan x="${{cx}}" dy="1.05em" fill="${{qoqColor}}" font-weight="700">${{qoq.text}}</tspan>`
        : "";
      return `<text x="${{cx}}" y="${{y + h/2}}" text-anchor="middle" dominant-baseline="middle" font-size="${{fs}}" fill="${{style.textFill}}">${{d.language}}<tspan x="${{cx}}" dy="1.05em">${{d.share.toFixed(1)}}%</tspan>${{qoqLine}}</text>`;
    }}

    function svgHeader() {{
      return `<svg viewBox="0 0 ${{SIZE}} ${{SIZE}}" width="${{SIZE}}" height="${{SIZE}}" xmlns="http://www.w3.org/2000/svg">`;
    }}

    function renderTreemapStatic(items, idx) {{
      const highlightSet = cumulativeTopSet(items);
      let s = svgHeader();
      items.forEach(d => {{
        const style = tileStyle(d.language, idx, highlightSet);
        s += `<g data-lang="${{d.language}}">`;
        s += `<rect x="${{d.x}}" y="${{d.y}}" width="${{d.w}}" height="${{d.h}}" fill="${{style.fill}}" stroke="${{style.stroke}}" stroke-width="${{style.strokeWidth}}" rx="2"/>`;
        s += labelMarkup(d, idx, d.x, d.y, d.w, d.h, highlightSet);
        s += `</g>`;
      }});
      return s + "</svg>";
    }}

    function applyTileStyles(svg, items, idx) {{
      const highlightSet = cumulativeTopSet(items);
      items.forEach(d => {{
        const el = svg.querySelector(`g[data-lang="${{d.language}}"]`);
        if (!el) return;
        const style = tileStyle(d.language, idx, highlightSet);
        const rect = el.querySelector("rect");
        rect.setAttribute("fill", style.fill);
        rect.removeAttribute("fill-opacity");
        rect.setAttribute("stroke", style.stroke);
        rect.setAttribute("stroke-width", style.strokeWidth);
        let text = el.querySelector("text");
        const x = parseFloat(rect.getAttribute("x"));
        const y = parseFloat(rect.getAttribute("y"));
        const w = parseFloat(rect.getAttribute("width"));
        const h = parseFloat(rect.getAttribute("height"));
        const markup = labelMarkup(d, idx, x, y, w, h, highlightSet);
        if (markup) {{
          if (!text) {{
            const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
            g.innerHTML = markup;
            el.appendChild(g.firstChild);
          }} else {{
            const tmp = document.createElementNS("http://www.w3.org/2000/svg", "g");
            tmp.innerHTML = markup;
            text.replaceWith(tmp.firstChild);
          }}
        }} else if (text) {{
          text.remove();
        }}
      }});
    }}

    function lerp(a, b, t) {{ return a + (b - a) * t; }}
    function ease(t) {{ return t < 0.5 ? 2*t*t : 1 - Math.pow(-2*t + 2, 2)/2; }}

    function animateTo(period, duration) {{
      const token = ++animToken;
      const nextItems = itemsFor(period);
      const idx = periodIdx(period);
      const svg = stage.querySelector("svg");
      if (!svg || gridMode) {{
        drawSingle(period);
        return;
      }}

      const prevMap = {{}};
      svg.querySelectorAll("g[data-lang]").forEach(el => {{
        const rect = el.querySelector("rect");
        if (rect) prevMap[el.getAttribute("data-lang")] = rect;
      }});

      const start = performance.now();
      function frame(now) {{
        if (token !== animToken) return;
        const t = ease(Math.min(1, (now - start) / duration));
        nextItems.forEach(d => {{
          let el = svg.querySelector(`g[data-lang="${{d.language}}"]`);
          const p = prevMap[d.language];
          let x, y, w, h;
          if (p) {{
            x = lerp(parseFloat(p.getAttribute("x")), d.x, t);
            y = lerp(parseFloat(p.getAttribute("y")), d.y, t);
            w = lerp(parseFloat(p.getAttribute("width")), d.w, t);
            h = lerp(parseFloat(p.getAttribute("height")), d.h, t);
          }} else {{
            x = d.x; y = d.y; w = d.w; h = d.h;
          }}
          if (!el) {{
            el = document.createElementNS("http://www.w3.org/2000/svg", "g");
            el.setAttribute("data-lang", d.language);
            el.innerHTML = `<rect rx="2"/>`;
            svg.appendChild(el);
          }}
          const rect = el.querySelector("rect");
          rect.setAttribute("x", x); rect.setAttribute("y", y);
          rect.setAttribute("width", w); rect.setAttribute("height", h);
        }});
        applyTileStyles(svg, nextItems, idx);
        if (t < 1) requestAnimationFrame(frame);
      }}
      requestAnimationFrame(frame);
    }}

    function drawSingle(period) {{
      const idx = periodIdx(period);
      stage.innerHTML = renderTreemapStatic(itemsFor(period), idx);
      periodSelect.value = String(periodIndex);
      postViewerHeight();
    }}

    function redrawCurrent() {{
      if (gridMode) drawGrid();
      else drawSingle(currentPeriod());
    }}

    function openGridModal(period, idx) {{
      if (!gridMode) return;
      const svg = renderTreemapStatic(itemsFor(period), idx);
      document.getElementById("gridModalTitle").textContent = period;
      document.getElementById("gridModalBody").innerHTML = svg;
      gridModal.hidden = false;
      postViewerHeight();
    }}
    function closeGridModal() {{
      gridModal.hidden = true;
      document.getElementById("gridModalBody").innerHTML = "";
      postViewerHeight();
    }}

    function drawGrid() {{
      stopSlideshow();
      let html = '<div class="grid-view">';
      PERIODS.forEach((p, i) => {{
        const svg = renderTreemapStatic(itemsFor(p), i);
        html += `<div class="grid-cell" role="button" tabindex="0" aria-label="Powieksz treemap ${{p}}"><div class="grid-period-label">${{p}}</div>${{svg}}</div>`;
      }});
      stage.innerHTML = html + "</div>";
      stage.querySelectorAll(".grid-cell").forEach((cell, i) => {{
        const p = PERIODS[i];
        cell.addEventListener("click", () => openGridModal(p, i));
        cell.addEventListener("keydown", (e) => {{
          if (e.key === "Enter" || e.key === " ") {{
            e.preventDefault();
            openGridModal(p, i);
          }}
        }});
      }});
      postViewerHeight();
    }}

    function refresh() {{
      viewerEl.classList.toggle("grid-mode", gridMode);
      const showControls = !gridMode;
      singleControls.style.display = showControls ? "flex" : "none";
      analysisControls.style.display = showControls ? "flex" : "none";
      if (gridMode) {{
        drawGrid();
        return;
      }}
      drawSingle(currentPeriod());
    }}

    function resolvePeriodIndex(idx) {{
      if (loopEnabled) return (idx + PERIODS.length) % PERIODS.length;
      return Math.max(0, Math.min(PERIODS.length - 1, idx));
    }}

    function isLoopWrap(prevIndex, nextIndex) {{
      if (!loopEnabled) return false;
      return (
        (prevIndex === PERIODS.length - 1 && nextIndex === 0) ||
        (prevIndex === 0 && nextIndex === PERIODS.length - 1)
      );
    }}

    function goPeriod(idx, animate) {{
      const prevIndex = periodIndex;
      periodIndex = resolvePeriodIndex(idx);
      const hardCut = isLoopWrap(prevIndex, periodIndex);
      const useAnimation = animate && !hardCut && !gridMode;

      if (useAnimation) {{
        animateTo(currentPeriod(), {ANIM_MS});
      }} else {{
        animToken++;
        drawSingle(currentPeriod());
      }}
      periodSelect.value = String(periodIndex);
    }}

    function stopSlideshow() {{
      if (timer) {{ clearInterval(timer); timer = null; }}
      syncPlayIcon(false);
    }}

    function startSlideshow() {{
      if (gridMode) return;
      stopSlideshow();
      syncPlayIcon(true);
      const ms = parseInt(speedRange.value, 10);
      timer = setInterval(() => {{
        if (periodIndex >= PERIODS.length - 1 && !loopEnabled) {{
          stopSlideshow();
          return;
        }}
        goPeriod(periodIndex + 1, true);
      }}, ms);
    }}

    document.getElementById("btnLoop").addEventListener("click", () => {{
      loopEnabled = !loopEnabled;
      syncLoopButton();
    }});

    document.getElementById("typeTabs").addEventListener("click", e => {{
      const btn = e.target.closest("button[data-type]");
      if (!btn) return;
      viewType = btn.dataset.type;
      document.querySelectorAll("#typeTabs button").forEach(b => b.classList.toggle("active", b === btn));
      refresh();
    }});

    gridToggle.addEventListener("change", () => {{
      stopSlideshow();
      gridMode = gridToggle.checked;
      refresh();
    }});

    document.getElementById("btnFirst").addEventListener("click", () => {{
      stopSlideshow();
      goPeriod(0, false);
    }});
    document.getElementById("btnPrev").addEventListener("click", () => goPeriod(periodIndex - 1, false));
    document.getElementById("btnNext").addEventListener("click", () => goPeriod(periodIndex + 1, false));
    document.getElementById("btnLast").addEventListener("click", () => {{
      stopSlideshow();
      goPeriod(PERIODS.length - 1, false);
    }});
    periodSelect.addEventListener("change", () => goPeriod(parseInt(periodSelect.value, 10), false));
    speedRange.addEventListener("input", () => {{
      speedVal.textContent = speedRange.value;
      syncSpeedStepHint();
      if (timer) startSlideshow();
    }});
    document.getElementById("btnPlay").addEventListener("click", () => {{
      if (timer) stopSlideshow();
      else startSlideshow();
    }});
    marketThresholdRange.addEventListener("input", () => {{
      marketThreshold = parseInt(marketThresholdRange.value, 10);
      marketThresholdVal.textContent = marketThreshold <= 0 ? "wyl." : String(marketThreshold);
      redrawCurrent();
    }});
    maWindowSelect.addEventListener("change", () => {{
      maWindow = parseInt(maWindowSelect.value, 10);
      redrawCurrent();
    }});
    showQoQToggle.addEventListener("change", () => {{
      showQoQ = showQoQToggle.checked;
      redrawCurrent();
    }});
    stockPaletteToggle.addEventListener("change", () => {{
      stockPalette = stockPaletteToggle.checked;
      redrawCurrent();
    }});

    gridModalBackdrop.addEventListener("click", closeGridModal);
    gridModalClose.addEventListener("click", closeGridModal);
    document.addEventListener("keydown", (e) => {{
      if (e.key === "Escape" && !gridModal.hidden) closeGridModal();
    }});
    if (typeof ResizeObserver !== "undefined") {{
      const root = document.querySelector(".viewer");
      if (root) new ResizeObserver(() => postViewerHeight()).observe(root);
    }}
    window.addEventListener("resize", postViewerHeight);

    marketThresholdVal.textContent = marketThreshold <= 0 ? "wyl." : String(marketThreshold);
    refresh();
  </script>
</body>
</html>
"""


def main() -> None:
    shares = pd.read_csv(PROCESSED_SHARES)
    shares["month"] = pd.to_datetime(shares["month"])
    quarterly = quarterly_language_averages(shares)
    payload = build_payload(quarterly)

    out_html = VIZ_DIR / "yearly_viewer.html"
    out_json = VIZ_DIR / "data" / "yearly_viewer.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    out_html.write_text(render_html(payload), encoding="utf-8")
    print(f"Saved {out_html.name}")


if __name__ == "__main__":
    main()
