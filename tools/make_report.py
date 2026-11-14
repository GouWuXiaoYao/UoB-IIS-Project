"""Build the A2 report as a .docx using nothing but the standard library.

The report has to be a Word file, the project forbids third-party runtime
dependencies, and pip does not work in this sandbox, so the writer below emits the
smallest WordprocessingML package that Word and LibreOffice both open: one document
part, one styles part, one footer with a page field, and a table.

Reference style: University of Birmingham Harvard (author-date). In-text citations are
(name, year); the reference list is alphabetical and is excluded from the word count,
as the marking instructions state. Lecture material is cited as (W4 L12, p.5) -- week,
lecture, slide -- because the course decks are supplied as slide PDFs and a slide
number is the only stable locator in them.

    python tools/make_report.py            # write docs/A2_Report_3138100.docx
    python tools/make_report.py --check    # build in memory and print the counts
"""

from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "A2_Report_3138100.docx"

TITLE = "Pre-emptive Governance for AI-Assisted Legacy Refactoring"

# --------------------------------------------------------------------------- content
# ("style", "text") pairs. Styles: title, sub, meta, h1, p, bullet, caption, ref.
BLOCKS: list[tuple[str, object]] = [
    ("title", TITLE),
    ("sub", "An assessment card and a mandatory confirmation gate, evaluated as a scripted prototype"),
    ("meta", "Student 3138100  ·  Intelligent Interactive Systems  ·  Assignment 2"),
    ("meta", "Report format: University of Birmingham Harvard (author-date)"),
    ("counts", ""),
    ("h1", "Abstract"),
    ("p",
     "Legacy refactoring with an AI assistant invites a failure mode the literature already documents: "
     "the code arrives faster than the developer can check it, and reviewers accept opaque suggestions "
     "because the cost of verification falls on them afterwards (Shihab et al., 2025; Roy, Khasgiwala "
     "and Joshi, 2026). This project moves governance upstream. Before any code is generated, the "
     "assistant must state what the change touches, and the developer must confirm each item. The "
     "deliverable is a working prototype of that boundary, built with the standard library only. A "
     "static analyser derives an impact set from the repository and reports 1.00 recall and 1.00 "
     "precision against hand-written labels on six seed repositories spanning three difficulty strata. "
     "An assessment card renders those items as statements rather than identifiers. A gate refuses "
     "generation until every required item is confirmed, and refuses a card that hides one. Sixteen "
     "event types record the session, and every number reported here is recomputed from those logs."),
    ("p",
     "The evaluation is deliberately weaker than the claim it would like to make. No human participants "
     "were recruited: suggestions are replayed from recordings, the operator is a script, and the three "
     "interface frames come from a real session driven by that script. Under a scripted operator the "
     "outcome metrics are identical in both conditions, so nothing here supports a hypothesis about "
     "developer behaviour. What the artefacts do support is narrower: the impact set is measurably "
     "correct, the gate cannot be bypassed through its interface, and the log schema is sufficient to "
     "recompute each metric. The report separates implemented, simulated and planned work throughout."),
    ("h1", "1  Problem and context"),
    ("p",
     "Brownfield refactoring is where AI assistance is least safe and most attractive. A patch arrives "
     "in seconds, yet the developer must still decide whether it respects invariants spread across "
     "modules the model never saw as a whole. Sergeyuk et al. (2026) report developers spending up to "
     "half of their IDE time reviewing and repairing generated code, and Shihab et al. (2025) describe "
     "a prompt-response-implement loop that speeds completion while degrading understanding. Existing "
     "explainability arrives at the wrong moment: it explains a suggestion that already exists, when "
     "the reviewer's attention is cheapest and the framing is fixed (Ye et al., 2025; Gao et al., "
     "2026). The gap is temporal. No mechanism asks the developer to confirm what a change will touch "
     "before the change exists, and none ties that confirmation to a machine-checked impact set."),
    ("h1", "2  Design rationale"),
    ("p",
     "Five decisions carry the design; each names a weeks 1-4 concept and says what it "
     "changed in the code."),
    ("p",
     "Confirmation as a precondition, not a request. Week 4 draws the boundary sharply: the model "
     "proposes and the system disposes, and confirmation is one of five checks an application runs "
     "before it executes (W4 L12, p.5; W4 L12, p.8). That settled where the check lives. The prototype "
     "does not ask the model to be careful; it wraps generation in a gate that raises GateClosed unless "
     "every required item is confirmed, so a prompt cannot trade the check away. The baseline passes "
     "through the same interface with an empty card, so the conditions differ only in the check."),
    ("p",
     "The card carries the arguments. The same lecture's reversibility-by-visibility matrix puts "
     "irreversible but visible actions in the cell that says confirm, with the arguments shown (W4 L12, "
     "p.16), and a later slide insists that a confirmation names the object rather than the category "
     "(W4 L12, p.12). This is why the card is not a yes/no dialogue. It lists five derived items, each "
     "a sentence about a module, a contract or a side effect, and the analyser that produces them is "
     "the part of the system with a measured result: recall 1.00 and precision 1.00 on six tasks."),
    ("p",
     "The blocked state names what is missing. Norman's two gulfs explain why an interface must show "
     "how to act and what happened (W2 L06, p.6); the remedies for slips, mistakes and inference errors "
     "differ, and for the last it is show what was heard (W2 L06, p.10). The blocked alert therefore "
     "repeats the unconfirmed items as the same "
     "sentences the card used, and the repair turn offers the available options instead of asking the "
     "developer to retype them (W3 L07, p.12)."),
    ("p",
     "No checkbox is ever pre-ticked. This one needs care, because the honest account is split. The "
     "decision came from the measurement design: a pre-ticked box makes mechanical confirmation the "
     "only possible behaviour, so the variable under study would be destroyed before the first "
     "session. The lecture support is narrower than that argument: recognition beats recall, so "
     "options should be visible rather than recalled (W2 L05, p.8), which explains why the items are "
     "laid out in full but not why they start empty. The first version rendered them checked and "
     "disabled; a test now fails if that returns."),
    ("p",
     "Logs are the evidence. The prompting lecture keeps intermediate steps in a schema field for "
     "logs, tests and debugging, and keeps a prompt log of version, change and score (W3 L09, p.9; W3 "
     "L09, p.10). That made the event log the only data source: sixteen event types, one JSON line each, "
     "atomic append, no field able to hold free text. Every table is recomputed from those lines, so a "
     "reader can check a number without trusting this text."),
    ("p",
     "Evaluation without participants is declared. The course's own project examples list replay, "
     "scripted conversations, synthetic data and timing as a legitimate way to answer a focused "
     "question, provided implemented, simulated and planned parts are labelled (W2 examples, p.19). "
     "That licenses this scope and carries an obligation: six recordings marked simulated, a scripted "
     "operator, a status column in every table."),
    ("caption", "Table 1. Design choices, the concept each rests on, and the status of the work."),
    ("table", [
        ("Design choice", "Why it suits the problem", "Supporting evidence or reference", "Status"),
        ("Gate, not prompt", "A prompt can be argued away; a precondition cannot",
         "W4 L12 p.5, p.8", "Implemented"),
        ("Card lists impact items", "Confirmation without arguments is a click",
         "W4 L12 p.16, p.12", "Implemented"),
        ("Blocked alert names items", "The developer must see what is missing, not guess",
         "W2 L06 p.6, p.10; W3 L07 p.12", "Implemented"),
        ("Checkboxes start empty", "Pre-ticking removes the behaviour under study",
         "W2 L05 p.8 (partial)", "Implemented"),
        ("JSONL as sole data source", "Every metric must be recomputable by a reader",
         "W3 L09 p.9, p.10", "Implemented"),
        ("Replay instead of live calls", "No key, no network, same bytes on every run",
         "W2 examples p.19", "Simulated"),
        ("Human study, N = 10", "The design is specified and powered; the data is not collected",
         "Own protocol, docs/SPEC.md", "Planned"),
    ]),
    ("h1", "3  Scope, and the boundary between implemented and simulated"),
    ("p",
     "The prototype is eleven modules and 433 tests, all runnable offline with no "
     "third-party dependency. Implemented: corpus factory, analyser, card, gate, telemetry schema, "
     "scorer, orchestrator, web interface, provenance ledger and release snapshot. Simulated: the "
     "model. Six suggestions were recorded once and replayed byte for byte; no external model API was "
     "ever called, and the client is tested against a loopback stub only. Planned: "
     "the human study, its hypotheses and the inferential tests that would accompany them. The logs "
     "hold no free text, only hashes and lengths, and no table links a pseudonym to a person: there "
     "is nothing to re-identify. A "
     "provenance ledger records which artefacts are original, reused or assisted, with the check that "
     "verified each assisted row, so the boundary is auditable rather than asserted."),
    ("h1", "4  Evidence, and what it does not show"),
    ("p",
     "Three results survive. The impact set reaches 1.00 recall and 1.00 precision against "
     "labels written before the analyser existed. A gate refuses a card that hides an item, and generation "
     "below the dwell time. Assignment is deterministic and "
     "balanced: 300 sessions per condition, chi-square p = 1.000. Three results do not "
     "survive. Outcome metrics are identical across conditions because the scripted operator confirms "
     "everything and accepts the first suggestion, so no effect is attributable to governance. The "
     "escape rate of 1.00 is an artefact: each recording omits one consumer. Task "
     "duration is wall-clock time, so it moves with the machine: four runs of the same harness gave "
     "p = 0.058, 0.036, 0.036 and 0.035, and the Holm decision flips. A value that crosses the "
     "threshold with load is not a finding. What remains is an apparatus a reader can "
     "recompute, and a null result reported as null."),
    ("h1", "References"),
    ("ref", "Gao, Z., Muñoz Barón, M., Habiba, U., Graziotin, D. and Wagner, S. (2026) 'Evaluating the impact of explainable AI on trust in AI-assisted code review', Proceedings of the ACM on Software Engineering, 3(ISSTA), Article ISSTA093, pp. 1-23."),
    ("ref", "Roy, R., Khasgiwala, V. and Joshi, V. (2026) 'Generative AI and technical debt in software development: productivity gains versus code quality and security risk', International Journal of Computer Information Systems and Industrial Management Applications, 18(22s), pp. 331-348."),
    ("ref", "Sergeyuk, A., Zakharov, I., Koshchenko, E. and Izadi, M. (2026) 'Human-AI experience in integrated development environments: a systematic literature review', arXiv preprint arXiv:2503.06195."),
    ("ref", "Shihab, M. I., Hundhausen, C., Tariq, A., Haque, S., Qiao, Y. and Mulanda, B. W. (2025) 'The effects of GitHub Copilot on computing students' programming effectiveness, efficiency, and processes in brownfield coding tasks', in Proceedings of the 2025 ACM Conference on International Computing Education Research V.1, pp. 407-420."),
    ("ref", "University of Birmingham (2026) Intelligent Interactive Systems, weeks 1-4: lecture slides. Birmingham: School of Computer Science. Cited as (W4 L12, p.5): week, lecture, slide."),
    ("ref", "Ye, R., Zhang, Z., Almazroua, B. and Liut, M. (2025) 'Beyond autocomplete: designing CopilotLens towards transparent and explainable AI coding agents', arXiv preprint arXiv:2506.20062v3."),
]

