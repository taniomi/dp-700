#!/usr/bin/env python3
"""Render assessments/data/questions.jsonl into assessments/dashboard.bento.html,
the cross-attempt rollup (readiness score, accuracy trend per domain, persistent
gaps) as an interactive Bento Slides deck.

Usage: python3 scripts/render_views.py

assessments/dashboard.bento.html must already exist (a self-contained Bento
Slides app + document). If it doesn't, fetch the base app once:
    curl -fsSL https://bento.page/releases/slides/Bento_Slides.bento.html \
        -o assessments/dashboard.bento.html
This script only ever rewrites the JSON inside that file's #bento-doc
<script> block -- it never regenerates the surrounding app shell.
"""
import json
import re
from collections import defaultdict
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TAXONOMY_PATH = REPO_ROOT / "scripts" / "taxonomy.yaml"
DATA_PATH = REPO_ROOT / "assessments" / "data" / "questions.jsonl"
ASSESSMENTS_DIR = REPO_ROOT / "assessments"
EXAM_RESULT_PATH = ASSESSMENTS_DIR / "data" / "exam_result.json"
DASHBOARD_BENTO_PATH = ASSESSMENTS_DIR / "dashboard.bento.html"

BG = "#12141C"
FG = "#F2F0EA"
MUTED = "#8A8FA3"
ACCENT = "#5CC8FF"
PASS_COLOR = "#3DDC84"
DOMAIN_COLORS = ["#5CC8FF", "#FFB454", "#FF6B81", "#7ED9A8", "#C49BFF", "#FFE066", "#4FD1C5"]
FONT = "system-ui, sans-serif"
MARGIN_X = 96
CONTENT_W = 1280 - 2 * MARGIN_X


def load_records():
    if not DATA_PATH.exists():
        return []
    return [json.loads(l) for l in DATA_PATH.read_text().splitlines() if l.strip()]


def load_taxonomy():
    return yaml.safe_load(TAXONOMY_PATH.read_text())


def deck_title(taxonomy):
    """Stable per-exam title. _existing_doc_id keys off it, so it must not change
    between runs or the deck forks its Bento docId."""
    return f"{taxonomy['exam_code']} Readiness Dashboard"


def load_exam_result():
    """Optional: the actual certification result, once the exam is taken. Kept as
    its own small data file (like questions.jsonl / assessments.jsonl) rather than
    hand-edited into the deck JSON, so re-running this script never clobbers it."""
    if not EXAM_RESULT_PATH.exists():
        return None
    return json.loads(EXAM_RESULT_PATH.read_text())


# ---------------------------------------------------------------------------
# Domain-weighted readiness score
# ---------------------------------------------------------------------------
def _weighted_score(records, taxonomy):
    """Hierarchical weighted accuracy over one set of records:
    subarea accuracy -> equal-weighted average per domain (Microsoft doesn't
    publish subarea percentages) -> domain-weighted overall score using the
    real exam's published weights.

    Domains/subareas with zero questions in `records` are excluded rather than
    counted as 0%, and the remaining weights are renormalized so they still sum
    to 100 -- otherwise an unstudied area would either crash the average or
    unfairly drag the score down.
    """
    by_key = defaultdict(lambda: {"c": 0, "t": 0})
    for r in records:
        if r["domain"] and r["subarea"]:
            by_key[(r["domain"], r["subarea"])]["t"] += 1
            by_key[(r["domain"], r["subarea"])]["c"] += r["correct"]

    by_domain = {}
    total_weight_used = 0.0
    for domain, ddata in taxonomy["domains"].items():
        subarea_accuracies = []
        subarea_n = {}
        for subarea in ddata["subareas"]:
            d = by_key.get((domain, subarea))
            if d and d["t"] > 0:
                subarea_accuracies.append(d["c"] / d["t"])
                subarea_n[subarea] = d["t"]
        if not subarea_accuracies:
            continue  # no data anywhere in this domain yet -- exclude, renormalize below
        domain_accuracy = sum(subarea_accuracies) / len(subarea_accuracies)
        by_domain[domain] = {
            "accuracy": domain_accuracy * 100,
            "weight_pct": ddata["weight_pct"],
            "n": sum(subarea_n.values()),
            "subarea_n": subarea_n,
        }
        total_weight_used += ddata["weight_pct"]

    if not by_domain:
        return None, {}

    overall = 0.0
    for d in by_domain.values():
        normalized_weight = d["weight_pct"] / total_weight_used
        d["contribution"] = d["accuracy"] * normalized_weight
        overall += d["contribution"]

    return overall, by_domain


