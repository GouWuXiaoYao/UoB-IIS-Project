# Course concept evidence check (W1–W4, first-hand material edition)

Purpose: to give the report's §Design rationale **verifiable** grounding in course concepts. This file only checks evidence; it changes no code and writes no report.

## 0. What material was used, and how page numbers are counted

The first-hand material is in `modules/`: `W1/`–`W4/` each hold that week's lecture PDF and the weekly summary docx; there is also `modules/IIS_W1-4_概念与知识点汇总.docx` (the cross-week master volume) and `modules/.work/txt/*.txt` (page-by-page text extracted from the lecture PDFs, with page boundaries marked `===== PAGE n =====`).

**Page-number convention**: `p.n` below means **page n of the lecture PDF**, that is, the n-th slide (title page included). Each check locates the text page by page in `modules/.work/txt/` and then re-reads the PDF page order, so it is reproducible.

**First-hand lectures confirmed as citable**: W1 L01/L02/L03, W2 L04/L05/L06, W3 L07/L08/L09, W4 L10/L11/L12, W2 `examples_projects.pdf` (the example-project booklet).
**The two that supply no methodology text**: `W2/exp.pdf` is, on inspection, a "First Hand (Meta Quest 3) viewing guide" (26 pages: a video segment timeline plus an L1–L6 concept mapping) and contains **no evaluation methodology**; for §05 of `IIS_W1-4_概念与知识点汇总.docx` ("three kinds of validity / metric menu / four-sentence evaluation paragraph") no corresponding page can be found in this batch of PDFs (see §4).

**Evidence strength**: **strong** = the page names the concept explicitly and gives the mechanism or remedy, and the implementation is that mechanism; **medium** = the concept is named, but attaching it to a specific decision needs one explanatory step; **weak** = only the topic is similar; **mismatch** = same name, different meaning.

---

## 1. Usable first-hand correspondences (ordered by strength)