# Words in these styles are outside the marking limit: the title block, the note that
# states the count, figure and table captions, and the reference list (the marking
# instructions exclude references explicitly).
UNCOUNTED = {"title", "sub", "meta", "counts", "caption", "ref"}

# Block style -> the styleId actually written into the document part.
STYLE_ID = {
    "title": "Title",
    "sub": "Sub",
    "meta": "Meta",
    "counts": "Counts",
    "h1": "Heading1",
    "p": "Body",
    "caption": "Caption",
    "ref": "Ref",
}


def words(text: str) -> int:
    return len([w for w in text.split() if w.strip()])


def section_counts(blocks=None) -> dict[str, int]:
    """Count words the way the marking instructions do: abstract, then the rest.

    `blocks` defaults to the document's own blocks; tests pass variants to show that
    captions and the reference list are excluded while table cells are included.
    """
    abstract = 0
    body = 0
    in_abstract = False
    for style, payload in (BLOCKS if blocks is None else blocks):
        if style == "h1":
            in_abstract = str(payload).strip().startswith("Abstract")
        if style == "table":
            rows = payload  # type: ignore[assignment]
            for row in rows:
                for cell in row:
                    if in_abstract:
                        abstract += words(cell)
                    else:
                        body += words(cell)
            continue
        if style in UNCOUNTED:
            continue
        text = str(payload)
        if in_abstract:
            abstract += words(text)
        else:
            body += words(text)
    return {"abstract": abstract, "body": body, "total": abstract + body}


