#!/usr/bin/env python3
"""Build the council HTML report from the files in a council output folder.

Usage: python3 render_report.py <OUT_DIR>

Reads (whatever exists): meta.json, brief.md, verdict.md, advisor-*.md,
review-*.md, mapping.md, act.md. Writes <OUT_DIR>/report.html.
No third-party dependencies.
"""
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

CSS_PATH = Path(__file__).resolve().parent.parent / "assets" / "report.css"
ADVISOR_COLORS = {
    "breaker": "--breaker", "architect": "--architect", "simplifier": "--simplifier",
    "newcomer": "--newcomer", "operator": "--operator",
}
STANCE_CLASSES = [
    ("crit", ("critical", "rejected", "negative")),
    ("pos", ("positive", "chosen", "base")),
    ("mixed", ("mixed", "grafted", "partial")),
]


# ---------- tiny markdown to HTML ----------

def render_inline(text: str) -> str:
    """Escape HTML, then apply inline code, bold and severity badges."""
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"\b(P[012])\b", lambda m: f'<span class="sev sev-{m[1].lower()}">{m[1]}</span>', text)


def is_table_row(line: str) -> bool:
    return line.strip().startswith("|") and line.strip().endswith("|")


def split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def render_table(rows: list[str]) -> str:
    """Render markdown table rows (header, separator, body) as HTML."""
    header = split_row(rows[0])
    body = [split_row(r) for r in rows[1:] if not re.fullmatch(r"[\s|:\-]+", r)]
    head_html = "".join(f"<th>{render_inline(c)}</th>" for c in header)
    body_html = "".join(
        "<tr>" + "".join(f"<td>{render_inline(c)}</td>" for c in row) + "</tr>" for row in body
    )
    return f'<div class="table-wrap"><table><thead><tr>{head_html}</tr></thead><tbody>{body_html}</tbody></table></div>'


def take_block(lines: list[str], start: int, predicate) -> tuple[list[str], int]:
    """Collect consecutive lines from start while predicate holds."""
    end = start
    while end < len(lines) and predicate(lines[end]):
        end += 1
    return lines[start:end], end


