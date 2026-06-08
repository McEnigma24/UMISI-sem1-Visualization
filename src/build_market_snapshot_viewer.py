"""Animowana mapa udzialow kwartalnych (slideshow, ranking po udziale)."""

from __future__ import annotations

import json
import re

import pandas as pd

from build_viz import quarterly_language_averages
from config import LANGUAGE_COLORS, LANGUAGES, PROCESSED_SHARES, VIZ_DIR

CHART_W = 720
LABEL_W = 118
ROW_H = 20
ROW_GAP = 2
ANIM_MS = 450
PAD_TOP = 28


def _sort_periods(periods: list[str]) -> list[str]:
    def key(p: str) -> tuple[int, int]:
        m = re.match(r"(\d{4})-Q(\d)", p)
        if not m:
            return 0, 0
        return int(m.group(1)), int(m.group(2))

    return sorted(periods, key=key)


def _bar_height() -> float:
    return ROW_H - ROW_GAP


def build_layouts(quarterly: pd.DataFrame) -> dict[str, list[dict]]:
    max_share = float(quarterly["avg_share_pct"].max()) * 1.05
    bar_max_w = CHART_W - LABEL_W - 16

    layouts: dict[str, list[dict]] = {}
    for period, group in quarterly.groupby("period", sort=True):
        group = group.sort_values("avg_share_pct", ascending=False)
        items: list[dict] = []
        for rank, (_, row) in enumerate(group.iterrows()):
            lang = str(row["language"])
            share = float(row["avg_share_pct"])
            y = rank * ROW_H
            w = (share / max_share) * bar_max_w if max_share > 0 else 0
            items.append(
                {
                    "language": lang,
                    "y": round(y, 1),
                    "w": round(w, 1),
                    "h": round(_bar_height(), 1),
                    "share": round(share, 2),
                }
            )
        layouts[str(period)] = items
    return layouts


def build_payload(quarterly: pd.DataFrame) -> dict:
    periods = _sort_periods(quarterly["period"].astype(str).unique().tolist())
    n_langs = len(LANGUAGES)
    return {
        "width": CHART_W,
        "height": PAD_TOP + n_langs * ROW_H + 8,
        "label_width": LABEL_W,
        "pad_top": PAD_TOP,
        "periods": periods,
        "colors": LANGUAGE_COLORS,
        "layouts": build_layouts(quarterly),
    }


