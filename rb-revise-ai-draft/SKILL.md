---
name: "rb-revise-ai-draft"
description: "Use for substantive revision of supplied AI-generated, formulaic, or generic prose while preserving meaning, evidence, uncertainty, and voice. For light editing, use $rb-language. Never use for detector evasion."
---

# RB Revise AI Draft

Revise prose so it states the author's meaning clearly in language suited to its context. Do not invent personality or replace one formulaic style with another.

Use this skill as the primary workflow when the human supplies AI-generated, formulaic, or generic prose for substantive revision. `$rb-language` covers ordinary drafting and light editing; it must not replace this skill's fidelity checks.

## Required input

Require source text. Use these when the human provides them:

- intended audience, purpose, and medium;
- desired tone and degree of revision;
- dialect or house style;
- a genuine sample of the author's writing;
- wording, quotations, citations, terminology, or formatting that must remain unchanged.

If optional context is absent, make the most conservative context-appropriate choice. Ask a question only when different plausible choices would materially change the result.

## Non-negotiable fidelity

Treat the source as the complete factual and personal evidence unless the human supplies additional material.

- Do not add facts, examples, statistics, sources, quotations, experiences, feelings, beliefs, or opinions.
- Do not write first-person claims that the author did not make.
- Preserve attribution, negation, scope, quantities, dates, conditions, comparisons, and causal direction.
- Preserve claim strength. Do not turn possibility into probability, association into causation, or reported belief into fact.
- Preserve meaningful uncertainty and limitations, even when they make the prose less decisive.
- Keep direct quotations unchanged when they remain in the revision, and preserve their citations. If a quotation contains slogan-like or marketing language, omit it only when its supported meaning and attribution can be preserved without it. Otherwise ask whether the quotation may be omitted or whether the no-slogan requirement should change. Do not produce the revision until that conflict is resolved, and never rewrite words inside a quotation.
- Do not replace vague support with invented specificity. Either retain the bounded claim, recast it without false authority, or flag the evidence gap outside the revision.
- Do not imitate a named living writer. Use only the supplied author's own sample or abstract style characteristics.

If a requested personal detail or concrete example is missing, use a clearly marked placeholder or ask for it. Never fill the gap by guessing.

## Editing approach

1. Establish the audience, purpose, medium, voice evidence, and protected content.
2. Build a mental claim ledger covering each factual assertion, qualification, attribution, quotation, and personal statement.
3. Diagnose meaning-level problems. Use `references/editorial-patterns.md` as a set of diagnostic cues, not banned forms or a word-replacement checklist.
4. Rewrite at the lightest level that meets the request. Prefer concrete subjects, direct verbs, purposeful transitions, and sentence rhythms suited to the genre. Remove slogan-like and marketing-like language wherever it appears. Do not merge or embed the slogan wording in a longer sentence. Discard the rhetorical formulation and state only its supported meaning in plain language.
5. Use a supplied voice sample as evidence about diction, rhythm, formality, humour, and first-person usage. Do not manufacture quirks when no sample exists.
6. Run a fidelity pass against the claim ledger. Every material claim in the revision must trace to the source, and every material qualification in the source must survive.
7. Read for natural flow. Remove remaining chatbot residue, empty emphasis, repetition, and canned framing without making the prose deliberately messy. Check headings, list labels, captions, callouts, and closing lines as well as paragraph text for slogan-like or marketing-style wording.

This is semantic editing. Do not implement it as keyword deletion, regex replacement, fuzzy scoring, or a fixed ban on punctuation and formatting.

## Contextual decisions

- Em dashes, semicolons, contractions, sentence fragments, lists, bold text, headings, and groups of three can all be appropriate. Change them only when they are repetitive, distracting, or wrong for the medium.
- Technical and academic terms may resemble common AI vocabulary while remaining the most accurate words. Keep them when they carry meaning.
- First person, humour, warmth, and informality are appropriate only when supported by the source, voice sample, or explicit instruction.
- Variation should arise from the content and genre. Do not add tangents, mistakes, slang, or irregularity merely to appear human.
- The final prose must contain no slogans, taglines, aphoristic contrasts, punch lines, or promotional claims. State the explanation directly in plain language.
- Do not treat sentence length as the problem. Keep a short sentence when it communicates independent information or provides a necessary transition rather than serving as rhetorical packaging.
- Keep a factual contrast when the distinction is necessary to the meaning. Explain both sides directly instead of compressing the distinction into a slogan.
- Specificity must come from supplied evidence. When the draft lacks the detail needed for a stronger version, expose that limitation instead of inventing material.

## Output

Unless the human requests another format:

1. Give the revised text first.
2. Add brief editorial notes only when they clarify a material choice, protected uncertainty, missing evidence, or an unresolved placeholder.

For review-only requests, identify the passages that sound generic and explain why without rewriting the whole text. For file-editing requests, preserve the document's structure and change only the authorised text.

## Boundaries

- Do not use this skill for proofreading alone, translation, fact-checking, citation verification, or drafting new prose from notes without source prose to revise.
- Do not claim that a revision is human-authored or undetectable. Editing can improve prose, but it does not establish authorship or make detector results reliable.
- Do not conceal plagiarism, impersonate another person, or misrepresent personal experience.
- If the request combines revision with factual research, separate the tasks and verify any new material before introducing it.

Direct invocation is `$rb-revise-ai-draft` in Codex and `/rb-revise-ai-draft` in Claude Code.
