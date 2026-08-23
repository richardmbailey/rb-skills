---
name: "rb-simplify-language"
description: "Manual invocation only. Use only when the human explicitly requests $rb-simplify-language in Codex or /rb-simplify-language in Claude Code. It is intended primarily for agent-facing control text but may be applied to any text the human supplies. Do not select it automatically."
---

# RB Simplify Language

Use this method primarily to make agent-facing control text easier to interpret and audit. When the human explicitly invokes it for other text, reduce semantic ambiguity while preserving that text's purpose, genre, voice, rationale, examples, and useful redundancy.

This is an LLM-specific controlled-language method inspired by simplified technical writing. It does not claim ASD-STE100 compliance and does not apply that standard's vocabulary or sentence-length rules.

## Invocation

Apply this skill only when the human explicitly invokes it by name. Valid invocations include:

- Codex: `$rb-simplify-language`;
- Claude Code: `/rb-simplify-language`;
- an explicit natural-language request to apply the `rb-simplify-language` skill.

Do not select or apply this skill automatically because a task concerns prompts, system instructions, tools, workflows, handoffs, or evaluation criteria. A mention that quotes, documents, reviews, or modifies the skill itself is not an invocation unless the human also asks to apply its method.

## Scope

The intended use is agent-facing control text such as:

- system and developer instructions;
- agent skills and procedures;
- tool descriptions and tool-selection boundaries;
- workflow states, transitions, and gates;
- agent-to-agent handoffs;
- acceptance criteria, rubrics, and evaluation instructions;
- permission, safety, retry, and failure-handling rules.

Because this skill is manual-only, the human may also invoke it for any other supplied text. For text that is not agent-facing, apply the clarity and ambiguity checks that fit the request. Preserve the text's natural form. Do not convert ordinary prose into a control protocol unless the human asks for that format.

If the request is specifically to make supplied prose sound more natural or less AI-generated, use `$rb-revise-ai-draft` as the primary workflow. Use `$rb-write-skill` as the primary workflow when creating or restructuring a complete reusable skill. Use `$rb-multi-agent-systems` as the primary workflow when the unresolved work concerns orchestration architecture. If the human also invokes `$rb-simplify-language`, apply it only to the text within that broader workflow.

## Required inputs

Require the source text or enough requirements to draft it. For agent-facing control text, use these when available:

- the actor or component governed by the text;
- the intended behaviour and prohibited behaviour;
- authoritative names for tools, states, fields, roles, and artifacts;
- observable decision criteria and acceptance conditions;
- precedence rules and relevant higher-level constraints;
- required output format and compatibility constraints.

If a missing criterion would materially change behaviour, do not invent it. Mark the ambiguity and ask for the decision when it blocks a safe or faithful revision.

## Method

1. Identify the supplied text's purpose, audience, and format. For agent-facing control text, separate operative rules from user-facing explanation. For other text, preserve its natural form unless the human requests a controlled format.
2. Build an intent ledger. For each required behaviour, identify the actor, condition, action, object, observable result, failure response, and precedence. Preserve negation, scope, quantities, exceptions, permissions, and side effects.
3. Establish canonical terms. Use one name for each tool, state, role, object, and action. Do not collapse distinct concepts merely because their names are similar.
4. Classify each requirement:
   - deterministic structure or syntax belongs in a schema, parser, enum, table, or exact field definition where practical;
   - semantic judgement needs a bounded natural-language criterion, examples, and an explicit failure or escalation path;
   - explanatory material belongs in rationale or examples, separate from the operative rule.
5. Rewrite the operative rules:
   - give each independently testable instruction its own clause or list item;
   - put the condition before the action: `If <observable condition>, <actor> does <action>.`;
   - name the actor when more than one actor could act;
   - use direct imperatives when the current agent is the only possible actor;
   - use exact canonical names for tools, fields, states, and artifacts;
   - define temporal, quantitative, or qualitative thresholds when they affect a decision;
   - state required behaviour positively and add explicit prohibitions where they protect a real boundary;
   - state what happens when input is missing, validation fails, a tool is unavailable, or an action is denied;
   - express precedence when rules can conflict.
6. Use modal terms consistently. Treat `MUST` and `MUST NOT` as hard requirements, `SHOULD` as a default that needs a stated reason to override, and `MAY` as permission. If the artifact already defines different meanings, preserve its definitions.
7. Separate operative rules from supporting material with labels such as `Rule`, `Rationale`, and `Example` when a reader could otherwise confuse explanation with requirements.
8. Prefer a typed handoff or result schema when components exchange stable fields. Keep prose for meanings that cannot be represented faithfully as syntax alone.
9. Validate the result against the intent ledger and the checklist in `references/simplified-language-patterns.md`.

## Ambiguity rules

Words such as `appropriate`, `reasonable`, `relevant`, `normally`, `sufficient`, `recent`, `if useful`, `as needed`, `try to`, and `consider` are review signals, not banned words.

For each signal:

1. Determine whether the surrounding text already supplies an observable meaning.
2. Replace it with that criterion when doing so preserves intent.
3. Retain it when it has a defined domain meaning.
4. Flag an unresolved decision when no faithful criterion exists.

Do not replace semantic judgement with elaborate regexes, keyword lists, fuzzy scores, or arbitrary numeric thresholds. A deterministic linter may locate review candidates, but a semantic review must decide whether the wording is ambiguous in context.

## Robustness without overconstraint

- Do not impose a fixed sentence-length limit.
- Do not minimise word count at the expense of meaning.
- Keep rationale, examples, and bounded repetition when they reduce a plausible misinterpretation.
- Do not convert every instruction into uppercase normative language.
- Do not force natural user dialogue, teaching prose, or final answers into a control protocol.
- Do not turn a preference into a prohibition or a possibility into a requirement.
- Do not invent thresholds, actors, failure behaviour, permissions, or precedence.

## Output

For a drafting or revision request, return the revised control text first. Then report only material unresolved ambiguities, assumptions, or compatibility effects.

For an audit-only request, report findings in priority order. For each finding, identify:

- the ambiguous or conflicting text;
- the competing interpretations;
- the behavioural consequence;
- a proposed replacement when the source contains enough information;
- the decision needed when it does not.

For a file-editing request, preserve the existing structure where practical and change only the authorised control surface. Do not silently rewrite surrounding explanatory or user-facing prose.

## Completion check

Before completion, confirm that:

- every action has an actor or an unambiguous imperative subject;
- every behaviour-changing condition is stated before or with its action;
- canonical terms are stable;
- hard requirements, preferences, permissions, and prohibitions remain distinct;
- observable criteria replace vague qualifiers where the source supports them;
- missing criteria are visible rather than invented;
- precedence, failure, denial, and terminal behaviour are explicit where relevant;
- rules remain distinct from rationale and examples;
- the revised text preserves the source's behavioural meaning;
- user-facing prose remains natural unless the human requested otherwise.

Direct invocation is `$rb-simplify-language` in Codex and `/rb-simplify-language` in Claude Code.