def render_html(payload: dict) -> str:
    data_json = json.dumps(payload, ensure_ascii=True)
    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Mapa udzialow kwartalnych</title>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; overflow: hidden; height: 100%; }}
    body {{
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      background: #fff;
      color: #111;
    }}
    .viewer {{ max-width: 780px; margin: 0 auto; padding: 0.5rem 1rem 0; }}
    .slideshow-rows {{
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
      align-items: stretch;
      width: 100%;
      max-width: 920px;
      margin: 0 auto 0.65rem;
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
    .toolbar {{
      display: flex; flex-wrap: wrap; gap: 0.5rem 1rem;
      align-items: center; justify-content: center; margin-bottom: 0.5rem;
    }}
    .toolbar label {{ font-size: 0.9rem; color: #333; }}
    .toolbar label.toggle {{
      display: inline-flex; align-items: center; gap: 0.35rem;
      cursor: pointer; user-select: none;
    }}
    .toolbar button, .slideshow-rows button {{
      border: 1px solid #ccc; background: #f8f8f8; border-radius: 6px;
      padding: 0.4rem 0.75rem; cursor: pointer; font-size: 0.9rem;
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
    <div class="slideshow-rows" id="slideshowControls">
      <div class="slideshow-row slideshow-toolbar-line">
        <div class="nav-cluster">
          <button type="button" id="btnFirst" title="Pierwszy kwartal">&#9198;</button>
          <button type="button" id="btnPrev" title="Poprzedni kwartal">&#9664;</button>
          <select id="periodSelect" aria-label="Kwartal" title="Wybor kwartalu"></select>
          <button type="button" id="btnNext" title="Nastepny kwartal">&#9654;</button>
          <button type="button" id="btnLast" title="Ostatni kwartal">&#9197;</button>
        </div>
        <div class="speed-cluster">
          <label>Predkosc (ms)
            <input type="range" id="speedRange" min="100" max="4000" step="50" value="1000" />
            <span id="speedVal">1000</span>
            <span class="speed-step-hint" id="speedStepHint"></span>
          </label>
        </div>
        <button type="button" id="btnPlay" class="btn-play-icon" title="Odtwarzaj" aria-label="Odtwarzaj slideshow"><svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M8 5v14l11-7z"/></svg></button>
        <button type="button" id="btnLoop" class="btn-loop active" aria-pressed="true" title="Zapetlanie wlaczone" aria-label="Wlacz i wylacz zapetlanie slajdowa"><svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg></button>
      </div>
    </div>
    <div id="stage"></div>
  </div>
  <script>
    const DATA = {data_json};
    const W = DATA.width;
    const H = DATA.height;
    const LABEL_W = DATA.label_width;
    const PAD_TOP = DATA.pad_top;
    const PERIODS = DATA.periods;
    const COLORS = DATA.colors;

    let periodIndex = PERIODS.length - 1;
    let loopEnabled = true;
    let timer = null;
    let animToken = 0;

    const stage = document.getElementById("stage");
    const periodSelect = document.getElementById("periodSelect");

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
    function itemsFor(period) {{ return DATA.layouts[period] || []; }}

    function svgHeader() {{
      return `<svg viewBox="0 0 ${{W}} ${{H}}" width="${{W}}" height="${{H}}" xmlns="http://www.w3.org/2000/svg">` +
        `<text x="${{W/2}}" y="18" text-anchor="middle" font-size="13" fill="#444">Udzial rynku (%)</text>`;
    }}

    function renderStatic(items) {{
      let s = svgHeader();
      items.forEach(d => {{
        const c = COLORS[d.language] || "#999";
        const y = PAD_TOP + d.y;
        s += `<g data-lang="${{d.language}}">`;
        s += `<text x="4" y="${{y + d.h/2}}" dominant-baseline="middle" font-size="10" fill="#333">${{d.language}}</text>`;
        s += `<rect x="${{LABEL_W}}" y="${{y}}" width="${{d.w}}" height="${{d.h}}" fill="${{c}}" rx="2"/>`;
        if (d.w > 36) {{
          s += `<text x="${{LABEL_W + d.w - 4}}" y="${{y + d.h/2}}" text-anchor="end" dominant-baseline="middle" font-size="9" fill="#fff">${{d.share.toFixed(1)}}%</text>`;
        }} else {{
          s += `<text x="${{LABEL_W + d.w + 4}}" y="${{y + d.h/2}}" dominant-baseline="middle" font-size="9" fill="#333">${{d.share.toFixed(1)}}%</text>`;
        }}
        s += `</g>`;
      }});
      return s + "</svg>";
    }}

    function lerp(a, b, t) {{ return a + (b - a) * t; }}
    function ease(t) {{ return t < 0.5 ? 2*t*t : 1 - Math.pow(-2*t + 2, 2)/2; }}

    function animateTo(period, duration) {{
      const token = ++animToken;
      const nextItems = itemsFor(period);
      const svg = stage.querySelector("svg");
      if (!svg) {{ drawSingle(period); return; }}

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
          let y, w, h;
          const targetY = PAD_TOP + d.y;
          if (p) {{
            y = lerp(parseFloat(p.getAttribute("y")), targetY, t);
            w = lerp(parseFloat(p.getAttribute("width")), d.w, t);
            h = lerp(parseFloat(p.getAttribute("height")), d.h, t);
          }} else {{
            y = targetY; w = d.w; h = d.h;
          }}
          if (!el) {{
            el = document.createElementNS("http://www.w3.org/2000/svg", "g");
            el.setAttribute("data-lang", d.language);
            el.innerHTML = `<text x="4" dominant-baseline="middle" font-size="10" fill="#333">${{d.language}}</text><rect x="${{LABEL_W}}" rx="2"/><text font-size="9"></text>`;
            svg.appendChild(el);
          }}
          const rect = el.querySelector("rect");
          rect.setAttribute("y", y);
          rect.setAttribute("width", w);
          rect.setAttribute("height", h);
          rect.setAttribute("fill", COLORS[d.language] || "#999");
          const texts = el.querySelectorAll("text");
          if (texts[0]) texts[0].setAttribute("y", y + h / 2);
          if (texts[1]) {{
            const inside = w > 36;
            texts[1].setAttribute("x", inside ? LABEL_W + w - 4 : LABEL_W + w + 4);
            texts[1].setAttribute("y", y + h / 2);
            texts[1].setAttribute("text-anchor", inside ? "end" : "start");
            texts[1].setAttribute("fill", inside ? "#fff" : "#333");
            texts[1].textContent = d.share.toFixed(1) + "%";
          }}
        }});
        if (t < 1) requestAnimationFrame(frame);
      }}
      requestAnimationFrame(frame);
    }}

    function drawSingle(period) {{
      stage.innerHTML = renderStatic(itemsFor(period));
      periodSelect.value = String(periodIndex);
    }}

    function resolvePeriodIndex(idx) {{
      if (loopEnabled) return (idx + PERIODS.length) % PERIODS.length;
      return Math.max(0, Math.min(PERIODS.length - 1, idx));
    }}

    function isLoopWrap(prev, next) {{
      if (!loopEnabled) return false;
      return (prev === PERIODS.length - 1 && next === 0) || (prev === 0 && next === PERIODS.length - 1);
    }}

    function goPeriod(idx, animate) {{
      const prev = periodIndex;
      periodIndex = resolvePeriodIndex(idx);
      const hardCut = isLoopWrap(prev, periodIndex);
      if (animate && !hardCut) animateTo(currentPeriod(), {ANIM_MS});
      else {{ animToken++; drawSingle(currentPeriod()); }}
      periodSelect.value = String(periodIndex);
    }}

    function stopSlideshow() {{
      if (timer) {{ clearInterval(timer); timer = null; }}
      syncPlayIcon(false);
    }}

    function startSlideshow() {{
      stopSlideshow();
      syncPlayIcon(true);
      const ms = parseInt(document.getElementById("speedRange").value, 10);
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
    document.getElementById("speedRange").addEventListener("input", () => {{
      document.getElementById("speedVal").textContent = document.getElementById("speedRange").value;
      syncSpeedStepHint();
      if (timer) startSlideshow();
    }});
    document.getElementById("btnPlay").addEventListener("click", () => {{
      if (timer) stopSlideshow();
      else startSlideshow();
    }});

    drawSingle(currentPeriod());
  </script>
</body>
</html>
"""


def main() -> None:
    shares = pd.read_csv(PROCESSED_SHARES)
    shares["month"] = pd.to_datetime(shares["month"])
    quarterly = quarterly_language_averages(shares)
    payload = build_payload(quarterly)

    out_html = VIZ_DIR / "market_snapshot_viewer.html"
    out_json = VIZ_DIR / "data" / "market_snapshot_viewer.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    out_html.write_text(render_html(payload), encoding="utf-8")
    print(f"Saved {out_html.name}")


if __name__ == "__main__":
    main()