# ------------------------------------------------------------------------- packaging
NS = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
)

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
</Relationships>"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles %s>
<w:docDefaults><w:rPrDefault><w:rPr>
<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
<w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault>
</w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Body"><w:name w:val="Body"/>
<w:pPr><w:spacing w:after="180"/><w:jc w:val="left"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Body"/>
<w:pPr><w:spacing w:after="120"/></w:pPr><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:b/><w:sz w:val="40"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Sub"><w:name w:val="Sub"/><w:basedOn w:val="Body"/>
<w:pPr><w:spacing w:after="240"/></w:pPr><w:rPr><w:i/><w:sz w:val="28"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Meta"><w:name w:val="Meta"/><w:basedOn w:val="Body"/>
<w:rPr><w:sz w:val="20"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Counts"><w:name w:val="Counts"/><w:basedOn w:val="Body"/>
<w:pPr><w:spacing w:before="240" w:after="240"/></w:pPr><w:rPr><w:b/><w:sz w:val="22"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Body"/>
<w:pPr><w:keepNext/><w:spacing w:before="360" w:after="120"/><w:outlineLvl w:val="0"/></w:pPr>
<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:b/><w:sz w:val="28"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Caption"><w:name w:val="Caption"/><w:basedOn w:val="Body"/>
<w:pPr><w:spacing w:before="120" w:after="60"/></w:pPr><w:rPr><w:i/><w:sz w:val="20"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Ref"><w:name w:val="Ref"/><w:basedOn w:val="Body"/>
<w:pPr><w:spacing w:after="120"/><w:ind w:left="567" w:hanging="567"/></w:pPr>
<w:rPr><w:sz w:val="22"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="TableText"><w:name w:val="TableText"/><w:basedOn w:val="Body"/>
<w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:rPr><w:sz w:val="19"/></w:rPr></w:style>
</w:styles>""" % NS

FOOTER = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr %s><w:p><w:pPr><w:jc w:val="center"/></w:pPr>
<w:r><w:fldChar w:fldCharType="begin"/></w:r>
<w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>
<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r>
<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>""" % NS

