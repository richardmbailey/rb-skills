# Legacy `_rb-agent-skills` Compatibility

Read this reference only when no current flat `rb-skills` source repository is
available and discovery finds a legacy `_rb-agent-skills` pack.

The compatibility path remains supported because
`rb-install-skills/scripts/install_skills.py` still detects the legacy layout.
Do not prefer it over the current flat repository.

From the legacy pack root, verify the pack and installed visibility with:

```bash
python3 scripts/verify_pack.py
python3 scripts/audit_skill_visibility.py
```

In a legacy pack, reusable skills live under `skills/` and project resources
are managed by the root helper scripts. Report that the legacy path was used,
which checks passed, and whether migration to the flat `rb-skills` repository
should be scheduled. Do not silently restructure or migrate the pack during a
repair task.
