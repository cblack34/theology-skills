---
name: scripture-exegesis
description: "Arbitrate a biblical passage from the Greek or Hebrew text in the argument of the book. Use when the user asks for exegesis, a reading of a verse, an NT quotation of the OT, or a check of a claim against the original languages. Not for sermon drafting, devotionals, or coding tasks."
---

# Scripture exegesis

Establish the wording, then the argument of the book. Commentaries are secondary. Label anything the text does not say.

## Pipeline

1. Establish the text. New Testament: SBLGNT. Old Testament: Westminster Leningrad Codex. See `references/editions.md` for repos and when to open them.
2. Read the verse inside the book's argument. Do not treat a sentence as independent of the paragraph or the letter.
3. If the NT cites or alludes to the OT, compare the Masoretic text and Rahlfs LXX. Say which the NT follows, and what the difference does to the sense.
4. Open pseudepigrapha only for a claimed echo. Name the edition. Do not treat a parallel as a source.
5. Consult scholarship after the text. Cite author, title, and locus. Do not let a commentary override the wording.
6. Mark historical reconstruction, unstated authorial intent, and cultural gap-filling as inference. Use "the text does not say this" when it does not.

## Output rules

- Default English is NASB 1995. If NIV or NET carries the syntax more clearly, say so and why.
- If an English rendering differs from the Greek or Hebrew in a way that changes the claim, note the divergence and follow the original.
- Show a Greek or Hebrew form, morphology, or case function only when it resolves a claim. Define the function in that clause.
- Do not affirm a user or a source when the wording, syntax, or book argument contradicts them. State the discrepancy.
- Do not isolate a proof-text from the argument the author is making.

## Not in this skill

Working commentaries, study-specific file paths, and a particular book's outline belong in that study's notes, not here.
