---
name: "rb-create-safe-operation-policy"
description: "Use when a user wants to create, explain, tighten, or explicitly relax the fixed .rb-safe-operation-policy.json file from natural-language path restrictions."
---

# RB Create Safe Operation Policy

Turn the user's ordinary-language restrictions into a typed proposal, show the exact prospective effect, and write the fixed repository policy only after confirmation bound to that proposal. The user never has to author JSON. This skill does not plan or execute implementation work.

## Boundaries

- The only authoritative file is `<project-root>/.rb-safe-operation-policy.json`. Do not search parent directories or accept another action-bearing location.
- The policy can only narrow the installed global safe-operation authority. It cannot grant a tool, adapter, path, effect, command, network destination, provider, or resource.
- First-release path rules use only an exact path or directory subtree and independently deny `read`, `create`, `modify`, or `delete`. Translate user-facing `write` to all three mutation capabilities and state that expansion in the preview.
- A denied read is prospective. It cannot remove content from the current conversation, provider logs, Git history, copies, backups, caches, or process memory.
- The Codex CLI translator is `instruction_only_authoring`. It runs with unnecessary Codex capabilities disabled and its event stream must contain no tool calls, but do not call it framework-isolated or proof of operating-system isolation. Use `framework_tool_enforced_authoring` only through the separately selected manifest-pinned PydanticAI compatibility translator that allocates no tools.
- Never read a target's contents in order to write a denial rule. Pass only the bounded request, current typed policy facts, and sanitised named-path metadata to the translator.

## Procedure

1. Resolve the authoritative project root and invoke the manifest-pinned runtime as specified in [policy-authoring-contract.md](references/policy-authoring-contract.md). Use `policy-explain` to load the fixed file or canonical absence identity before inspecting other project content.
2. Restate the proposed interpretation using exact project-relative POSIX paths. Resolve material ambiguity with the human before creating a proposal. Examples requiring clarification include whether “touch” includes reads, whether a directory rule is recursive, or which of two similarly named paths is meant.
3. Produce one strict `ProjectPolicyProposal` schema 1.0. Preserve every existing policy field and stable rule ID whose authorization meaning is unchanged. Reasons are explanatory text only and cannot grant authority.
4. Save the transient proposal outside the repository or under protected `.rb-safe-operation/` control state. Do not put a proposal, prompt, or reasoning trace in the product tree.
5. Run `policy-preview` against the fixed project root. The deterministic runtime validates canonical paths, rule limits, alias uncertainty, monotonic global-policy merge, source compare-and-swap identity, and whether the effective change is create, tightening, reason-only, relaxation, or mixed.
6. Show the complete plain-language preview, source/effective policy identities, every added/retained/removed rule ID, the write expansion, any observability loss, the assurance profile, and the prospective-only disclosure. Do not persist yet.
7. Ask the human to confirm that exact preview. Show the exact statement emitted for it: `CONFIRM SAFE OPERATION POLICY <token>` for creation, tightening, or reason-only changes, and `CONFIRM SAFE OPERATION POLICY RELAXATION <token>` for relaxation or mixed changes. Ask the human to provide that complete unchanged statement. A relaxation or mixed change needs a separately explicit confirmation that restrictions are being removed or narrowed. Do not infer confirmation from the original request.
8. Use `policy-confirm` to bind the human's exact statement to the proposal hash, preview hash, source compare-and-swap identity, and confirmation token. Human identity remains instruction-only evidence.
9. Run `policy-apply`. The coordinator reacquires the shared project mutation lease, rechecks the fixed source identity, writes a durable intent, atomically replaces only the policy file, fsyncs and rereads it, and writes the committed authoring record. A stale preview, existing lease, alias, uncertain replacement, or record failure stops without pretending success.
10. Run `policy-explain` again and compare its source and effective identities with the committed authoring record. Report the exact rule effect and that every earlier plan, assessment, approval, or resumable run must be recompiled and reassessed under the new policy identity.

## Stops

- Unresolved semantic ambiguity: ask one bounded clarification and do not write.
- Invalid or widening proposal: report the typed diagnostic and leave the existing bytes unchanged.
- Stale confirmation or concurrent change: regenerate the proposal and preview; never overwrite.
- Live or indeterminate execution lease: stop for human inspection; do not remove it.
- Failure after the policy replacement intent or atomic replacement: report `indeterminate` and require human inspection. Do not retry automatically.
- A request to edit implementation files, run a plan, or assess plan safety belongs to the appropriate planning, execution, or assessment skill after policy authoring finishes.

## Records

Retain the typed proposal, preview, confirmation, intent, committed authoring record, old/new source identities, old/new effective identities, rule-ID change set, classification, assurance label, and timestamps. Do not persist raw model reasoning, credentials, denied content, or private provider responses.