SECTPR = (
    "<w:sectPr><w:footerReference w:type=\"default\" r:id=\"rId2\"/>"
    '<w:pgSz w:w="11906" w:h="16838"/>'
    '<w:pgMar w:top="1418" w:right="1418" w:bottom="1418" w:left="1418" '
    'w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>'
)

BORDER = (
    '<w:tblBorders>'
    + "".join(
        f'<w:{side} w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
        for side in ("top", "left", "bottom", "right", "insideH", "insideV")
    )
    + "</w:tblBorders>"
)


def paragraph(style: str, text: str) -> str:
    keep = ' xml:space="preserve"'
    return (
        f'<w:p><w:pPr><w:pStyle w:val="{STYLE_ID[style]}"/></w:pPr>'
        f"<w:r><w:t{keep}>{escape(text)}</w:t></w:r></w:p>"
    )


def table(rows) -> str:
    out = ['<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/>' + BORDER + "</w:tblPr>"]
    widths = (1700, 1900, 1400, 900)
    out.append("<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in widths) + "</w:tblGrid>")
    for index, row in enumerate(rows):
        header = index == 0
        out.append("<w:tr>")
        for column, cell in enumerate(row):
            shade = '<w:shd w:val="clear" w:fill="EEEEEE"/>' if header else ""
            run = (
                f'<w:r><w:rPr>{"<w:b/>" if header else ""}<w:sz w:val="19"/></w:rPr>'
                f'<w:t xml:space="preserve">{escape(cell)}</w:t></w:r>'
            )
            out.append(
                f'<w:tc><w:tcPr><w:tcW w:w="{widths[column]}" w:type="dxa"/>{shade}'
                f'<w:vAlign w:val="top"/></w:tcPr>'
                f'<w:p><w:pPr><w:pStyle w:val="TableText"/></w:pPr>{run}</w:p></w:tc>'
            )
        out.append("</w:tr>")
    out.append("</w:tbl>")
    # A paragraph after the table keeps Word happy and separates it from the next heading.
    out.append('<w:p><w:pPr><w:pStyle w:val="TableText"/></w:pPr></w:p>')
    return "".join(out)


def document_xml() -> str:
    counts = section_counts()
    body: list[str] = []
    for style, payload in BLOCKS:
        if style == "table":
            body.append(table(payload))  # type: ignore[arg-type]
        elif style == "counts":
            body.append(
                paragraph(
                    "counts",
                    f"Word count: {counts['total']} total (abstract {counts['abstract']}, "
                    f"main report {counts['body']}). The count excludes this line, the title "
                    f"block, table and figure captions, and the reference list.",
                )
            )
        else:
            body.append(paragraph(style, str(payload)))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<w:document {NS}><w:body>" + "".join(body) + SECTPR + "</w:body></w:document>"
    )


