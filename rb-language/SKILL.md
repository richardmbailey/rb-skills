---
name: "rb-language"
description: "Use for ordinary drafting or light editing of user-facing prose when no specific skill owns the task. Prefer direct language. For substantive revision of supplied AI-like prose, use $rb-revise-ai-draft."
---

# RB Language

Draft or lightly edit ordinary user-facing prose. This is a task skill, not a global formatting layer.

## Selection boundary

Use this skill for ordinary writing such as emails, announcements, short updates, social posts, website copy, and light edits when no more specific skill owns the task.

Light editing changes local wording, tone, clarity, or length without requiring a claim-by-claim audit. Substantive revision applies when the human identifies supplied prose as AI-generated, formulaic, or generic, or when the task requires detailed preservation of claims, evidence, quotations, citations, or uncertainty across a broader rewrite.

Do not select this skill as the primary workflow when:

- the human supplies AI-generated, formulaic, or generic prose for substantive revision; use `$rb-revise-ai-draft`;
- the human explicitly invokes `$rb-simplify-language` for agent instructions or other control text;
- the task creates or updates project vocabulary or `CONTEXT.md`; use `$rb-project-language`;
- the request is proofreading only, literal translation, fact-checking, citation verification, or code-only work;
- another skill's description matches the requested artifact, analysis, or workflow more specifically.

If the human explicitly invokes `$rb-language`, follow that invocation unless it conflicts with a higher-priority instruction or would displace a required specialist workflow. Explain the conflict instead of silently changing the task.

## Required input

Use the facts, notes, draft, or instructions the human supplies. Use the intended audience, purpose, medium, and tone when they are available. If missing context would materially change the result, ask for it. Otherwise make the most conservative suitable choice.

## Method

1. Identify the requested deliverable and its audience.
2. Begin with the requested substance. Remove canned praise, throat-clearing, chatbot commentary, and offers to continue.
3. Prefer concrete subjects, direct verbs, plain words, and specific supported facts. Remove filler, unsupported promotional language, vague authority, and empty emphasis.
4. Preserve meaning, attribution, claim strength, uncertainty, quotations, citations, and genuine personal claims. Do not invent facts, opinions, feelings, experiences, evidence, or stylistic quirks.
5. Preserve code, commands, schemas, field names, identifiers, defined terminology, and other exact content unless the human asks to change it.
6. Follow the needs of the medium. Keep useful headings, lists, emphasis, punctuation, sentence lengths, and repetition. Do not treat a word or formatting choice as proof of AI authorship.
7. Check that the final prose is direct, natural for its context, and free of unsupported hype or canned AI phrasing. Do not claim that the result is human-authored or guaranteed to evade an AI detector.

## Output

Return the requested prose in the requested format. Do not add editorial notes unless the human asks for them or a source conflict, missing fact, or unresolved placeholder needs explanation.

Direct invocation is `$rb-language` in Codex and `/rb-language` in Claude Code.
