"""Count the README's prose words exactly as the README claims to.

Rule (stated in README.md so a reader can repeat it without this tool):
blank lines, fenced code blocks, table rows and the paragraph that states the count are
excluded; every other word counts, including headings and list bullets.

The claim paragraph excludes itself so the number stays true however the note is worded
(otherwise editing the note changes the number it reports, and the check can never pass).

    python tools/word_count.py            # print the count
    python tools/word_count.py --check    # exit 1 if README states a different number

The point of --check is that the stated number cannot drift away from the text without
something failing, which is what happened the first time this was written by hand.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
CLAIM = re.compile(r"Prose word count of this README:\s*\*\*(\d+) words\*\*")


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


def main(argv: list[str]) -> int:
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
