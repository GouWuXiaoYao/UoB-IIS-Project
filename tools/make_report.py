"""Build the A2 report as a .docx using nothing but the standard library.

The report has to be a Word file, the project forbids third-party runtime
dependencies, and pip does not work in this sandbox, so the writer below emits the
smallest WordprocessingML package that Word and LibreOffice both open: one document
part, one styles part, one footer with a page field, a table and five figures.

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

EMU_PER_CM = 360000

# --------------------------------------------------------------------------- content
# ("style", "text") pairs, plus ("figure", (path, width_cm)) and ("table", rows).
# Styles: title, sub, meta, h1, p, caption, ref, figure.
BLOCKS: list[tuple[str, object]] = [
    ("title", TITLE),
    ("sub", "An assessment card and a mandatory confirmation gate, evaluated as a scripted prototype"),
    ("meta", "Student 3138100  ·  Intelligent Interactive Systems  ·  Assignment 2"),
    ("meta", "Report format: University of Birmingham Harvard (author-date)"),
    ("counts", ""),
    ("h1", "Abstract"),
    ("p",
     "Legacy refactoring with an AI assistant invites a failure mode the literature already "
     "documents: the code arrives faster than the developer can check it, and reviewers accept "
     "opaque suggestions because the cost of verification falls on them afterwards (Shihab et "
     "al., 2025; Roy, Khasgiwala and Joshi, 2026). This project moves governance upstream. "
     "Before any code is generated the assistant must state what the change touches, and the "
     "developer must confirm each item. The deliverable is a working prototype of that "
     "boundary, written with the standard library only: a static analyser derives the impact "
     "set from the repository, an assessment card states it as five sentences rather than "
     "identifiers, and a gate refuses generation until every required item is confirmed."),
    ("p",
     "The analyser reaches 1.00 recall and 1.00 precision against labels written before it "
     "existed, on six seed repositories in three difficulty strata. Sixteen event types record "
     "each session, and every number here is recomputed from those logs. The evaluation is "
     "deliberately weaker than the hypothesis it would test: no participants were recruited, "
     "suggestions are replayed from recordings, the operator is a script, and the figures come "
     "from a session that script drove. Under it the outcome metrics are identical in both "
     "conditions, so nothing here supports a claim about developer behaviour. Implemented, "
     "simulated and planned work is separated throughout."),
    ("h1", "1  Problem and context"),
    ("p",
     "Brownfield refactoring is where AI assistance is least safe and most attractive. A patch "
     "arrives in seconds, yet the developer must still decide whether it respects invariants "
     "spread across modules the model never saw as a whole. Sergeyuk et al. (2026) find "
     "developers spending up to half their IDE time reviewing and repairing generated code, and "
     "Shihab et al. (2025) describe a prompt-response-implement loop that speeds completion "
     "while degrading understanding. Explainability arrives too late: it explains a "
     "suggestion that already exists (Ye et al., 2025; Gao et al., 2026). The gap is temporal: "
     "no mechanism asks the developer to confirm what a change will touch before the change "
     "exists, and none ties confirmation to a machine-checked impact set."),
    ("h1", "2  Design rationale"),
    ("p",
     "Five decisions carry the design; each names a Weeks 1–4 concept and its effect in code."),
    ("p",
     "Confirmation as a precondition, not a request. Week 4 draws the boundary sharply: the "
     "model proposes and the system disposes, and confirmation is one of five checks an "
     "application runs before it executes (W4 L12, p.5; W4 L12, p.8). The prototype does not "
     "ask the model to be careful; it wraps generation in a gate that raises GateClosed unless "
     "every required item is confirmed, so a prompt cannot trade the check away."),
    ("p",
     "The card carries the arguments. The same lecture's reversibility-by-visibility matrix puts "
     "irreversible but visible actions in the cell marked confirm, with the arguments shown "
     "(W4 L12, p.16), and a later slide insists a confirmation names the object, not the "
     "category (W4 L12, p.12). The card is not a yes/no dialogue: it lists five derived items, "
     "each a sentence about a module, a contract or a side effect; the analyser behind them "
     "has a measured result."),
    ("p",
     "The blocked state names what is missing. Norman's two gulfs explain why an interface must "
     "show how to act and what happened (W2 L06, p.6), and the remedy for an inference error is "
     "show what was heard (W2 L06, p.10). The alert repeats the unconfirmed items in the card's "
     "own sentences, and the repair turn offers the options rather than asking for them to be "
     "retyped (W3 L07, p.12)."),
    ("p",
     "Nothing is pre-ticked, and the reason is measurement rather than a course concept: a "
     "pre-ticked box makes mechanical confirmation the only behaviour, destroying the "
     "variable before the first session. Recognition over recall (W2 L05, p.8) explains the full "
     "layout, not the empty start; a test now fails if the boxes return checked."),
    ("p",
     "Logs are the evidence. The prompting lecture keeps intermediate steps in a schema field "
     "for logs, tests and debugging (W3 L09, p.9), and a prompt log of version, change and score "
     "(W3 L09, p.10). So the event log is the only data source: sixteen event types, one "
     "JSON line each, atomic append, no free-text field."),
    ("caption", "Table 1. Design choices, the concept each rests on, and the status of the work."),
    ("table", [
        ("Design choice", "Why it fits", "Evidence", "Status"),
        ("Gate, not prompt", "A prompt can be argued away", "W4 L12 p.5, p.8", "Implemented"),
        ("Card lists impact items", "A bare confirmation is a click", "W4 L12 p.16, p.12",
         "Implemented"),
        ("Alert repeats items", "The developer must see what is missing",
         "W2 L06 p.6, p.10; W3 L07 p.12", "Implemented"),
        ("Empty checkboxes", "Pre-ticking removes the behaviour under study", "W2 L05 p.8",
         "Implemented"),
        ("JSONL as sole source", "Every metric is recomputable", "W3 L09 p.9, p.10",
         "Implemented"),
        ("Replay, not live calls", "No key, no network, same bytes", "W2 examples p.19",
         "Simulated"),
        ("Human study, N = 10", "Specified and powered, not run", "docs/SPEC.md", "Planned"),
    ]),
    ("h1", "3  The system, and where the model sits"),
    ("p",
     "The prototype is one package, govern/, behind one command. Figure 1 shows the "
     "components and two flows: control, where a task enters the session orchestrator, the "
     "impact analyser derives the items, the card builds and the gate decides whether generation "
     "may start; and evidence, where every step appends a JSONL event that the experiment and "
     "analysis layers read and nothing else. The model sits behind one boundary, Client, with "
     "two modes; replay is the only mode this study used, so the edge to the external API is "
     "drawn and never traversed."),
    ("figure", ("System diagram/system-diagram.png", 14.6)),
    ("caption", "Figure 1. System diagram: components, flows and status. Solid implemented, "
                "dashed simulated, grey planned; edge 8 is never traversed. Source: drawn by "
                "tools/make_diagram.py from the modules in this repository."),
    ("h1", "4  Three interactions, illustrated"),
    ("p",
     "Each frame is a session served by the local interface and driven by the script; no "
     "person took part."),
    ("p",
     "Example 1: generation waits for confirmation. Two of five items are confirmed, so the "
     "alert names the three outstanding in the card's own sentences and Generate stays "
     "disabled. Confirming the rest clears the alert and enables it. The diff pane is empty "
     "because nothing may be generated yet."),
    ("figure", ("storyboards/1-c1-gate-closed.png", 12.6)),
    ("caption", "Figure 2 (a). Gate closed: 2 of 5 confirmed; the alert names three items; "
                "Generate disabled; the refusal is logged. Source: screenshot of the prototype."),
    ("figure", ("storyboards/2-c1-gate-open.png", 12.6)),
    ("caption", "Figure 2 (b). Gate open: 5 of 5 confirmed; the alert is gone; Generate enabled. "
                "Source: screenshot of the prototype."),
    ("p",
     "Example 2: the baseline. The same task without the card; the suggestion is shown at once "
     "and the panel says generation is not gated. The frame makes the comparison visible."),
    ("figure", ("storyboards/3-c0-baseline.png", 12.6)),
    ("caption", "Figure 3. Baseline (C0): no card, generation not gated, suggestion shown at once. "
                "Source: screenshot of the prototype."),
    ("p",
     "Example 3: rejecting. The developer reads the diff and rejects it; the message says the "
     "working copy is untouched, and five files hash to their previous values, none changed. "
     "Nothing is applied without a decision, and the decision costs nothing: Week 1's principle "
     "that state stays visible and actions stay reversible (W1 L01, p.10)."),
    ("figure", ("storyboards/4-c1-reject.png", 12.6)),
    ("caption", "Figure 4. Rejection: working copy untouched, five files unchanged, two checks "
                "failing, both logged. Source: screenshot of the prototype."),
    ("h1", "5  Scope: implemented, simulated, planned"),
    ("p",
     "Implemented: corpus factory, impact analyser, card, gate, replay client, telemetry, "
     "scorer, orchestrator, web interface, provenance checker, experiment harness and analysis "
     "layer — fifteen modules and 446 tests, standard library only. Simulated: the model, served "
     "from six recordings replayed byte for byte; no external API was called. Planned: the human "
     "study, its hypotheses and the tests that would accompany them — specified and powered, not "
     "run. The course's examples licence evaluation without participants when the parts are "
     "labelled (W2 examples, p.19)."),
    ("p",
     "Evidence, and its limits. Two results survive: the impact set reaches 1.00 recall and "
     "precision against labels written before the analyser existed, and a hundred simulated "
     "allocations give 300 task slots per condition, chi-square p = 1.000. Three do not. Outcome "
     "metrics are identical, because the scripted operator confirms everything and accepts the "
     "first suggestion. The escape rate of 1.00 is an artefact: each recording omits one "
     "consumer. Task duration is wall-clock time: four runs gave p = 0.058, 0.036, 0.036 and "
     "0.035, and Holm's verdict flips."),
    ("h1", "6  Repository and development evidence"),
    ("p",
     "The repository holds the code, corpus, tests and figures; README.md is the entry point, "
     "and docs/PROVENANCE.md is the development record — one row per artefact with its origin "
     "(original, reused or assisted) and the check that verified it, including three drafts "
     "changed after review, among them the pre-ticked checkbox the suite now forbids. Version "
     "1.0.0 is recorded in config/config.json; a release from it carries a SHA256SUMS manifest; "
     "one command runs the checks and both conditions. "
     "【需补充：public GitHub repository URL】"),
    ("h1", "References"),
    ("ref", "Gao, Z., Muñoz Barón, M., Habiba, U., Graziotin, D. and Wagner, S. (2026) 'Evaluating the impact of explainable AI on trust in AI-assisted code review', Proceedings of the ACM on Software Engineering, 3(ISSTA), Article ISSTA093, pp. 1-23."),
    ("ref", "Roy, R., Khasgiwala, V. and Joshi, V. (2026) 'Generative AI and technical debt in software development: productivity gains versus code quality and security risk', International Journal of Computer Information Systems and Industrial Management Applications, 18(22s), pp. 331-348."),
    ("ref", "Sergeyuk, A., Zakharov, I., Koshchenko, E. and Izadi, M. (2026) 'Human-AI experience in integrated development environments: a systematic literature review', arXiv preprint arXiv:2503.06195."),
    ("ref", "Shihab, M. I., Hundhausen, C., Tariq, A., Haque, S., Qiao, Y. and Mulanda, B. W. (2025) 'The effects of GitHub Copilot on computing students' programming effectiveness, efficiency, and processes in brownfield coding tasks', in Proceedings of the 2025 ACM Conference on International Computing Education Research V.1, pp. 407-420."),
    ("ref", "University of Birmingham (2026) Intelligent Interactive Systems, weeks 1-4: lecture slides and project examples. Birmingham: School of Computer Science. Cited as (W4 L12, p.5): week, lecture, slide."),
    ("ref", "Ye, R., Zhang, Z., Almazroua, B. and Liut, M. (2025) 'Beyond autocomplete: designing CopilotLens towards transparent and explainable AI coding agents', arXiv preprint arXiv:2506.20062v3."),
]

# Words in these styles are outside the marking limit: the title block, the note that
# states the count, figure and table captions, and the reference list (the marking
# instructions exclude references explicitly).
UNCOUNTED = {"title", "sub", "meta", "counts", "caption", "ref", "figure", "break"}

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
    "figure": "Figure",
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
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"'
)

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="png" ContentType="image/png"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

HEAD_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
</Relationships>"""

