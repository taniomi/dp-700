#!/usr/bin/env python3
"""Parse a Microsoft Learn practice-assessment results page (full page HTML,
copied via DevTools -> Copy outerHTML on <html>) into structured records and
append them to assessments/data/questions.jsonl.

Usage: python3 scripts/parse_assessment.py assessments/assessment-N.html [--date YYYY-MM-DD] [--url URL]
       (--date is only needed to override the date the page itself reports)
"""
import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TAXONOMY_PATH = REPO_ROOT / "scripts" / "taxonomy.yaml"
DATA_PATH = REPO_ROOT / "assessments" / "data" / "questions.jsonl"
ASSESSMENTS_PATH = REPO_ROOT / "assessments" / "data" / "assessments.jsonl"

ARTICLE_RE = re.compile(r'<article class="padding-top-md">(.*?)</article>', re.S)
QNUM_RE = re.compile(r"\s*<h2>Question (\d+) of \d+</h2>")
TAG_RE = re.compile(r"<[^>]+>")
RESULTS_TITLE_RE = re.compile(r"Practice Assessment Results:\s*(.+?)</h1>")
# The page has rendered this heading in at least two locale formats across
# real exports: "July 21, 2026" and "27 July 2026".
DATE_FORMATS = ("%B %d, %Y", "%d %B %Y")


def strip_tags(fragment):
    """Collapse an HTML fragment down to clean, whitespace-normalized text."""
    return html.unescape(re.sub(r"\s+", " ", TAG_RE.sub(" ", fragment))).strip()


def load_taxonomy():
    return yaml.safe_load(TAXONOMY_PATH.read_text())


def classify(text, taxonomy):
    """Match question text + doc links against the keyword taxonomy.
    Returns (domain, subarea) or (None, None) if nothing matched."""
    low = text.lower()
    for domain, ddata in taxonomy["domains"].items():
        for subarea, sdata in ddata["subareas"].items():
            for kw in sdata["keywords"]:
                if re.search(kw, low):
                    return domain, subarea
    return None, None


def official_domain_for_objective(obj_code, taxonomy):
    """Map an official 'N.M Name' objective code straight to its domain/subarea
    by position, since the numbering matches the taxonomy file's order exactly."""
    m = re.match(r"(\d+)\.(\d+)", obj_code)
    if not m:
        return None, None
    domain_idx, subarea_idx = int(m.group(1)) - 1, int(m.group(2)) - 1
    domains = list(taxonomy["domains"].items())
    if not (0 <= domain_idx < len(domains)):
        return None, None
    domain_name, ddata = domains[domain_idx]
    subareas = list(ddata["subareas"].keys())
    if not (0 <= subarea_idx < len(subareas)):
        return domain_name, None
    return domain_name, subareas[subarea_idx]


def extract_date(page_html):
    """Pull the date out of the page's own "Practice Assessment Results: ..."
    heading and return it as YYYY-MM-DD, or None if the heading isn't found/parseable."""
    m = RESULTS_TITLE_RE.search(page_html)
    if not m:
        return None
    raw = html.unescape(m.group(1)).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_blocks(page_html):
    """Split the full results page into (question_num, article_html) pairs."""
    blocks = []
    for m in ARTICLE_RE.finditer(page_html):
        body = m.group(1)
        qm = QNUM_RE.match(body)
        if qm:
            blocks.append((int(qm.group(1)), body))
    return blocks


def extract_section(article_html, id_prefix):
    """Grab the inner HTML of <section id="{id_prefix}-N">...</section>."""
    m = re.search(rf'id="{id_prefix}-\d+">(.*?)</section>', article_html, re.S)
    return m.group(1) if m else ""


def split_rationale(correct_answer_html):
    """The rationale <div> is nested as the last child inside the
    'question-correct-answer' section, after the answer-choices list.
    Returns (choices_html, rationale_inner_html)."""
    m = re.search(r'id="question-rationale-\d+">(.*)</div>\s*$', correct_answer_html, re.S)
    if not m:
        return correct_answer_html, ""
    return correct_answer_html[: m.start()], m.group(1)


def parse_rationale(rationale_html):
    """Parse a question's rationale <div> inner HTML into (objective_code, explanation, links).

    Two formats show up in practice:
    - "Rich": explicit <strong>Objective:</strong> / <strong>What This Item Tests:</strong> /
      <strong>Additional Reading:</strong> / <strong>Rationale:</strong> sections, with
      Additional Reading as an actual <ul><li><a href="...">Title</a></li></ul> list.
    - "Simple": no headers at all -- just explanatory <p> text, ending in one or more bare
      <p><a href="...">Title</a></p> paragraphs with no surrounding sentence.

    links must be a list of {"title": str, "url": str} dicts, in document order,
    pulling the real href (not just the anchor text) out of the HTML.
    """
    links = [
        {"title": html.unescape(title), "url": url}
        for url, title in re.findall(r'<a href="([^"]+)">([^<]+)</a>', rationale_html)
    ]

    if "Objective:" in rationale_html:
        obj_match = re.search(
            r"<strong>Objective:</strong></p>\s*<p>(.*?)</p>", rationale_html, re.S
        )
        objective_code = strip_tags(obj_match.group(1)) if obj_match else None

        rationale_match = re.search(
            r"<strong>Rationale:</strong></p>\s*<p>(.*?)</p>\s*$", rationale_html, re.S
        )
        explanation = strip_tags(rationale_match.group(1)) if rationale_match else ""
    else:
        objective_code = None
        # Strip out the bare link paragraphs, leaving only the explanatory <p> tags.
        no_links = re.sub(r"<p>\s*<a href=[^>]+>[^<]+</a>\s*</p>", "", rationale_html)
        explanation = strip_tags(no_links)

    return objective_code, explanation, links