def render_list(items: list[str]) -> str:
    ordered = bool(re.match(r"\s*\d+[.)]\s", items[0]))
    tag = "ol" if ordered else "ul"
    cleaned = [re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", item) for item in items]
    return f"<{tag}>" + "".join(f"<li>{render_inline(c)}</li>" for c in cleaned) + f"</{tag}>"


def render_code(lines: list[str], start: int) -> tuple[str, int]:
    """Render a fenced code block starting at lines[start]."""
    end = start + 1
    while end < len(lines) and not lines[end].strip().startswith("```"):
        end += 1
    code = html.escape("\n".join(lines[start + 1 : end]))
    return f"<pre><code>{code}</code></pre>", end + 1


def is_list_item(line: str) -> bool:
    return bool(re.match(r"\s*(?:[-*+]|\d+[.)])\s+", line))


def is_paragraph_line(line: str) -> bool:
    starts_block = line.lstrip().startswith(("#", "|", "```"))
    return bool(line.strip()) and not starts_block and not is_list_item(line)


def render_markdown(text: str) -> str:
    """Convert the small markdown subset councils produce into HTML."""
    lines, parts, i = text.splitlines(), [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.strip().startswith("```"):
            block, i = render_code(lines, i)
            parts.append(block)
        elif heading := re.match(r"(#{1,6})\s+(.*)", line):
            level = min(len(heading[1]) + 1, 4)
            parts.append(f"<h{level}>{render_inline(heading[2])}</h{level}>")
            i += 1
        elif is_table_row(line):
            rows, i = take_block(lines, i, is_table_row)
            parts.append(render_table(rows))
        elif is_list_item(line):
            items, i = take_block(lines, i, is_list_item)
            parts.append(render_list(items))
        else:
            para, i = take_block(lines, i, is_paragraph_line)
            parts.append(f"<p>{render_inline(' '.join(para))}</p>")
    return "\n".join(parts)


# ---------- reading the council files ----------

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def split_sections(markdown: str) -> dict[str, str]:
    """Split a document on '## ' headings into {lowercased title: body}."""
    sections, title, buffer = {}, "_intro", []
    for line in markdown.splitlines():
        if line.startswith("## "):
            sections[title] = "\n".join(buffer).strip()
            title, buffer = line[3:].strip().lower(), []
        else:
            buffer.append(line)
    sections[title] = "\n".join(buffer).strip()
    return sections


def find_section(sections: dict[str, str], *keywords: str) -> str:
    """Return the first section whose title contains any keyword."""
    for title, body in sections.items():
        if any(k in title for k in keywords):
            return body
    return ""


def stance_class(stance: str) -> str:
    lowered = stance.lower()
    for css_class, words in STANCE_CLASSES:
        if any(w in lowered for w in words):
            return f"st-{css_class}"
    return "st-mixed"


def parse_alignment(body: str) -> list[tuple[str, str, str]]:
    """Parse 'Advisor | stance | concern' lines."""
    rows = []
    for line in body.splitlines():
        cells = [c.strip(" -*`") for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0] and not re.fullmatch(r"[\s:\-]*", cells[0]) and cells[0].lower() != "advisor":
            rows.append((cells[0], cells[1], " | ".join(cells[2:])))
    return rows


def color_var(name: str) -> str:
    key = next((k for k in ADVISOR_COLORS if k in name.lower()), "architect")
    return ADVISOR_COLORS[key]


# ---------- page sections ----------

def alignment_html(rows: list[tuple[str, str, str]]) -> str:
    cards = "".join(
        f'<div class="adv" style="--c: var({color_var(n)})"><div class="name">{html.escape(n)}</div>'
        f'<span class="stance {stance_class(s)}">{html.escape(s)}</span>'
        f'<div class="concern">{render_inline(c)}</div></div>'
        for n, s, c in rows
    )
    return f'<section><h2>Advisor alignment</h2><div class="grid">{cards}</div></section>' if cards else ""


def box(title: str, body: str) -> str:
    return f'<section><h2>{title}</h2><div class="box">{render_markdown(body)}</div></section>' if body else ""


def collapsible(title: str, body: str, dot: str = "") -> str:
    marker = f'<span class="dot" style="--c: var({dot})"></span>' if dot else ""
    return f"<details><summary>{marker}{html.escape(title)}</summary><div>{render_markdown(body)}</div></details>"


def header_html(meta: dict, title: str) -> str:
    chips = [
        f"Repo: {meta.get('repo', '?')}",
        f"Base: {meta.get('branch', '?')} @ {str(meta.get('sha', ''))[:8]}",
        f"Tests: {meta.get('tests', 'n/a')}",
        f"Functions over limits: {meta.get('lizard_count', 'n/a')}",
    ]
    chip_html = "".join(f'<span class="chip">{html.escape(c)}</span>' for c in chips)
    return (
        f'<header><div class="eyebrow">Code Council · {html.escape(meta.get("mode", ""))} mode</div>'
        f"<h1>{html.escape(title)}</h1><div class=\"meta\">{chip_html}</div></header>"
    )


def verdict_html(sections: dict[str, str]) -> str:
    verdict = find_section(sections, "verdict")
    first = find_section(sections, "one thing", "first")
    first_html = f'<div class="first"><strong>Do this first:</strong> {render_markdown(first)}</div>' if first else ""
    return f'<section><h2>Verdict</h2><div class="verdict">{render_markdown(verdict)}{first_html}</div></section>'


def main_items_html(sections: dict[str, str]) -> str:
    fixes = find_section(sections, "prioritized fixes")
    if fixes:
        return box("Prioritized fixes", fixes)
    design = find_section(sections, "chosen design")
    plan = find_section(sections, "implementation plan")
    return box("Chosen design", design) + box("Implementation plan", plan)


def title_from(brief: str, meta: dict) -> str:
    match = re.search(r"(?im)^\s*[-*]?\s*\**goal\**\s*[:\-]\s*(.+)$", brief)
    if match:
        return match[1].strip()
    heading = re.search(r"(?m)^#\s+(.+)$", brief)
    return heading[1].strip() if heading else f"{meta.get('mode', 'council')} of {meta.get('repo', 'code')}"


def advisor_files(out: Path) -> list[Path]:
    return sorted(out.glob("advisor-*.md"))


def details_section(title: str, items: list[tuple[str, str, str]]) -> str:
    inner = "".join(collapsible(name, body, dot) for name, body, dot in items)
    return f"<section><h2>{title}</h2>{inner}</section>" if inner else ""


def footer_html(out: Path) -> str:
    transcript = html.escape(str(out / "transcript.md"))
    stamp = f"{datetime.now():%Y-%m-%d %H:%M}"
    return f"<footer>Code Council · {stamp} · Full transcript: <code>{transcript}</code></footer>"


def build_page(out: Path) -> str:
    meta = json.loads(read(out / "meta.json") or "{}")
    sections = split_sections(read(out / "verdict.md"))
    title = title_from(read(out / "brief.md"), meta)
    advisors = [(p.stem.removeprefix("advisor-").title(), read(p), color_var(p.stem)) for p in advisor_files(out)]
    reviews = [(p.stem.replace("-", " ").title(), read(p), "") for p in sorted(out.glob("review-*.md"))]
    mapping = read(out / "mapping.md")
    if mapping:
        reviews.insert(0, ("Anonymization mapping", mapping, ""))
    body = "".join([
        header_html(meta, title),
        verdict_html(sections),
        alignment_html(parse_alignment(find_section(sections, "alignment"))),
        main_items_html(sections),
        box("Where the council agrees", find_section(sections, "agrees")),
        box("Where the council clashes", find_section(sections, "clashes")),
        box("Blind spots caught in peer review", find_section(sections, "blind spot")),
        box("Rejected", find_section(sections, "rejected")),
        box("Act results", read(out / "act.md")),
        details_section("Full advisor responses", advisors),
        details_section("Peer reviews", reviews),
        footer_html(out),
    ])
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Code Council Report</title><style>{CSS_PATH.read_text()}</style></head>"
        f"<body><main>{body}</main></body></html>"
    )


def main() -> None:
    out = Path(sys.argv[1]).resolve()
    (out / "report.html").write_text(build_page(out), encoding="utf-8")
    print(f"REPORT={out / 'report.html'}")


if __name__ == "__main__":
    main()