IMAGE_REL = (
    '<Relationship Id="rId{rid}" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
    'Target="media/image{index}.png"/>'
)

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
<w:style w:type="paragraph" w:styleId="Figure"><w:name w:val="Figure"/><w:basedOn w:val="Body"/>
<w:pPr><w:keepNext/><w:spacing w:before="120" w:after="60"/><w:jc w:val="center"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Ref"><w:name w:val="Ref"/><w:basedOn w:val="Body"/>
<w:pPr><w:spacing w:after="30"/><w:ind w:left="454" w:hanging="454"/></w:pPr>
<w:rPr><w:sz w:val="21"/></w:rPr></w:style>
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


def png_size(data: bytes) -> tuple[int, int]:
    """Width and height from the IHDR chunk; a PNG is checked, not trusted."""
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or data[12:16] != b"IHDR":
        raise ValueError("not a PNG image")
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def figure(rel_id: str, name: str, data: bytes, width_cm: float, index: int) -> str:
    """One inline picture, sized by width so the aspect ratio cannot drift."""
    width_px, height_px = png_size(data)
    cx = int(width_cm * EMU_PER_CM)
    cy = int(cx * height_px / width_px)
    label = escape(name)
    return (
        '<w:p><w:pPr><w:pStyle w:val="Figure"/></w:pPr><w:r><w:drawing>'
        '<wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{cx}" cy="{cy}"/>'
        f'<wp:docPr id="{index}" name="{label}"/>'
        '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        '<a:graphic><a:graphicData '
        'uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
        f'<pic:nvPicPr><pic:cNvPr id="{index}" name="{label}"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="{rel_id}"/><a:stretch><a:fillRect/></a:stretch>'
        '</pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
    )