def compute_readiness_score(records, taxonomy, recent_n=5):
    """Two readiness signals: one from every attempt ever logged, one from just
    the most recent `recent_n` attempts -- the first is the stable baseline, the
    second answers "am I ready right now" without being diluted by mistakes you
    already fixed weeks ago. Both use the same domain/subarea weighting."""
    dated_attempts = sorted(
        {(r["assessment_id"], r.get("date") or "") for r in records},
        key=lambda x: x[1],
    )
    attempt_order = [a for a, _ in dated_attempts]
    recent_ids = set(attempt_order[-recent_n:])
    recent_records = [r for r in records if r["assessment_id"] in recent_ids]

    overall_score, overall_by_domain = _weighted_score(records, taxonomy)
    recent_score, recent_by_domain = _weighted_score(recent_records, taxonomy)

    return {
        "overall": overall_score,
        "by_domain": overall_by_domain,
        "recent": {
            "score": recent_score,
            "by_domain": recent_by_domain,
            "attempts_included": sorted(recent_ids),
        },
    }


# ---------------------------------------------------------------------------
# Bento Slides dashboard
# ---------------------------------------------------------------------------
def accuracy_color(pct):
    """Map a domain's accuracy percentage to a status color for the readiness
    table (used to bg-color the Accuracy cell so gaps jump out at a glance)."""
    if pct >= 85:
        return "#234A33"  # on track — meets the 85% pass bar
    if pct >= 60:
        return "#4A3923"  # needs work
    return "#4A2330"  # priority gap — same muted red as the gaps-table badge


def _domain_trend(records, taxonomy, attempts):
    """domain -> [accuracy_pct_or_None per attempt in `attempts` order],
    skipping domains with no data in any attempt."""
    per_domain = defaultdict(list)
    for a in attempts:
        _, by_domain = _weighted_score([r for r in records if r["assessment_id"] == a], taxonomy)
        for domain in taxonomy["domains"]:
            d = by_domain.get(domain)
            per_domain[domain].append(round(d["accuracy"], 1) if d else None)
    return {d: accs for d, accs in per_domain.items() if any(a is not None for a in accs)}


def _existing_doc_id(html_text, title):
    """Reuse the docId Bento minted on first open of *our* deck, so re-running
    this script doesn't fork the document identity. A pristine, never-opened
    template (or someone else's deck) is not ours -- start fresh instead."""
    if not re.search(r'"title"\s*:\s*"' + re.escape(title) + '"', html_text):
        return None
    m = re.search(r'"docId"\s*:\s*"([^"]+)"', html_text)
    return m.group(1) if m else None


def _text(id, x, y, w, h, html, size, weight=600, color=FG, align="left", valign="top", **fx):
    el = {
        "id": id, "type": "text", "x": x, "y": y, "w": w, "h": h,
        "rotation": 0, "opacity": 1, "html": html, "fontSize": size,
        "fontFamily": FONT, "fontWeight": weight, "color": color,
        "align": align, "valign": valign, "lineHeight": 1.15,
    }
    if fx:
        el["fx"] = fx
    return el


def _slide_heading(slide_id, title):
    return [
        _text(f"{slide_id}-title", MARGIN_X, 64, CONTENT_W, 64, title, 36, weight=800),
        {"id": f"{slide_id}-rule", "type": "shape", "shape": "rect", "x": MARGIN_X, "y": 128,
         "w": 64, "h": 6, "fill": ACCENT, "stroke": "none", "strokeWidth": 0, "radius": 3,
         "rotation": 0, "opacity": 1},
    ]


