# Deferred executable prototype

The user selected skill instructions and references first. This development
package preserves work prepared before that clarification. It is not installed,
release-qualified, or the implementation used by the active instruction edition.

P0/P1 were independently reviewed. P2 filesystem/bootstrap work and an early
report slice have tests but still need independent integration review and the
remaining runner, adapters, host, browser and release gates. The last pre-move
combined run passed 59 tests; no actual finished suite runner exists.

See [the plan](../../docs/rb-build-test-suite-specification/IMPLEMENTATION_PLAN.md)
and its implementation-evidence directory. Paths in earlier receipts identify
the location at the time of those checks. Source was moved here without changing
runtime logic; test fixture lookup was adjusted for the new location.

Run development checks with the pinned dependencies installed:

```bash
PYTHONPATH=development/rb-build-test-suite/src python -m unittest discover \
  -s development/rb-build-test-suite/tests -v
```
