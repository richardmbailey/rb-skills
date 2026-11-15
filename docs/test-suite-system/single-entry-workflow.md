# One invocation owns construction, audit and repair

The user requested that invoking `rb-build-test-suite` handle the whole workflow
without manually alternating between builder and auditor skills. The instructions
now require this for every suite created or extended by the builder, including
non-scientific projects. The host automatically dispatches the separate auditor,
routes findings, repairs authorized tests and test infrastructure, reruns required
checks and obtains review of the exact final candidate.

The earlier rule limited the paired route to scientific suites, explicitly
reliable/audited requests or adopted policy. That restriction is intentionally
superseded. The former `optional-verifier` evaluation expected a small ordinary
suite to omit the auditor under reviewed policy; its expectation now distinguishes
optional additional domain verification from the mandatory test-suite audit.
This change follows the user's new requirement, not an attempt to conceal a
failed evaluation.

The default remains three total assessment rounds. Missing delegation, unresolved
criteria, insufficient authority or exhausted rounds leave acceptance incomplete.
Explicit user limits such as planning-only or no audit take precedence, with a
partial deliverable. Test construction does not silently authorize application
behaviour changes, weaker scientific criteria or deployment. Routine execution of
an existing adopted suite uses its saved command rather than rebuilding it.

Updated surfaces: builder SKILL.md, metadata, README, project and independent
verification references; shared paired-workflow reference; both skill READMEs;
repository overview; routing case; five regression decision probes; instruction
and consistency contracts. No executable coordinator, schema or example changed.

Independent reviewer `/root/single_entry_review` (GPT-6 Astra medium, fresh task
packet) found no blocking conflict. Its five semantic probes covered ordinary
non-scientific construction, a weak assertion after round one, unavailable
delegation, explicit planning/no-audit limits, and an unauthorized application bug.
It also applied the `rb-simplify-language` method to actor, precedence, authority,
failure and termination wording. These are instruction reviews and decision
probes, not executed construction trials or measured skill lift.

Validation: 46 repository regression tests passed; instruction and consistency
contracts, all top-level skill eval manifests, metadata (36 skills, 1,140
aggregate description words within 1,155), publication hygiene and diff whitespace
checks passed. Codex symlinks already exposed the source changes. Both generated
Claude copies were refreshed after an inspected dry-run.

Not rerun: numerical examples, executable coordinator and constrained-runtime
suites, hosted CI, live Claude agent execution or repeated with/without-skill
construction trials. This change is limited to instructions, routing expectations
and documentation; the prior heat example is evidence for the existing loop,
not a fresh behavioural evaluation of this wording revision. No commit or push.