def table(rows) -> str:
    # Fixed layout: the four columns add up to the text width (11906 - 2*1418 = 9070),
    # so nothing spills past the right margin the way proportional widths did.
    widths = (2050, 3000, 2400, 1620)
    out = [
        '<w:tbl><w:tblPr><w:tblW w:w="9070" w:type="dxa"/>'
        '<w:tblLayout w:type="fixed"/>' + BORDER + "</w:tblPr>"
    ]
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


def document_xml() -> tuple[str, list[tuple[str, bytes]]]:
    """The document part plus the media parts it references, in one pass."""
    counts = section_counts()
    body: list[str] = []
    media: list[tuple[str, bytes]] = []
    for style, payload in BLOCKS:
        if style == "figure":
            path, width_cm = payload  # type: ignore[misc]
            data = (ROOT / path).read_bytes()
            index = len(media) + 1
            media.append((f"word/media/image{index}.png", data))
            body.append(figure(f"rId{2 + index}", Path(path).name, data, float(width_cm), index))
        elif style == "break":
            # The reference list starts on its own page, so no entry is orphaned at the foot
            # of the last section page.
            body.append('<w:p><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:br w:type="page"/></w:r></w:p>')
        elif style == "table":
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
        f"<w:document {NS}><w:body>" + "".join(body) + SECTPR + "</w:body></w:document>",
        media,
    )


def document_rels(images: int) -> str:
    extra = "".join(IMAGE_REL.format(rid=3 + index, index=1 + index) for index in range(images))
    return HEAD_RELS.replace("</Relationships>", extra + "</Relationships>")


def build(path: Path | None = None) -> Path:
    """Write the document. Content is computed before the archive is opened, so a bug in
    the content cannot leave a half-written .docx behind (it did once)."""
    target = path or OUT
    target.parent.mkdir(parents=True, exist_ok=True)
    xml, media = document_xml()
    parts: list[tuple[str, object]] = [
        ("[Content_Types].xml", CONTENT_TYPES),
        ("_rels/.rels", ROOT_RELS),
        ("word/document.xml", xml),
        ("word/_rels/document.xml.rels", document_rels(len(media))),
        ("word/styles.xml", STYLES),
        ("word/footer1.xml", FOOTER),
    ]
    temporary = target.with_name(target.name + ".part")
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in parts + media:
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
