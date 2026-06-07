"""Interaktywna koncentracja rynku kwartalna (slideshow + sklad top N)."""

from __future__ import annotations

import json
import re

import pandas as pd

from build_viz import quarterly_language_averages
from config import LANGUAGE_COLORS, LANGUAGES, PROCESSED_SHARES, VIZ_DIR

CHART_W = 860
CHART_H = 300
MARGIN = {"top": 28, "right": 24, "bottom": 44, "left": 52}
ANIM_MS = 400


def _sort_periods(periods: list[str]) -> list[str]:
    def key(p: str) -> tuple[int, int]:
        m = re.match(r"(\d{4})-Q(\d)", p)
        if not m:
            return 0, 0
        return int(m.group(1)), int(m.group(2))

    return sorted(periods, key=key)


def build_payload(quarterly: pd.DataFrame) -> dict:
    max_n = len(LANGUAGES)
    periods = _sort_periods(quarterly["period"].astype(str).unique().tolist())
    series: dict[str, list[dict]] = {str(n): [] for n in range(1, max_n + 1)}

    for period in periods:
        group = quarterly[quarterly["period"] == period].copy()
        group = group.sort_values("avg_share_pct", ascending=False)
        langs = group["language"].astype(str).tolist()
        shares = group["avg_share_pct"].tolist()
        for n in range(1, max_n + 1):
            top_langs = langs[:n]
            top_shares = shares[:n]
            series[str(n)].append(
                {
                    "period": period,
                    "share_pct": round(sum(top_shares), 2),
                    "languages": top_langs,
                    "language_pct": [round(float(s), 2) for s in top_shares],
                }
            )

    return {
        "width": CHART_W,
        "height": CHART_H,
        "margin": MARGIN,
        "periods": periods,
        "max_n": max_n,
        "series": series,
        "colors": LANGUAGE_COLORS,
    }


