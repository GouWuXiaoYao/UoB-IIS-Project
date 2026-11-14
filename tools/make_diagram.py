"""Draw the system diagram for the report, using only the repository's own PNG writer.

Why a generator rather than an image file: the diagram has to stay true to the code.
`NODES` pairs each drawn box with the symbol that implements it, and `--check` fails if
that symbol no longer exists, so the picture cannot quietly outlive the code.

States drawn, in the report's own vocabulary:
  implemented  solid black frame, white fill
  simulated    dashed blue frame  (model output replayed from recordings/)
  planned      grey frame and grey fill (the human study; the paid API call)

Edges run in gutters between columns, never across a box, and carry numbers that the
edge list at the foot of the image resolves to a file and a line. No third-party
dependency: analysis/png.py is the writer the analysis figures already use.

    python tools/make_diagram.py            # write "System diagram/system-diagram.png"
    python tools/make_diagram.py --check    # exit 1 if a drawn stage is no longer in the code
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analysis.png import BLACK, BLUE, GREY, WHITE, Canvas  # noqa: E402

OUT_DIR = ROOT / "System diagram"
OUT = OUT_DIR / "system-diagram.png"

INK = BLACK
SIM = BLUE
PLAN = GREY
PALE = (238, 238, 238)

# Every stage drawn -> (file it lives in, text that must still appear in that file).
NODES = {
    "corpus": ("corpus/index.json", ""),
    "impact": ("govern/impact.py", "def analyze("),
    "card": ("govern/card.py", "def build("),
    "gate": ("govern/gate.py", "def decide("),
    "client": ("govern/llm.py", "def generate("),
    "recordings": ("govern/llm.py", "def _replay("),
    "score": ("govern/score.py", "def evaluate("),
    "hidden": ("govern/hidden.py", "def run("),
    "logger": ("govern/log.py", "class Logger"),
    "session": ("govern/session.py", "def submit_prompt("),
    "web": ("govern/web.py", "class App"),
    "runner": ("experiments/runner.py", "def execute("),
    "analysis": ("analysis/report.py", "def build_outputs("),
}

# Edge: number -> (what flows, where it is realised). Drawn on the image, expanded in
# "System diagram/README.md".
EDGES = {
    1: ("TASK + INTENT INTO THE SESSION", "tasks.py:28 LOAD_INDEX"),
    2: ("PARTICIPANT ACTION INTO SESSION", "web.py:97 APP.PROMPT"),
    3: ("CARD STATE BACK TO THE PAGE", "web.py:56 CARD_VIEW"),
    4: ("PROMPT -> IMPACT SET", "session.py:248 ANALYZE"),
    5: ("IMPACT SET -> CARD", "session.py:250 CARD.BUILD"),
    6: ("OPEN GATE -> GENERATE", "session.py:355 GATECLOSED FIRST"),
    7: ("REQUEST HASH -> RECORDING", "llm.py:238 / :266"),
    8: ("LIVE PATH: NEVER TAKEN", "llm.py:285 URLOPEN"),
    9: ("SUGGESTION -> SCORER", "session.py:432 HIDDEN.RUN"),
    10: ("MODEL REPLY -> GENERATION_REQUEST", "llm.py:246 LOG_REQUEST"),
    11: ("EVERY EVENT -> JSONL APPEND", "session.py:216 LOGGER.EMIT"),
    12: ("EVENTS -> RUN DIRECTORY", "runner.py:63 CELL_LOG_PATH"),
    13: ("CELLS WRITTEN BACK", "runner.py:177 EXECUTE"),
    14: ("RUN DIRECTORY -> FIGURES", "analysis/run.py:43 BUILD"),
    15: ("PLANNED: PARTICIPANTS", "SPEC 5.2 H1-H7, NOT RUN"),
}


class Diagram:
    def __init__(self, width: int = 1300, height: int = 960) -> None:
        self.canvas = Canvas(width, height)

    def node(self, x, y, w, h, kind, heading, lines=()):
        canvas = self.canvas
        colour = {"impl": INK, "sim": SIM, "plan": PLAN}[kind]
        if kind == "plan":
            canvas.fill_rect(x, y, w, h, PALE)
        if kind == "sim":
            for offset in range(0, w, 10):
                canvas.dashed(x + offset, y, x + offset + 5, y, colour, 1)
                canvas.dashed(x + offset, y + h, x + offset + 5, y + h, colour, 1)
            for offset in range(0, h, 10):
                canvas.dashed(x, y + offset, x, y + offset + 5, colour, 1)
                canvas.dashed(x + w, y + offset, x + w, y + offset + 5, colour, 1)
        else:
            canvas.box(x, y, w, h, colour)
        canvas.text(x + 12, y + 10, heading, colour, 2)
        for index, line in enumerate(lines):
            canvas.text(x + 12, y + 32 + index * 14, line, colour, 1)

    def badge(self, x, y, number, colour=INK):
        self.canvas.fill_rect(x - 10, y - 9, 20, 18, WHITE)
        self.canvas.line(x - 10, y - 9, x + 10, y - 9, colour, 1)
        self.canvas.line(x - 10, y + 9, x + 10, y + 9, colour, 1)
        self.canvas.text_center(x, y - 5, str(number), colour, 1)

    def edge(self, points, kind="impl", number=None, label_at=0):
        canvas = self.canvas
        colour = {"impl": INK, "sim": SIM, "plan": PLAN}[kind]
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            if kind == "impl":
                canvas.line(x0, y0, x1, y1, colour, 2)
            else:
                canvas.dashed(x0, y0, x1, y1, colour, 5)
        (px, py), (qx, qy) = points[-2], points[-1]
        if px == qx:
            step = 1 if qy > py else -1
            canvas.line(qx, qy, qx - 7, qy - 10 * step, colour, 2)
            canvas.line(qx, qy, qx + 7, qy - 10 * step, colour, 2)
        else:
            step = 1 if qx > px else -1
            canvas.line(qx, qy, qx - 10 * step, qy - 7, colour, 2)
            canvas.line(qx, qy, qx - 10 * step, qy + 7, colour, 2)
        if number is not None:
            sx, sy = points[label_at]
            ex, ey = points[label_at + 1]
            mx, my = (sx + ex) // 2, (sy + ey) // 2
            self.badge(mx, my, number, colour)

    def draw(self):
        c = self.canvas
        c.text(40, 26, "SYSTEM DIAGRAM: PRE-EMPTIVE GOVERNANCE FOR LEGACY REFACTORING", INK, 2)
        c.text(
            40,
            52,
            "EACH BOX IS A MODULE IN THIS REPOSITORY; EACH NUMBERED EDGE IS RESOLVED AT THE FOOT OF THIS IMAGE",
            GREY,
            1,
        )

        # ---- column A: inputs and the participant's prototype
        c.text(50, 100, "A  INPUTS AND INTERACTION", GREY, 1)
        self.node(50, 118, 330, 74, "impl", "CORPUS  6 TASKS",
                  ("3 PAIRS X 2 STRATA: L M H", "REPO + INTENT + HIDDEN TESTS", "GOLD PATCH + IMPACT LABELS"))
        self.node(50, 220, 330, 70, "impl", "WEB UI  STATIC INDEX.HTML",
                  ("ONE CHECKBOX PER CARD ITEM", "CONFIRM, GENERATE, ACCEPT, END"))
        self.node(50, 318, 330, 86, "impl", "SESSION ORCHESTRATOR",
                  ("OWNS CONDITION C0 OR C1 AND PHASE", "EMITS EVERY EVENT TO THE LOG", "STATE REBUILT FROM THE LOG"))
        self.node(50, 432, 330, 64, "impl", "IMPACT.ANALYZE",
                  ("PURE AST, NO MODEL CALLED", "RECALL 1.00, PRECISION 1.00"))
        self.node(50, 524, 330, 84, "impl", "CARD.BUILD + GATE.DECIDE",
                  ("ITEMS AS STATEMENTS, NEVER IDS", "C0: EMPTY CARD, PASSTHROUGH", "C1: BLOCKED UNTIL ALL CONFIRMED"))

        # ---- column B: the model boundary
        c.text(470, 100, "B  MODEL BOUNDARY", GREY, 1)
        c.text(
            470,
            114,
            "AI ADVISES, THE SYSTEM DISPOSES: THIS STUDY REPLAYS A RECORDING, IT NEVER CALLS A MODEL",
            GREY,
            1,
        )
        self.node(470, 220, 330, 70, "sim", "RECORDINGS  6 FILES",
                  ("WRITTEN BY A SCRIPT, NOT A MODEL", "EACH OMITS ONE CONSUMER"))
        self.node(470, 318, 330, 90, "impl", "CLIENT.GENERATE",
                  ("MODE=REPLAY: SIMULATED RECORDING", "IMPLEMENTED CODE, FIXED REQUEST HASH", "SIX TASKS X 10 REPLAYS IDENTICAL", "MODEL PROPOSES, SYSTEM DISPOSES"))
        self.node(470, 442, 330, 70, "plan", "EXTERNAL MODEL API  MODE=LIVE",
                  ("NEVER CALLED IN THIS STUDY", "TESTED ONLY AGAINST A STUB"))
        self.node(470, 524, 330, 84, "impl", "SCORE.EVALUATE + HIDDEN.RUN",
                  ("SIX JSON RULES, GOLD 6/6", "HIDDEN SUITE IN A CHILD PROCESS", "DEBT AND VULN DELTAS"))

        # ---- column C: evidence and offline analysis
        c.text(890, 100, "C  EVIDENCE AND OFFLINE ANALYSIS", GREY, 1)
        self.node(890, 220, 360, 92, "impl", "LOG  RUNS ID LOGS *.JSONL",
                  ("16 EVENT TYPES, ONE LINE EACH", "HASH + LENGTH, NEVER RAW TEXT", "ATOMIC APPEND, SEQ FROM 1"))
        self.node(890, 336, 360, 74, "impl", "RUNS  RUN ID",
                  ("CONFIG SNAPSHOT + MANIFEST", "METRICS.JSON, WORK/"))
        self.node(890, 434, 360, 74, "impl", "EXPERIMENTS/RUNNER",
                  ("CONDITION FILE, BOUNDED POOL", "RESUME AFTER THE LAST SESSION_END"))
        self.node(890, 532, 360, 74, "impl", "ANALYSIS/REPORT",
                  ("READS LOGS ONLY, NEVER MEMORY", "XLSX + 4 FIGURES + CAPTIONS"))
        self.node(890, 630, 360, 66, "plan", "HUMAN STUDY  N=10",
                  ("HYPOTHESES AND TESTS SPECIFIED", "NO PARTICIPANT RECRUITED"))

        # ---- edges, all in gutters
        self.edge([(50, 155), (28, 155), (28, 361), (50, 361)], "impl", 1, 1)
        self.edge([(215, 290), (215, 318)], "impl", 2, 0)
        self.edge([(265, 318), (265, 290)], "impl", 3, 0)
        self.edge([(215, 404), (215, 432)], "impl", 4, 0)
        self.edge([(215, 496), (215, 524)], "impl", 5, 0)
        self.edge([(380, 566), (440, 566), (440, 363), (470, 363)], "impl", 6, 1)
        self.edge([(635, 290), (635, 318)], "sim", 7, 0)
        self.edge([(635, 408), (635, 442)], "plan", 8, 0)
        self.edge([(800, 380), (820, 380), (820, 566), (800, 566)], "impl", 9, 1)
        self.edge([(800, 350), (855, 350), (855, 300), (890, 300)], "sim", 10, 1)
        self.edge([(380, 340), (415, 340), (415, 140), (860, 140), (860, 250), (890, 250)], "impl", 11, 0)
        self.edge([(1070, 312), (1070, 336)], "impl", 12, 0)
        self.edge([(1070, 434), (1070, 410)], "impl", 13, 0)
        self.edge([(1250, 373), (1270, 373), (1270, 569), (1250, 569)], "impl", 14, 1)
        self.edge([(890, 663), (872, 663), (872, 470), (890, 470)], "plan", 15, 1)

        self.legend()
        self.edge_list()

    def legend(self):
        c = self.canvas
        c.text(40, 726, "LEGEND", GREY, 1)
        self.node(40, 742, 250, 52, "impl", "IMPLEMENTED", ("CODE IN THIS TREE, TESTED",))
        self.node(310, 742, 250, 52, "sim", "SIMULATED", ("DATA FROM A SCRIPT, NOT A MODEL",))
        self.node(580, 742, 250, 52, "plan", "PLANNED", ("NOT RUN, NO DATA",))
        c.line(860, 752, 900, 752, INK, 2)
        c.text(908, 747, "IMPLEMENTED FLOW", INK, 1)
        c.dashed(860, 770, 900, 770, SIM, 5)
        c.text(908, 765, "SIMULATED FLOW (FILE READ)", SIM, 1)
        c.dashed(860, 788, 900, 788, PLAN, 5)
        c.text(908, 783, "PLANNED FLOW (NOT EXERCISED)", PLAN, 1)
        c.text(
            40,
            812,
            "NO EDGE REACHES THE EXTERNAL API. THE SIX RECORDINGS CARRY SOURCE=SIM AND A SCRIPT DRIVES THE PAGE,",
            INK,
            1,
        )
        c.text(40, 828, "SO NOTHING IN THIS FIGURE IS A MEASUREMENT OF A PERSON OR OF A LIVE MODEL.", INK, 1)

    def edge_list(self):
        c = self.canvas
        c.text(40, 858, "EDGE  WHAT FLOWS                              WHERE IT IS REALISED", GREY, 1)
        c.text(680, 858, "EDGE  WHAT FLOWS                              WHERE IT IS REALISED", GREY, 1)
        for index, number in enumerate(sorted(EDGES)):
            column, row = divmod(index, 8)
            x = 40 + column * 640
            y = 876 + row * 14
            what, where = EDGES[number]
            c.text(x, y, f"{number:>2}", INK, 1)
            c.text(x + 26, y, what, INK, 1)
            c.text(x + 360, y, where, GREY, 1)


def build(path: Path | None = None) -> Path:
    target = path or OUT
    target.parent.mkdir(parents=True, exist_ok=True)
    diagram = Diagram()
    diagram.draw()
    return diagram.canvas.save(target)


def check() -> int:
    problems = []
    for name, (source, symbol) in sorted(NODES.items()):
        path = ROOT / source
        if not path.exists():
            problems.append(f"{name}: {source} is missing")
        elif symbol and symbol not in path.read_text(encoding="utf-8"):
            problems.append(f"{name}: {symbol!r} not found in {source}")
    if not OUT.exists():
        problems.append("System diagram/system-diagram.png has not been generated")
    for line in problems:
        print(f"fail: {line}")
    if problems:
        return 1
    print(f"ok: {len(NODES)} stages match the source, {OUT.relative_to(ROOT)} exists")
    return 0


def main(argv: list[str]) -> int:
    if "--check" in argv:
        return check()
    target = build()
    print(f"wrote {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