| Design decision | Verifiable course concept | Location in the course material | How the concept shaped the decision | Evidence strength |
|---|---|---|---|---|
| C1: no code is generated without item-by-item confirmation (`Session.generate()` raises `GateClosed`) | "**The model proposes; your system disposes**" + the **confirmation** of the five pre-execution checks | W4 L12 **p.5** (proposal ≠ execution), **p.8** (the five checks explained one by one) | Confirmation is made an **application-side pre-check**, not a polite request inside the prompt: the model only produces a proposal, and the generation step is released by the system according to the check result | **strong** |
| The card shows "which modules/contracts this run will touch" (a 5-item impact set) rather than a yes/no | The reversibility × visibility matrix: "**Irreversible but visible: confirm, with the arguments shown**" | W4 L12 **p.16** (two questions: can it be undone, will a person notice; four-cell disposition); p.15 is the in-class exercise on the same judgement | This fixes the card's **content**: a confirmation must carry judgeable parameters, or "confirm" degrades into a click | **strong** |
| The confirmation surface names the concrete object ("billing.state.remember→PRICE_CACHE is written during request handling"), not "this change" | "**Name the object: 'Project review', six attendees, not 'the meeting'**" | W4 L12 **p.12** ("What the person sees before it runs") | Directly determined that `labelFor()` maps `item_id` to a **named object**; this is the hardest first-hand ground for "write declarative sentences" | **strong** |
| The interception prompt uses declarative sentences to state what the system understood | L06's three kinds of error need **different remedies**: "**show what was heard, confirm risky actions, and expose the system's model**" | W2 L06 **p.10** (slip / mistake / system inference error each given a remedy); p.9 defines the three | The interception copy restates "what the system heard", because the error lies in the **goal the system inferred**, not in the user's action | **strong** |
| `Generate` is disabled until every box is ticked, and states which items are still missing | **signifier** (a perceptible hint for action) and the **two gulfs** (execution / evaluation); the remedy for a slip = constraint/confirmation/undo | W2 L06 **p.4** (affordance vs signifier), **p.5** (suggestion chips are a strong signifier), **p.6** (the two gulfs), **p.10** (slip remedies) | Decided to stop the error before execution with "constraint + signifier" (disabled + a list of missing items), rather than reporting an error after submission | **strong** |
| On interception, lay out the available actions instead of asking the user to rephrase | The **clarify** turn among L07's four repair turns: "**present the options the system has, and do not ask for clearer input**" | W3 L07 **p.12** ("Four repair turns should be specified before any other dialogue is written") | The missing-item hint lists "these three are still missing" rather than "please supply more information" | **strong** |
| No human participants: replay + scripted sessions + synthetic data + timing (Q1) | The third of the example projects' four common points, "**Evaluation without participants**: replays, scripted conversations, synthetic data and timing answer a focused question" | W2 `examples_projects` **p.19** (the four common points); p.20 asks "What could you measure alone, without participants?"; p.6/p.12/p.15/p.16 are the four examples' own replay evaluations | The course grounding for Q1: the course itself lists "evaluation without participants" as acceptable practice, so the report explains the trade-off accordingly instead of apologising for it | **strong** |
| The three states (implemented / simulated / planned) must be labelled separately | The same page's fourth point, "**Honest scope**: implemented, simulated and planned parts are labelled" | W2 `examples_projects` **p.19** | Runs in the same direction as the marking red line; determined that README, report and storyboard all state the three-way split | **strong** |
| The log is the only data source; metrics may only be recomputed from JSONL | "**Keep the steps in a schema field for logs, tests and debugging**"; "**prompt log recording version, change made and score**" | W3 L09 **p.9** (why the log rather than the interface: printed reasoning persuades whether or not it is correct), **p.10** (change one thing at a time, recording version/change/score) | Supports the hard rule "every run writes JSONL"; also grounds the manifest (model/temperature/seed/app_version) | **strong** |
| The five checkboxes are **never pre-ticked** | "**Recognition beats recall**": recognition is identifying options that are **already visible**, recall is producing them without a cue | W2 L05 **p.8** (Norman 2013's "knowledge in the world/head"); p.9 (suggestion chips and shown sources move the cue into the world) | Supports the half "lay the candidates out for recognition"; **does not support** "avoid mechanical confirmation" (see §2) | **medium** |
| The empty-state copy when C0 has no card | "**Make the system's limits visible so people can revise their mental model**" (G1–G6 make the capability boundary and the situation visible) | W1 L03 **p.12** (expectation gulf), p.7 (G1–G6 reveal the capability envelope) | Makes "no card for this condition" a readable state rather than something that looks broken | **medium** |
| Treating "reversible" and "visible" as design dimensions (background motivation) | *the second shift makes system state visible and actions reversible, both deliberate design choices* (paraphrase: the source note states this only in Chinese, so it is not quoted) | W1 L01 **p.10** | Explains why the card must be both "undoable" and "visible", giving the L12 matrix its historical lineage | **medium** (historical narrative, not a specification) |

---

## 2. Verdicts on the four candidates in `docs/compliance-check.md` §2.1 (after checking the first-hand material)

| Original §2.1 candidate | Verdict | First-hand ground |
|---|---|---|
| Never pre-ticked ↔ **default effect / mechanical confirmation (confirmation fatigue)**; recognition better than recall | **the first half is still not supported; the second half has a first-hand anchor** | No "default effect" or "confirmation fatigue" appears in any W1–W4 lecture PDF. That claim comes from Shihab et al. (2025), cited in A1, and is a **literature** ground. "Recognition better than recall" can cite W2 L05 **p.8**, but that only explains "why the options are laid out", not "why they are not pre-ticked" — the problem with pre-ticking is that it **makes the judgement for the person**, and this batch of material does not discuss that directly |
| Listing declarative text on interception ↔ system state visibility, error messages in the user's language | **raised to strong (anchor replaced)** | W4 L12 **p.12** (naming the object) + W2 L06 **p.10** (show what was heard). The original candidate's "error messages in the user's language" has no corresponding page; Grice `manner` (W3 L07) is a **conversational maxim**, not a principle of error copy |
| Disable + state the reason ↔ preventing errors beats correcting them; the execution gulf | **raised to strong (wording replaced)** | W2 L06 **p.6** (the two gulfs), p.10 (slip remedies), **p.4/p.5** (signifier), W3 L07 **p.12** (clarify). "Preventing errors beats correcting them" is not the lecture's wording; it should be written as "**stop errors before execution with signifiers and constraints**" |
| Empty-state copy ↔ state visibility | **medium** | W1 L03 **p.12**, where the lecture makes the system's limits visible so that people can revise their mental model (paraphrase of a Chinese note) — citable, but it only supports "state must be visible", not specifically "the empty state must have copy" |

**Conclusion**: of the four candidates, 2 and 3 can be raised to **strong** on the first-hand material (but with the anchor or the wording replaced), the first half of 1 must be withdrawn (re-labelled as a literature ground), and 4 stays medium.

---

## 3. Two mis-mappings that must be avoided

| Do not write it this way | Why | Correct statement |
|---|---|---|
| Calling `docs/PROVENANCE.md` (the development provenance ledger: original / reused / assisted) L11's **Provenance** | L11 **p.10**'s four requirements are "**Resolvable / Specific and honest about coverage / Dated / Reportable**" — they are about whether **an answer's citation can be opened at the paragraph**. The ledger is about **where the work came from**. Same name, different meaning | If it is to hang under L11, what hangs there is "answer verifiability"; the ledger itself hangs under W1's accountability and W4's audit log (the L12 page on least privilege / complete mediation) |
| Writing "confirmation fatigue / mechanical confirmation" as a course concept | The term is on no page of W1–W4 | Write it as "**A1 literature ground (Shihab et al., 2025)**", listed separately from course concepts |

---

## 4. What is still missing (this does not affect the 9 strong pieces of evidence above)

1. **§05's "three kinds of validity / metric menu / four-sentence evaluation paragraph"**: there is no corresponding page in this batch of PDFs. `W2/exp.pdf` is a viewing guide (video segment timeline + an L1–L6 mapping), not evaluation methodology. To use these two, a lecture page on evaluation methodology is needed (or the report should instead cite W3 L09 p.9–p.10's "log/version/change/score", which is first-hand).
2. **All G1–G18 entries**: W1 L03 p.7–p.8 already groups them as G1–G6 / G7–G11 / G12–G18 and can be cited directly; for item-by-item wording the original L03 lecture is needed (the current PDF is the original lecture, p.7–p.8 is legible, which suffices).
3. **The item-by-item wording of the L12 five checks**: W4 L12 p.8 already gives them item by item (shape / permission / precondition / confirmation / idempotency), which suffices.