def render_html(payload: dict) -> str:
    data_json = json.dumps(payload, ensure_ascii=True)
    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Koncentracja rynku kwartalna</title>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; overflow: hidden; height: 100%; }}
    body {{
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      background: #fff;
      color: #111;
    }}
    .viewer {{ max-width: 920px; margin: 0 auto; padding: 0.5rem 1rem 0; }}
    .slideshow-rows {{
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
      align-items: stretch;
      width: 100%;
      max-width: 720px;
      margin: 0 auto 0.65rem;
    }}
    .slideshow-row {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: center;
      gap: 0.45rem 0.65rem;
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
    button.btn-play-pause {{ min-width: 8.5rem; font-weight: 600; }}
    button.btn-loop {{ min-width: 11rem; font-weight: 600; }}
    button.btn-loop.active {{
      background: #1a56db; color: #fff; border-color: #1a56db;
    }}
    .speed-row label {{
      display: inline-flex; flex-wrap: wrap; align-items: center;
      gap: 0.35rem 0.65rem;
    }}
    .speed-step-hint {{ font-size: 0.8rem; color: #64748b; }}
    .period-label {{ font-size: 1.2rem; font-weight: 600; min-width: 5.5rem; text-align: center; }}
    .share-label {{ font-size: 1rem; font-weight: 600; color: #c44e52; }}
    #stage svg {{
      display: block; width: 100%; max-width: {CHART_W}px; height: auto;
      border: 1px solid #e8e8e8; border-radius: 8px; background: #fafafa;
    }}
    .lang-panel {{
      margin-top: 0.65rem;
      padding: 0.6rem 0.75rem;
      border: 1px solid #e8e8e8;
      border-radius: 8px;
      background: #f9fafb;
      min-height: 3.2rem;
    }}
    .lang-panel .change-note {{
      font-size: 0.85rem;
      color: #b45309;
      font-weight: 600;
      margin-bottom: 0.35rem;
    }}
    .lang-panel .no-change {{
      font-size: 0.85rem;
      color: #64748b;
      margin-bottom: 0.35rem;
    }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 0.35rem; }}
    .chip {{
      display: inline-block;
      padding: 0.2rem 0.55rem;
      border-radius: 999px;
      font-size: 0.82rem;
      font-weight: 600;
      color: #111;
      border: 1px solid rgba(0,0,0,0.12);
    }}
    .chip.new {{ box-shadow: 0 0 0 2px #f59e0b; }}
    .chip.out {{ opacity: 0.45; text-decoration: line-through; }}
    .chip-wrap {{
      display: inline-flex;
      flex-direction: column;
      align-items: center;
      gap: 0.12rem;
    }}
    .chip-pct {{
      font-size: 0.72rem;
      font-weight: 600;
      color: #334155;
      line-height: 1;
    }}
    .event-marker {{ cursor: help; }}
  </style>
</head>
<body>
  <div class="viewer">
    <div class="toolbar" id="topNBar">
      <label>Top N jezykow
        <input type="range" id="topNRange" min="1" max="{payload['max_n']}" step="1" value="3" />
        <span id="topNVal">3</span>
      </label>
      <span class="share-label" id="shareLabel"></span>
    </div>
    <div class="slideshow-rows" id="slideshowControls">
      <div class="slideshow-row nav-row">
        <button type="button" id="btnFirst" title="Pierwszy kwartal">&#9198;</button>
        <button type="button" id="btnPrev" title="Poprzedni kwartal">&#9664;</button>
        <label>Kwartal <select id="periodSelect"></select></label>
        <span class="period-label" id="periodLabel"></span>
        <button type="button" id="btnNext" title="Nastepny kwartal">&#9654;</button>
        <button type="button" id="btnLast" title="Ostatni kwartal">&#9197;</button>
      </div>
      <div class="slideshow-row">
        <button type="button" id="btnPlay" class="btn-play-pause">Odtwarzaj</button>
      </div>
      <div class="slideshow-row speed-row">
        <label>Predkosc (ms)
          <input type="range" id="speedRange" min="100" max="4000" step="50" value="1000" />
          <span id="speedVal">1000</span>
          <span class="speed-step-hint" id="speedStepHint"></span>
        </label>
      </div>
      <div class="slideshow-row">
        <button type="button" id="btnLoop" class="btn-loop active" aria-pressed="true">Zapetlanie: wlaczone</button>
      </div>
    </div>
    <div id="stage"></div>
    <div class="lang-panel" id="langPanel"></div>
  </div>
  <script>
    const DATA = {data_json};
    const W = DATA.width;
    const H = DATA.height;
    const M = DATA.margin;
    const PERIODS = DATA.periods;
    const COLORS = DATA.colors;
    const INNER_W = W - M.left - M.right;
    const INNER_H = H - M.top - M.bottom;

    let topN = 3;
    let periodIndex = 0;
    let loopEnabled = true;
    let timer = null;

    const stage = document.getElementById("stage");
    const periodSelect = document.getElementById("periodSelect");
    const periodLabel = document.getElementById("periodLabel");
    const shareLabel = document.getElementById("shareLabel");
    const langPanel = document.getElementById("langPanel");
    const topNRange = document.getElementById("topNRange");
    const topNVal = document.getElementById("topNVal");

    PERIODS.forEach((p, i) => {{
      const opt = document.createElement("option");
      opt.value = String(i);
      opt.textContent = p;
      periodSelect.appendChild(opt);
    }});

    function syncLoopButton() {{
      const b = document.getElementById("btnLoop");
      if (!b) return;
      b.classList.toggle("active", loopEnabled);
      b.setAttribute("aria-pressed", loopEnabled ? "true" : "false");
      b.textContent = loopEnabled ? "Zapetlanie: wlaczone" : "Zapetlanie: wylaczone";
    }}
    function syncSpeedStepHint() {{
      const r = document.getElementById("speedRange");
      const h = document.getElementById("speedStepHint");
      if (r && h) h.textContent = "(krok " + r.step + " ms)";
    }}
    syncLoopButton();
    syncSpeedStepHint();

    function currentPeriod() {{ return PERIODS[periodIndex]; }}
    function seriesForN() {{ return DATA.series[String(topN)] || []; }}
    function pointAt(idx) {{ return seriesForN()[idx]; }}

    function setKey(langs) {{
      return langs.slice().sort().join("\\0");
    }}

    function compositionChanged(cur, prev) {{
      if (!prev) return false;
      return setKey(cur.languages) !== setKey(prev.languages);
    }}

    function orderOnlyChanged(cur, prev) {{
      if (!prev) return false;
      if (setKey(cur.languages) !== setKey(prev.languages)) return false;
      return cur.languages.join(",") !== prev.languages.join(",");
    }}

    /** 0 = brak, 1 = zmiana skladu, 2 = tylko kolejnosc */
    function eventKindAt(idx) {{
      if (idx <= 0) return 0;
      const cur = pointAt(idx);
      const prev = pointAt(idx - 1);
      if (compositionChanged(cur, prev)) return 1;
      if (orderOnlyChanged(cur, prev)) return 2;
      return 0;
    }}

    function escapeXml(t) {{
      return String(t)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }}

    function buildEventTooltip(idx) {{
      const cur = pointAt(idx);
      const prev = pointAt(idx - 1);
      if (!prev) return "";
      const p = cur.period;
      const kind = eventKindAt(idx);
      if (kind === 1) {{
        const prevSet = new Set(prev.languages);
        const curSet = new Set(cur.languages);
        const added = cur.languages.filter(l => !prevSet.has(l));
        const removed = prev.languages.filter(l => !curSet.has(l));
        let body = "Zmiana skladu top " + topN + ".";
        if (added.length) body += " Wchodza: " + added.join(", ") + ".";
        if (removed.length) body += " Wychodza: " + removed.join(", ") + ".";
        return p + ": " + body;
      }}
      if (kind === 2) {{
        const prevOrd = prev.languages.join(" > ");
        const curOrd = cur.languages.join(" > ");
        return p + ": zmiana kolejnosci w top " + topN + ". Bylo: " + prevOrd + ". Jest: " + curOrd + ".";
      }}
      return "";
    }}

    function xPos(idx) {{
      if (PERIODS.length <= 1) return M.left + INNER_W / 2;
      return M.left + (idx / (PERIODS.length - 1)) * INNER_W;
    }}

    function yPos(share) {{
      const yMax = 100;
      return M.top + INNER_H - (share / yMax) * INNER_H;
    }}

    function yTicks() {{
      const ticks = [];
      for (let v = 0; v <= 100; v += 20) ticks.push(v);
      return ticks;
    }}

    function renderChart(upToIdx) {{
      const series = seriesForN();
      const visible = series.slice(0, upToIdx + 1);
      let s = `<svg viewBox="0 0 ${{W}} ${{H}}" xmlns="http://www.w3.org/2000/svg">`;

      yTicks().forEach(v => {{
        const y = yPos(v);
        s += `<line x1="${{M.left}}" y1="${{y}}" x2="${{M.left + INNER_W}}" y2="${{y}}" stroke="#e5e7eb" stroke-width="1"/>`;
        s += `<text x="${{M.left - 8}}" y="${{y}}" text-anchor="end" dominant-baseline="middle" font-size="10" fill="#666">${{v}}%</text>`;
      }});

      const step = Math.max(1, Math.floor(PERIODS.length / 8));
      PERIODS.forEach((p, i) => {{
        if (i % step !== 0 && i !== PERIODS.length - 1) return;
        const x = xPos(i);
        s += `<text x="${{x}}" y="${{H - 10}}" text-anchor="middle" font-size="9" fill="#666">${{p}}</text>`;
      }});

      if (visible.length > 1) {{
        const path = visible.map((d, i) => {{
          const idx = PERIODS.indexOf(d.period);
          return `${{i === 0 ? "M" : "L"}}${{xPos(idx)}} ${{yPos(d.share_pct)}}`;
        }}).join(" ");
        s += `<path d="${{path}}" fill="none" stroke="#c44e52" stroke-width="2.5"/>`;
      }}

      for (let idx = 1; idx <= upToIdx; idx++) {{
        const kind = eventKindAt(idx);
        if (!kind) continue;
        const d = pointAt(idx);
        const x = xPos(idx);
        const y = yPos(d.share_pct);
        const isCurrent = idx === upToIdx;
        const tip = escapeXml(buildEventTooltip(idx));
        const r = isCurrent ? 7 : 5.5;
        if (kind === 1) {{
          s += `<g class="event-marker">`;
          s += `<title>${{tip}}</title>`;
          s += `<circle cx="${{x}}" cy="${{y}}" r="${{r}}" fill="#f59e0b" stroke="#b45309" stroke-width="2"/>`;
          s += `<circle cx="${{x}}" cy="${{y}}" r="2" fill="#fff"/>`;
          s += `</g>`;
        }} else {{
          const sz = isCurrent ? 8 : 6.5;
          s += `<g class="event-marker">`;
          s += `<title>${{tip}}</title>`;
          s += `<path d="M ${{x}} ${{y - sz}} L ${{x + sz}} ${{y}} L ${{x}} ${{y + sz}} L ${{x - sz}} ${{y}} Z"`;
          s += ` fill="#6366f1" stroke="#4338ca" stroke-width="1.6"/>`;
          s += `</g>`;
        }}
      }}

      {{
        const d = pointAt(upToIdx);
        const x = xPos(upToIdx);
        const y = yPos(d.share_pct);
        if (!eventKindAt(upToIdx)) {{
          s += `<circle cx="${{x}}" cy="${{y}}" r="5" fill="#c44e52" stroke="#fff" stroke-width="1.5"/>`;
        }}
      }}

      const cx = xPos(upToIdx);
      s += `<line x1="${{cx}}" y1="${{M.top}}" x2="${{cx}}" y2="${{M.top + INNER_H}}" stroke="#1a56db" stroke-width="1.5" stroke-dasharray="4 3" opacity="0.75"/>`;

      s += `<text x="${{M.left}}" y="16" font-size="12" fill="#444">Laczny udzial top N (%)</text>`;
      s += `<text x="${{M.left + INNER_W}}" y="16" font-size="9" fill="#64748b" text-anchor="end">`;
      s += `Kolo pom.: zmiana skladu. Romby: tylko kolejnosc — najedz myszka po opis.</text>`;
      s += `</svg>`;
      stage.innerHTML = s;
    }}

    function renderLangPanel(idx) {{
      const cur = pointAt(idx);
      const prev = idx > 0 ? pointAt(idx - 1) : null;
      const comp = prev && compositionChanged(cur, prev);
      const reord = prev && orderOnlyChanged(cur, prev);
      const prevSet = new Set(prev ? prev.languages : []);
      const curSet = new Set(cur.languages);
      const pcts = cur.language_pct || [];

      let html = "";
      if (comp) {{
        const added = cur.languages.filter(l => !prevSet.has(l));
        const removed = prev.languages.filter(l => !curSet.has(l));
        let note = "Zmiana skladu top " + topN;
        if (added.length) note += " — +" + added.join(", ");
        if (removed.length) note += (added.length ? "; " : " — ") + "-" + removed.join(", ");
        html += `<div class="change-note">${{note}}</div>`;
      }} else if (reord) {{
        html += `<div class="change-note">Zmiana kolejnosci w top ${{topN}} (ten sam zestaw jezykow)</div>`;
      }} else if (idx > 0) {{
        html += `<div class="no-change">Sklad i kolejnosc top ${{topN}} bez zmian wzgledem poprzedniego kwartalu</div>`;
      }}

      html += `<div class="chips">`;
      cur.languages.forEach((lang, i) => {{
        const isNew = comp && prev && !prevSet.has(lang);
        const cls = isNew ? "chip new" : "chip";
        const bg = COLORS[lang] || "#ddd";
        const pct = pcts[i] != null ? pcts[i].toFixed(1) + "%" : "";
        html += `<span class="chip-wrap">`;
        html += `<span class="${{cls}}" style="background:${{bg}}">${{lang}}</span>`;
        html += `<span class="chip-pct">${{pct}}</span>`;
        html += `</span>`;
      }});
      if (comp && prev) {{
        prev.languages.filter(l => !curSet.has(l)).forEach(lang => {{
          const bg = COLORS[lang] || "#ddd";
          const pi = prev.languages.indexOf(lang);
          const prevPcts = prev.language_pct || [];
          const pct = prevPcts[pi] != null ? prevPcts[pi].toFixed(1) + "%" : "";
          html += `<span class="chip-wrap">`;
          html += `<span class="chip out" style="background:${{bg}}">${{lang}}</span>`;
          html += `<span class="chip-pct">${{pct}}</span>`;
          html += `</span>`;
        }});
      }}
      html += `</div>`;
      langPanel.innerHTML = html;
    }}

    function refresh() {{
      const pt = pointAt(periodIndex);
      periodLabel.textContent = currentPeriod();
      periodSelect.value = String(periodIndex);
      shareLabel.textContent = pt ? `Lacznie: ${{pt.share_pct.toFixed(1)}}%` : "";
      renderChart(periodIndex);
      renderLangPanel(periodIndex);
    }}

    function resolvePeriodIndex(idx) {{
      if (loopEnabled) return (idx + PERIODS.length) % PERIODS.length;
      return Math.max(0, Math.min(PERIODS.length - 1, idx));
    }}

    function goPeriod(idx) {{
      periodIndex = resolvePeriodIndex(idx);
      refresh();
    }}

    function stopSlideshow() {{
      if (timer) {{ clearInterval(timer); timer = null; }}
      document.getElementById("btnPlay").textContent = "Odtwarzaj";
    }}

    function startSlideshow() {{
      stopSlideshow();
      document.getElementById("btnPlay").textContent = "Pauza";
      const ms = parseInt(document.getElementById("speedRange").value, 10);
      timer = setInterval(() => {{
        if (periodIndex >= PERIODS.length - 1 && !loopEnabled) {{
          stopSlideshow();
          return;
        }}
        goPeriod(periodIndex + 1);
      }}, ms);
    }}

    document.getElementById("btnLoop").addEventListener("click", () => {{
      loopEnabled = !loopEnabled;
      syncLoopButton();
    }});

    topNRange.addEventListener("input", () => {{
      topN = parseInt(topNRange.value, 10);
      topNVal.textContent = String(topN);
      refresh();
    }});

    document.getElementById("btnFirst").addEventListener("click", () => {{ stopSlideshow(); goPeriod(0); }});
    document.getElementById("btnPrev").addEventListener("click", () => goPeriod(periodIndex - 1));
    document.getElementById("btnNext").addEventListener("click", () => goPeriod(periodIndex + 1));
    document.getElementById("btnLast").addEventListener("click", () => {{ stopSlideshow(); goPeriod(PERIODS.length - 1); }});
    periodSelect.addEventListener("change", () => {{ stopSlideshow(); goPeriod(parseInt(periodSelect.value, 10)); }});
    document.getElementById("speedRange").addEventListener("input", () => {{
      document.getElementById("speedVal").textContent = document.getElementById("speedRange").value;
      syncSpeedStepHint();
      if (timer) startSlideshow();
    }});
    document.getElementById("btnPlay").addEventListener("click", () => {{
      if (timer) stopSlideshow();
      else startSlideshow();
    }});

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

    out_html = VIZ_DIR / "concentration_viewer.html"
    out_json = VIZ_DIR / "data" / "concentration_viewer.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    out_html.write_text(render_html(payload), encoding="utf-8")
    print(f"Saved {out_html.name}")


if __name__ == "__main__":
    main()