def _cert_slide(result, exam_code):
    """The actual exam result, if `exam_result.json` exists. Placed first: once
    you've passed, that's the headline and the practice-test slides become the
    historical record behind it, not the thing being led with."""
    title_html = (f"<div>{result['exam_code']}</div><div>{result['exam_title']}</div>"
                  if result.get("exam_code") and result.get("exam_title")
                  else result.get("exam", exam_code))

    elements = [
        # Hand-tuned in the Bento editor on 2026-08-13 (bigger/reordered header,
        # wider ring, bars shifted down + indented) — coordinates below capture
        # that layout so re-running this script doesn't reset it.
        {"id": "cert-ring", "type": "shape", "shape": "ellipse", "x": 290, "y": 59.7, "w": 700, "h": 365,
         "fill": "transparent", "stroke": PASS_COLOR, "strokeWidth": 2, "strokeStyle": "dashed",
         "radius": 0, "rotation": 0, "opacity": 0.35, "fx": {"loop": {"type": "dash-march"}}},
        _text("cert-title", MARGIN_X, 82.7, CONTENT_W, 64, title_html,
              26.67, weight=600, color=FG, align="center"),
        _text("cert-score", 340, 154.7, 600, 150, str(result["score"]), 120, weight=900, color=PASS_COLOR,
              align="center", valign="middle", enter="fade-up", countUp=True),
        _text("cert-score-sub", MARGIN_X, 312.7, CONTENT_W, 30,
              f"Passing score: {result['passing_score']} / {result['max_score']}",
              18, weight=500, color=MUTED, align="center"),
        _text("cert-date", MARGIN_X, 340.7, CONTENT_W, 26, f"Passed {result.get('date', '')}",
              14, weight=500, color=MUTED, align="center"),
        _text("cert-badge", MARGIN_X, 366.6, CONTENT_W, 40, f"✅ {result.get('result', 'Pass').upper()}",
              24, weight=800, color=PASS_COLOR, align="center"),
        _text("cert-rank-label", MARGIN_X, 455.4, CONTENT_W, 28,
              "Domain performance", 16, weight=700, color=FG, align="center"),
    ]

    # Per-domain bars, ranked strongest to weakest by the actual percentage
    # from the post-exam results graph (rather than a bare ordinal list).
    perf = sorted((result.get("domain_performance") or {}).items(), key=lambda kv: -kv[1])
    label_x, label_w, bar_w, row_h, row0 = MARGIN_X + 106.1, 400, 380, 56, 504.7
    # The hand-tuned 56px step fits 3 domains; exams with more (e.g. AZ-104 has 5)
    # compress the step so the last 32px-tall row still ends above y=700.
    if len(perf) > 3:
        row_h = min(row_h, (700 - 32 - row0) / (len(perf) - 1))
    bar_x = label_x + label_w
    for i, (domain, pct) in enumerate(perf):
        y = row0 + i * row_h
        color = DOMAIN_COLORS[i % len(DOMAIN_COLORS)]
        fill_w = max(4, round(bar_w * min(pct, 100) / 100))
        elements += [
            _text(f"cert-bar-label-{i}", label_x, y, label_w, 32, domain, 17, weight=600,
                  color=FG, valign="middle"),
            {"id": f"cert-bar-bg-{i}", "type": "shape", "shape": "rect", "x": bar_x, "y": y + 4,
             "w": bar_w, "h": 22, "fill": "rgba(242,240,234,0.08)", "stroke": "none", "strokeWidth": 0,
             "radius": 11, "rotation": 0, "opacity": 1},
            {"id": f"cert-bar-fg-{i}", "type": "shape", "shape": "rect", "x": bar_x, "y": y + 4,
             "w": fill_w, "h": 22, "fill": color, "stroke": "none", "strokeWidth": 0,
             "radius": 11, "rotation": 0, "opacity": 1, "fx": {"enter": "fade-up"}},
            _text(f"cert-bar-pct-{i}", bar_x + bar_w + 16, y, 80, 32, f"+{pct}%", 17, weight=700,
                  color=color, valign="middle"),
        ]

    return {"id": "s-cert", "background": BG, "transition": "none",
            "notes": f"Actual {exam_code} certification exam result — the headline, ahead of the practice history below.",
            "elements": elements}