def build(path: Path | None = None) -> Path:
    """Write the document. Content is computed before the archive is opened, so a bug in
    the content cannot leave a half-written .docx behind (it did once)."""
    target = path or OUT
    target.parent.mkdir(parents=True, exist_ok=True)
    parts = [
        ("[Content_Types].xml", CONTENT_TYPES),
        ("_rels/.rels", ROOT_RELS),
        ("word/document.xml", document_xml()),
        ("word/_rels/document.xml.rels", DOC_RELS),
        ("word/styles.xml", STYLES),
        ("word/footer1.xml", FOOTER),
    ]
    temporary = target.with_name(target.name + ".part")
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in parts:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    os.replace(temporary, target)
    return target


def main(argv: list[str]) -> int:
    counts = section_counts()
    print(
        f"abstract {counts['abstract']} words, main report {counts['body']} words, "
        f"total {counts['total']} words"
    )
    limit_abstract, limit_body, limit_total = 300, 1100, 1400
    problems = []
    if counts["abstract"] > limit_abstract:
        problems.append(f"abstract {counts['abstract']} > {limit_abstract}")
    if counts["body"] > limit_body:
        problems.append(f"main report {counts['body']} > {limit_body}")
    if counts["total"] > limit_total:
        problems.append(f"total {counts['total']} > {limit_total}")
    if problems:
        for problem in problems:
            print(f"fail: {problem}")
        return 1
    if "--check" in argv:
        print("ok: within the marking limits")
        return 0
    target = build()
    print(f"wrote {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

