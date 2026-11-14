"""Count words the way the marking instructions do, for the README and for the report.

Two modes, one rule each, both stated in the file being counted so a reader can repeat
them without this tool.

README mode (default): blank lines, fenced code blocks, table rows and the paragraph
that states the count are excluded; every other word counts, including headings and
list bullets.

Report mode (`--docx=PATH`): the .docx is read directly (zip + XML, no dependency) and
paragraphs are classified by their style. Counted: headings, body paragraphs and every
table cell, because the marking instructions say table text counts. Not counted: the
title block, the line that states the count, table and figure captions, and the
reference list. Abstract and main report are reported separately, because the limits
differ (300 and 1,100 words, 1,400 together).

    python tools/word_count.py            # print the README count
    python tools/word_count.py --check    # exit 1 if README states a different number
    python tools/word_count.py --docx=docs/A2_Report_3138100.docx --check
"""

from __future__ import annotations

import html
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
CLAIM = re.compile(r"Prose word count of this README:\s*\*\*(\d+) words\*\*")

# Report styles whose words are outside the marking limit.
REPORT_UNCOUNTED = {"title", "sub", "meta", "counts", "caption", "ref"}
STATED = re.compile(
    r"Word count:\s*(\d+)\s*total\s*\(abstract\s*(\d+),\s*main report\s*(\d+)\)"
)


def prose_words(text: str) -> int:
    """Words outside code blocks, table rows, blank lines and the claim paragraph."""
    kept: list[str] = []
    fenced = False
    in_claim = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced or line.startswith("|"):
            continue
        if CLAIM.search(line):
            in_claim = True
            continue
        if in_claim:
            if not line.strip():
                in_claim = False
            continue
        kept.append(line)
    return len([w for w in re.split(r"\s+", " ".join(kept)) if w.strip()])


def stated(text: str) -> int | None:
    match = CLAIM.search(text)
    return int(match.group(1)) if match else None


def docx_paragraphs(path: Path) -> list[tuple[str, str]]:
    """(style, text) for every paragraph in the document part, tables included."""
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    paragraphs: list[tuple[str, str]] = []
    for block in re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S):
        style = re.search(r'<w:pStyle w:val="([^"]+)"', block)
        text = "".join(
            html.unescape(run)
            for run in re.findall(r"<w:t[^>]*>(.*?)</w:t>", block, flags=re.S)
        )
        paragraphs.append((style.group(1) if style else "Body", text))
    return paragraphs


def report_counts(path: Path) -> dict[str, int]:
    abstract = body = 0
    in_abstract = False
    for style, text in docx_paragraphs(path):
        low = style.lower()
        if low == "heading1":
            in_abstract = text.strip().lower().startswith("abstract")
        if low in REPORT_UNCOUNTED:
            continue
        count = len([w for w in text.split() if w.strip()])
        if in_abstract:
            abstract += count
        else:
            body += count
    return {"abstract": abstract, "body": body, "total": abstract + body}


def report_main(path: Path, check: bool) -> int:
    counts = report_counts(path)
    print(
        f"{path.name}: abstract {counts['abstract']}, main report {counts['body']}, "
        f"total {counts['total']} words"
    )
    limits = (("abstract", 300), ("body", 1100), ("total", 1400))
    over = [(name, counts[name], limit) for name, limit in limits if counts[name] > limit]
    for name, value, limit in over:
        print(f"fail: {name} {value} words exceeds {limit}")
    if not check:
        return 1 if over else 0
    match = STATED.search(" ".join(text for _, text in docx_paragraphs(path)))
    if not match:
        print("fail: the report does not state its word count on the first page")
        return 1
    stated_total, stated_abstract, stated_body = (int(group) for group in match.groups())
    print(
        f"stated: abstract {stated_abstract}, main report {stated_body}, "
        f"total {stated_total}"
    )
    drift = [
        f"{name}: stated {shown}, text has {counts[name]}"
        for name, shown in (
            ("abstract", stated_abstract),
            ("body", stated_body),
            ("total", stated_total),
        )
        if shown != counts[name]
    ]
    if drift or over:
        for line in drift:
            print(f"fail: {line}")
        return 1
    print("ok: the stated counts match the text and are within the limits")
    return 0


def main(argv: list[str]) -> int:
    for argument in argv:
        if argument.startswith("--docx="):
            return report_main(Path(argument.split("=", 1)[1]), "--check" in argv)
        if argument.startswith("--docx") and len(argument) > len("--docx"):
            print(f"unknown argument: {argument}")
            return 2
    path = README
    for argument in argv:
        if argument.startswith("--path="):
            path = Path(argument.split("=", 1)[1])
        elif argument not in ("--check",):
            print(f"unknown argument: {argument}")
            return 2
    text = path.read_text(encoding="utf-8")
    count = prose_words(text)
    if "--check" not in argv:
        print(f"{count} prose words in {path.name}")
        return 0
    claim = stated(text)
    if claim is None:
        print(f"fail: {path.name} does not state a prose word count")
        return 1
    if claim != count:
        print(f"fail: {path.name} states {claim} words, the text has {count}")
        return 1
    print(f"ok: {path.name} states {count} prose words and has {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