def parse_question(num, article_html, taxonomy):
    legend_html = extract_section(article_html, "question-legend")
    your_html = extract_section(article_html, "question-selected-answer")
    correct_answer_html = extract_section(article_html, "question-correct-answer")
    choices_html, rationale_html = split_rationale(correct_answer_html)

    q_text = strip_tags(legend_html)

    is_wrong = (
        len(re.findall(r"This answer is incorrect\.", your_html)) > 0
        or len(re.findall(r"This answer is (?:in)?correct\.", your_html))
        != len(re.findall(r"This answer is correct\.", choices_html))
    )

    objective_code, explanation, links = parse_rationale(rationale_html)

    # Classification: official objective code wins when present. Otherwise, check
    # the doc link title(s) first -- a specific, deliberate signal -- before falling
    # back to the full question+explanation text, which often contains generic
    # scenario-setup words (e.g. "the lakehouse contains...") that can spuriously
    # match a keyword from an unrelated domain if checked first.
    domain = subarea = None
    tag_source = "unclassified"
    if objective_code:
        domain, subarea = official_domain_for_objective(objective_code, taxonomy)
        tag_source = "official" if domain else "unclassified"
    if not domain and links:
        domain, subarea = classify(" ".join(l["title"] for l in links), taxonomy)
        tag_source = "inferred" if domain else "unclassified"
    if not domain:
        domain, subarea = classify(q_text + " " + explanation, taxonomy)
        tag_source = "inferred" if domain else "unclassified"

    return {
        "question_num": num,
        "domain": domain,
        "subarea": subarea,
        "tag_source": tag_source,
        "objective_code": objective_code,
        "correct": not is_wrong,
        "concept": links[0]["title"] if links else None,
        "question_excerpt": q_text[:220],
        "explanation": explanation,
        "links": links,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Parse a Microsoft Learn practice-assessment HTML export."
    )
    parser.add_argument("path", type=Path, help="assessments/assessment-N.html")
    parser.add_argument(
        "--date", help="Assessment date, YYYY-MM-DD (overrides the page's own date heading)"
    )
    parser.add_argument(
        "--url", required=True, help="Link to the results page, for provenance"
    )
    args = parser.parse_args()

    assessment_id = args.path.stem  # e.g. "assessment-4"
    page_html = args.path.read_text(encoding="utf-8")
    date = args.date or extract_date(page_html)
    source_url = args.url
    if not date:
        print(
            "Couldn't find a 'Practice Assessment Results: <Month D, YYYY>' heading "
            "in the page, and no --date was given. Pass --date YYYY-MM-DD explicitly."
        )
        sys.exit(1)

    if DATA_PATH.exists():
        existing_ids = {
            json.loads(line)["assessment_id"]
            for line in DATA_PATH.read_text().splitlines()
            if line.strip()
        }
        if assessment_id in existing_ids:
            print(
                f"'{assessment_id}' is already in {DATA_PATH.relative_to(REPO_ROOT)}. "
                "Remove its lines first if you want to re-parse it."
            )
            sys.exit(1)

    taxonomy = load_taxonomy()
    blocks = parse_blocks(page_html)
    if not blocks:
        print("No 'Question N of M' articles found -- is this a full results-page HTML export?")
        sys.exit(1)

    records = []
    needs_review = []
    for num, body in blocks:
        rec = parse_question(num, body, taxonomy)
        rec["assessment_id"] = assessment_id
        rec["date"] = date
        rec["source_url"] = source_url
        records.append(rec)
        if rec["tag_source"] == "unclassified":
            needs_review.append(rec["question_num"])

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    correct = sum(r["correct"] for r in records)
    with ASSESSMENTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "assessment_id": assessment_id,
            "date": date,
            "source_url": source_url,
            "questions": len(records),
            "correct": correct,
        }) + "\n")

    print(f"Parsed {len(records)} questions from {assessment_id}: {correct}/{len(records)} correct")
    print(f"Appended to {DATA_PATH.relative_to(REPO_ROOT)} and {ASSESSMENTS_PATH.relative_to(REPO_ROOT)}")
    print(f"{args.path} can now be safely deleted -- its data is durably captured above.")
    if needs_review:
        print(f"\nNEEDS REVIEW -- no taxonomy match for question(s): {needs_review}")
        print("Edit scripts/taxonomy.yaml to add keywords, or fix these records by hand in questions.jsonl.")
    else:
        print("All questions classified.")


if __name__ == "__main__":
    main()
