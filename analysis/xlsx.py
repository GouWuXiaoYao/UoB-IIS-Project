"""A minimal .xlsx writer: a zip of SpreadsheetML parts.

openpyxl is not available (and would be a third-party runtime dependency anyway),
but a workbook only has to be a handful of XML documents in a zip. Enough of the
format is implemented here to open cleanly in Excel, LibreOffice and pandas:

* several worksheets, each a list of rows;
* inline strings (no shared-string table to keep in sync);
* numbers as real numbers, so a reader can re-compute from them;
* three cell formats: plain, bold (header row) and 3-decimal.

The writer is deterministic: the same cells produce byte-identical output, which
``tests/test_analysis.py`` checks.
"""

from __future__ import annotations

import datetime as _dt
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, Sequence

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
{sheets}
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""

_ROOT_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

_STYLES = """<?xml version="1.0" encoding="UTF-8"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="1"><numFmt numFmtId="164" formatCode="0.000"/></numFmts>
<fonts count="2">
<font><sz val="11"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><name val="Calibri"/></font>
</fonts>
<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="3">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""

_SHEET = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetData>
{rows}
</sheetData>
</worksheet>"""

_BAD = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}


def _esc(text: str) -> str:
    return "".join(_BAD.get(ch, ch) for ch in text)


def _column(index: int) -> str:
    """1 -> A, 26 -> Z, 27 -> AA."""
    out = ""
    while index:
        index, rem = divmod(index - 1, 26)
        out = chr(ord("A") + rem) + out
    return out


def _cell(ref: str, value: Any, style: int) -> str:
    attr = f' s="{style}"' if style else ""
    if value is None:
        return f'<c r="{ref}"{attr}/>'
    if isinstance(value, bool):
        return f'<c r="{ref}"{attr} t="b"><v>{int(value)}</v></c>'
    if isinstance(value, (int, float)):
        if value != value or value in (float("inf"), float("-inf")):
            return f'<c r="{ref}"{attr} t="inlineStr"><is><t>n/a</t></is></c>'
        return f'<c r="{ref}"{attr}><v>{value!r}</v></c>'
    if isinstance(value, (_dt.date, _dt.datetime)):
        value = value.isoformat()
    return f'<c r="{ref}"{attr} t="inlineStr"><is><t>{_esc(str(value))}</t></is></c>'


def sheet_xml(rows: Iterable[Sequence[Any]]) -> str:
    """One worksheet's XML. The first row is rendered bold."""
    out = []
    for r, row in enumerate(rows, start=1):
        cells = "".join(
            _cell(f"{_column(c)}{r}", value, 1 if r == 1 else (2 if isinstance(value, float) else 0))
            for c, value in enumerate(row, start=1)
        )
        out.append(f'<row r="{r}">{cells}</row>')
    return _SHEET.format(rows="\n".join(out))


def write(path: str | Path, sheets: dict[str, Iterable[Sequence[Any]]]) -> Path:
    """Write ``{sheet name: rows}`` to a workbook at ``path``."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    names = list(sheets)
    if not names:
        raise ValueError("a workbook needs at least one sheet")

    overrides = "\n".join(
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, len(names) + 1)
    )
    workbook = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"',
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        "<sheets>",
    ]
    for i, name in enumerate(names, start=1):
        workbook.append(f'<sheet name="{_esc(name)}" sheetId="{i}" r:id="rId{i}"/>')
    workbook.append("</sheets></workbook>")
    rels = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
    ]
    for i in range(1, len(names) + 1):
        rels.append(
            f'<Relationship Id="rId{i}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{i}.xml"/>'
        )
    rels.append(
        f'<Relationship Id="rId{len(names) + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    rels.append("</Relationships>")

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        def add(name: str, text: str) -> None:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, text)

        add("[Content_Types].xml", _CONTENT_TYPES.format(sheets=overrides))
        add("_rels/.rels", _ROOT_RELS)
        add("xl/workbook.xml", "\n".join(workbook))
        add("xl/_rels/workbook.xml.rels", "\n".join(rels))
        add("xl/styles.xml", _STYLES)
        for i, name in enumerate(names, start=1):
            add(f"xl/worksheets/sheet{i}.xml", sheet_xml(sheets[name]))
    target.write_bytes(buf.getvalue())
    return target


def read_sheets(path: str | Path) -> dict[str, list[list[str]]]:
    """Read back a workbook written by this module (used by the tests).

    Only the subset this module writes is understood, which makes it a fair
    round-trip check rather than a general reader.
    """
    from xml.etree import ElementTree as ET

    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    out: dict[str, list[list[str]]] = {}
    with zipfile.ZipFile(Path(path)) as zf:
        book = ET.fromstring(zf.read("xl/workbook.xml"))
        names = [s.get("name") for s in book.findall("m:sheets/m:sheet", ns)]
        for i, name in enumerate(names, start=1):
            root = ET.fromstring(zf.read(f"xl/worksheets/sheet{i}.xml"))
            rows: list[list[str]] = []
            for row in root.findall("m:sheetData/m:row", ns):
                cells = []
                for c in row.findall("m:c", ns):
                    if c.get("t") == "inlineStr":
                        node = c.find("m:is/m:t", ns)
                        cells.append(node.text if node is not None and node.text else "")
                    else:
                        v = c.find("m:v", ns)
                        cells.append(v.text if v is not None and v.text else "")
                rows.append(cells)
            out[str(name)] = rows
    return out