def build_bento_doc(records, taxonomy, existing_doc_id, exam_result=None):
    attempts = sorted(set(r["assessment_id"] for r in records))
    score = compute_readiness_score(records, taxonomy)
    overall, by_domain = score["overall"], score["by_domain"]
    recent = score["recent"]

    slides = []

    if exam_result:
        slides.append(_cert_slide(exam_result, taxonomy["exam_code"]))

    # --- Cover -------------------------------------------------------------
    # Hand-tuned in the Bento editor on 2026-08-14 (smaller/repositioned ring,
    # shorter headline, smaller score, sub pushed down) — coordinates below
    # capture that layout so re-running this script doesn't reset it.
    cover_elements = [
        {"id": "ring", "type": "shape", "shape": "ellipse", "x": 440, "y": 160, "w": 400, "h": 400,
         "fill": "transparent", "stroke": ACCENT, "strokeWidth": 2, "strokeStyle": "dashed",
         "radius": 0, "rotation": 0, "opacity": 0.3, "fx": {"loop": {"type": "dash-march"}}},
        _text("cover-title", MARGIN_X, 80, CONTENT_W, 80, f"{taxonomy['exam_code']} Readiness Score", 44, weight=800, align="center"),
        _text("score-big", 340, 220, 600, 280, f"{overall:.0f}%" if overall is not None else "—",
              133.33, weight=900, color=ACCENT, align="center", valign="middle",
              enter="fade-up", countUp=True),
        _text("cover-sub", MARGIN_X, 578.7, CONTENT_W, 40,
              f"Domain-weighted readiness — {len(attempts)} attempt(s), {len(records)} questions logged",
              22, weight=500, color=MUTED, align="center"),
    ]
    slides.append({"id": "s-cover", "background": BG, "transition": "none",
                    "notes": "Overall readiness score, weighted by Microsoft's published exam domain weights.",
                    "elements": cover_elements})

    # --- Readiness by domain -------------------------------------------------
    domain_rows = [{"cells": [{"html": "Domain"}, {"html": "Accuracy", "align": "right"},
                               {"html": "Weight", "align": "right"}, {"html": "Seen", "align": "right"},
                               {"html": "Contribution", "align": "right"}]}]
    for domain, d in by_domain.items():
        domain_rows.append({"cells": [
            {"html": domain},
            {"html": f"{d['accuracy']:.0f}%", "align": "right", "bg": accuracy_color(d["accuracy"])},
            {"html": f"{d['weight_pct']}%", "align": "right"},
            {"html": str(d["n"]), "align": "right"},
            {"html": f"{d['contribution']:.1f}", "align": "right"},
        ]})
    domains_elements = _slide_heading("s-domains", "Readiness by domain") + [
        _text("score-big", MARGIN_X, 150, 260, 100, f"{overall:.0f}%" if overall is not None else "—",
              64, weight=900, color=ACCENT, valign="middle"),
        _text("score-label", MARGIN_X, 250, 260, 30, "Overall (all attempts)", 16, color=MUTED),
        _text("score-recent", MARGIN_X, 285, 260, 60,
              f"Recent (last 5): <b>{recent['score']:.0f}%</b>" if recent["score"] is not None else "",
              16, color=MUTED),
        {"id": "domains-table", "type": "table", "x": 380, "y": 150, "w": 800, "h": 340,
         "rotation": 0, "opacity": 1, "header": True,
         "columns": [{"w": 2.2}, {"w": 1}, {"w": 0.8}, {"w": 0.8}, {"w": 1.2}],
         "rows": domain_rows,
         "style": {"headerBg": "#1E2230", "headerColor": FG, "zebra": "rgba(242,240,234,0.04)",
                   "borderColor": "rgba(242,240,234,0.14)", "borderWidth": 1, "cellPadX": 14,
                   "cellPadY": 10, "fontSize": 16, "color": FG, "radius": 8}},
    ]
    slides.append({"id": "s-domains", "background": BG, "transition": "morph",
                    "notes": "Per-domain accuracy, exam weight, questions seen, and weighted contribution to the overall score.",
                    "elements": domains_elements})

    # --- Trend per domain across attempts -----------------------------------
    trend = _domain_trend(records, taxonomy, attempts)
    series = []
    for i, (domain, accs) in enumerate(trend.items()):
        color = DOMAIN_COLORS[i % len(DOMAIN_COLORS)]
        series.append({"type": "line", "name": domain, "data": accs, "smooth": True,
                        "itemStyle": {"color": color}, "lineStyle": {"color": color}})
    trend_elements = _slide_heading("s-trend", "Accuracy trend by domain") + [
        {"id": "trend-chart", "type": "chart", "x": MARGIN_X, "y": 170, "w": CONTENT_W, "h": 460,
         "rotation": 0, "opacity": 1, "preset": "line",
         "option": {
             "xAxis": {"type": "category", "data": attempts},
             "yAxis": {"type": "value", "min": 0, "max": 100, "axisLabel": {"formatter": "{value}%"}},
             "legend": {"top": 0, "textStyle": {"color": FG}},
             "tooltip": {"trigger": "axis", "formatter": "{b}<br/>{a}: {c}%"},
             "series": series,
         },
         "fx": {"enter": "fade-up"}},
    ] if series else _slide_heading("s-trend", "Accuracy trend by domain") + [
        _text("trend-empty", MARGIN_X, 300, CONTENT_W, 60, "Not enough attempts yet for a trend.", 20, color=MUTED)
    ]
    slides.append({"id": "s-trend", "background": BG, "transition": "none",
                    "notes": "Domain-level accuracy across attempts, in taxonomy order.",
                    "elements": trend_elements})

    # --- Persistent gaps ------------------------------------------------------
    concept_misses = defaultdict(set)
    concept_domain = {}
    for r in records:
        if not r["correct"] and r["concept"]:
            concept_misses[r["concept"]].add(r["assessment_id"])
            concept_domain[r["concept"]] = (r["domain"], r["subarea"])
    persistent = sorted(
        ((c, a) for c, a in concept_misses.items() if len(a) >= 2),
        key=lambda x: -len(x[1]),
    )
    gaps_elements = _slide_heading("s-gaps", "Persistent gaps (missed in 2+ attempts)")
    if persistent:
        gap_rows = [{"cells": [{"html": "Concept"}, {"html": "Missed", "align": "right"}, {"html": "Domain / Subarea"}]}]
        for concept, attempt_set in persistent:
            domain, subarea = concept_domain[concept]
            gap_rows.append({"cells": [
                {"html": concept}, {"html": f"{len(attempt_set)}×", "align": "right", "bg": "#4A2330"},
                {"html": f"{domain} / {subarea}"},
            ]})
        gaps_elements.append({
            "id": "gaps-table", "type": "table", "x": MARGIN_X, "y": 170, "w": CONTENT_W, "h": 460,
            "rotation": 0, "opacity": 1, "header": True,
            "columns": [{"w": 1.6}, {"w": 0.5}, {"w": 1.6}], "rows": gap_rows,
            "style": {"headerBg": "#1E2230", "headerColor": FG, "zebra": "rgba(242,240,234,0.04)",
                      "borderColor": "rgba(242,240,234,0.14)", "borderWidth": 1, "cellPadX": 14,
                      "cellPadY": 10, "fontSize": 16, "color": FG, "radius": 8},
        })
    else:
        gaps_elements.append(_text("gaps-empty", MARGIN_X, 200, CONTENT_W, 60,
                                    "None yet — persistent gaps need the same concept missed across 2+ logged attempts.",
                                    20, color=MUTED))
    slides.append({"id": "s-gaps", "background": BG, "transition": "none",
                    "notes": "Concepts missed across two or more attempts — the highest-priority review list.",
                    "elements": gaps_elements})

    # --- New misses from the most recent attempt ------------------------------
    if attempts:
        latest = attempts[-1]
        latest_misses = sorted(c for c, a in concept_misses.items() if a == {latest})
        new_elements = _slide_heading("s-new", f"New misses — {latest} (not yet recurring)")
        if latest_misses:
            rows = [{"cells": [{"html": "Concept"}, {"html": "Domain / Subarea"}]}]
            for concept in latest_misses:
                domain, subarea = concept_domain[concept]
                rows.append({"cells": [{"html": concept}, {"html": f"{domain} / {subarea}"}]})
            new_elements.append({
                "id": "new-table", "type": "table", "x": MARGIN_X, "y": 170, "w": CONTENT_W, "h": 460,
                "rotation": 0, "opacity": 1, "header": True,
                "columns": [{"w": 1.6}, {"w": 1.6}], "rows": rows,
                "style": {"headerBg": "#1E2230", "headerColor": FG, "zebra": "rgba(242,240,234,0.04)",
                          "borderColor": "rgba(242,240,234,0.14)", "borderWidth": 1, "cellPadX": 14,
                          "cellPadY": 10, "fontSize": 16, "color": FG, "radius": 8},
            })
        else:
            new_elements.append(_text("new-empty", MARGIN_X, 200, CONTENT_W, 60, "None.", 20, color=MUTED))
        slides.append({"id": "s-new", "background": BG, "transition": "none",
                        "notes": "Misses that only showed up in the most recent attempt — not yet confirmed as persistent.",
                        "elements": new_elements})

    # --- Needs review (unclassified questions) --------------------------------
    unclassified = [r for r in records if r["tag_source"] == "unclassified"]
    if unclassified:
        review_elements = _slide_heading("s-review", "Needs review (no taxonomy match)")
        rows = [{"cells": [{"html": "Attempt"}, {"html": "Question"}]}]
        for r in unclassified:
            rows.append({"cells": [{"html": f"{r['assessment_id']} Q{r['question_num']}"},
                                    {"html": r["question_excerpt"][:120]}]})
        review_elements.append({
            "id": "review-table", "type": "table", "x": MARGIN_X, "y": 170, "w": CONTENT_W, "h": 460,
            "rotation": 0, "opacity": 1, "header": True,
            "columns": [{"w": 0.8}, {"w": 2.4}], "rows": rows,
            "style": {"headerBg": "#1E2230", "headerColor": FG, "zebra": "rgba(242,240,234,0.04)",
                      "borderColor": "rgba(242,240,234,0.14)", "borderWidth": 1, "cellPadX": 14,
                      "cellPadY": 10, "fontSize": 15, "color": FG, "radius": 8},
        })
        slides.append({"id": "s-review", "background": BG, "transition": "none",
                        "notes": "Questions the taxonomy keyword match couldn't classify — extend scripts/taxonomy.yaml.",
                        "elements": review_elements})

    doc = {
        "format": "bento/slides", "version": 1, "title": deck_title(taxonomy),
        "size": {"width": 1280, "height": 720},
        "theme": {"background": BG, "color": FG, "accent": ACCENT, "fontFamily": FONT},
        "slides": slides,
    }
    if existing_doc_id:
        doc["docId"] = existing_doc_id
    return doc


