"""Run seven current-instruction decision probes. Write a new receipt; never overwrite one."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from run import ROOT, invoke

REPO = ROOT.parent.parent
ROUTE_CONTEXT = ("The approved next phase is to change a pending job's due-time comparison from "
                 "< to <=, add an equality-boundary regression and run the focused job tests. "
                 "The repository has no additional approval requirement.")
HANDOFF_CONTEXT = "Synthetic repository: /example/import. You have only the supplied run and checkout facts."
CASES = [
    ("rb-execute-plan", "execute-respect-recorded-route-hold", ROUTE_CONTEXT),
    ("rb-execute-plan", "execute-default-standard-undecided-route", ROUTE_CONTEXT),
    ("rb-end-session", "end-session-matching-ci-receipt", HANDOFF_CONTEXT),
    ("rb-end-session", "end-session-mismatched-ci-receipt", HANDOFF_CONTEXT),
    ("rb-delegate", "unavailable-required-model",
     "The independent Astra-only subtask is a design assessment. The parent can still prepare the "
     "authorised handoff index from supplied records: inputs.csv contains the import inputs, and "
     "checks.md lists acceptance checks. Give the index as two filename/purpose lines."),
    ("rb-delegate", "history-with-model-override",
     "The parent uses Astra. The host offers gpt-6.2-sol at medium effort. The earlier decisions "
     "are to include a cutoff-equality fixture and preserve insertion order for equal timestamps. "
     "The worker may inspect only tests/fixtures/due.json and may return findings only."),
    ("rb-multi-agent-systems", "responses-continuing-worker-fresh-reviewer",
     "Use a synthetic count correction from 29 to 30. Only the requirement, proposed change and "
     "the test receipt may be given to the reviewer."),
]
WRAPPER = ("This is a text-only simulation. Use no tools. Give the response you would send in "
           "the scenario. Show any requested text deliverable directly. Distinguish proposed host "
           "actions from actions you can actually perform here.\n")
FIELDS = {"response": "response to the scenario"}


def hash_text(text):
    return hashlib.sha256(text.encode()).hexdigest()


def run_case(spec):
    skill, case_id, fixture = spec
    path = REPO / skill / "evals" / "eval-plan.json"
    manifest = json.loads(path.read_text())
    case = next(c for c in manifest["cases"] if c["id"] == case_id)
    paths = [f"{skill}/SKILL.md"]
    if skill == "rb-multi-agent-systems":
        paths.append(f"{skill}/references/openai-responses-continuity.md")
    materials = {p: (REPO / p).read_text() for p in paths}
    prompt = (WRAPPER + "\nWorkflow instructions:\n" + "\n".join(materials.values())
              + "\nSynthetic context:\n" + fixture + "\nRequest:\n" + case["prompt"])
    return {
        "case_id": case_id, "source_manifest": str(path.relative_to(REPO)), "request": case["prompt"],
        "synthetic_context": fixture, "workflow_sha256": {p: hash_text(t) for p, t in materials.items()},
        "prompt_sha256": hash_text(prompt), "success": case["success"],
        "trial": invoke("gpt-6.2-sol", prompt, FIELDS)
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new JSON file")
    args = parser.parse_args()
    with args.output.open("x") as out, ThreadPoolExecutor(max_workers=3) as pool:
        report = {
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "cli": subprocess.check_output(["codex", "--version"], text=True).strip(),
            "transport_sha256": hash_text((ROOT / "run.py").read_text()),
            "wrapper": WRAPPER, "schema_fields": FIELDS, "trials": list(pool.map(run_case, CASES))
        }
        out.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
