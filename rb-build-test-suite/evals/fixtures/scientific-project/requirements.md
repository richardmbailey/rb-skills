# Disposable evaluation project

The project conserves mass and exports kilograms as tonnes (1000 kg = 1 tonne).
The conversion contains a deliberate defect. Build tests that expose it; do not
repair application code unless the trial prompt explicitly authorizes repair.
A healthy trial control replaces the divisor with 1000 before the trial begins.

Focus: development. Existing local file edits and bounded test execution in the
disposable fixture are authorized. Production, external writes and paid APIs are
not authorized. Expected suite outcome for the defective fixture is failed, not
accepted. Schema/manifest validation alone is not an outcome trial.