SCRIPT_RE = re.compile(
    r'(<script type="application/bento\+json" id="bento-doc">)(.*?)(</script>)', re.S
)


def write_bento_dashboard(records, taxonomy, exam_result=None):
    if not DASHBOARD_BENTO_PATH.exists():
        raise SystemExit(
            f"{DASHBOARD_BENTO_PATH.relative_to(REPO_ROOT)} doesn't exist yet. Fetch the base app once:\n"
            f"  curl -fsSL https://bento.page/releases/slides/Bento_Slides.bento.html "
            f"-o {DASHBOARD_BENTO_PATH.relative_to(REPO_ROOT)}"
        )
    html = DASHBOARD_BENTO_PATH.read_text()
    doc = build_bento_doc(records, taxonomy, _existing_doc_id(html, deck_title(taxonomy)), exam_result)
    payload = json.dumps(doc, ensure_ascii=False).replace("<", "\\u003c")
    new_html, n = SCRIPT_RE.subn(lambda m: m.group(1) + payload + m.group(3), html, count=1)
    if n == 0:
        raise SystemExit(f"Could not find #bento-doc block in {DASHBOARD_BENTO_PATH.relative_to(REPO_ROOT)}")
    DASHBOARD_BENTO_PATH.write_text(new_html)


def main():
    records = load_records()
    if not records:
        print(f"No records in {DATA_PATH.relative_to(REPO_ROOT)} yet — run parse_assessment.py first.")
        return
    taxonomy = load_taxonomy()
    exam_result = load_exam_result()

    write_bento_dashboard(records, taxonomy, exam_result)
    print(f"Wrote {DASHBOARD_BENTO_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
