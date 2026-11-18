"""Run the matched author trials and blind readers with the authenticated Codex CLI."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import itertools
import json
from pathlib import Path
import random
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parent
REV = "44845c9a2c061420658eefb1c9a0a70cb98f578c"
MODELS = ("gpt-6.2-sol", "gpt-6.2-astra")
DISABLE = """shell_tool unified_exec code_mode_host apps auth_elicitation computer_use
browser_use goals hooks image_generation in_app_browser memories multi_agent multi_agent_v2
personality plugin_sharing plugins remote_plugin request_permissions_tool shell_snapshot
skill_mcp_dependency_install skill_search tool_call_mcp_elicitation tool_suggest
workspace_dependencies""".split()

READER_QUESTIONS = {
    "delivered": "How many rows have been delivered to the destination so far? Return a number or unknown.",
    "repair": "Which file and how many rows do you edit? Return file and number, or unknown.",
    "first_control": "Which control do you use immediately after editing? Give its name or unknown.",
    "restart_count": "How many input rows would New Batch load? Return a number or unknown.",
    "release": "At what status and with which control do you send the rows to their destination? Give both or unknown.",
}


def frozen(skill):
    spec = f"{REV}:{skill}/SKILL.md"
    return subprocess.check_output(["git", "show", spec], cwd=ROOT, text=True)


def schema(fields):
    return {"type": "object", "properties": {k: {"type": "string", "description": v}
            for k, v in fields.items()}, "required": list(fields), "additionalProperties": False}


def invoke(model, prompt, fields):
    with tempfile.TemporaryDirectory(prefix="rb-workflow-") as temp:
        root = Path(temp)
        for name in ("workspace", "state", "logs"):
            (root / name).mkdir()
        path = root / "schema.json"
        path.write_text(json.dumps(schema(fields)))
        output = root / "answer.json"
        argv = ["codex", "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules",
                "--skip-git-repo-check", "--sandbox", "read-only", "--cd", str(root / "workspace"),
                "--enable", "skip_host_skill_discovery", "-c", "project_doc_max_bytes=0",
                "-c", 'web_search="disabled"', "-c", "suppress_unstable_features_warning=true",
                "-c", f'sqlite_home="{root / "state"}"', "-c", f'log_dir="{root / "logs"}"',
                "-c", 'model_reasoning_effort="medium"', "-m", model]
        for flag in DISABLE:
            argv.extend(["--disable", flag])
        argv.extend(["--json", "--output-schema", str(path), "-o", str(output), "-"])
        start = time.monotonic()
        receipt = {"model": model, "effort": "medium"}
        try:
            proc = subprocess.run(argv, input=prompt, cwd=root / "workspace", capture_output=True,
                                  text=True, timeout=110)
            items = []
            notices = []
            completed = False
            for line in proc.stdout.splitlines():
                event = json.loads(line)
                if event["type"] == "turn.completed":
                    receipt["usage"] = event.get("usage")
                    completed = True
                if event["type"] == "item.completed":
                    item = event["item"]
                    if item["type"] == "error":
                        # CLI startup notices share this type with nonfatal transport warnings.
                        message = item.get("message", "")
                        if "Under-development features enabled" in message:
                            notices.append("unstable feature notice")
                        elif "deprecated" in message.lower():
                            notices.append("deprecated feature notice")
                        else:
                            notices.append("other CLI notice")
                    else:
                        items.append(item["type"])
            if notices:
                receipt["notices"] = notices
            unexpected = sorted(set(items) - {"reasoning", "agent_message"})
            if unexpected or proc.returncode or not completed:
                receipt["error"] = {"exit_code": proc.returncode, "unexpected_items": unexpected,
                                    "completed": completed}
            else:
                answer = json.loads(output.read_text())
                if (set(answer) != set(fields)
                        or not all(isinstance(v, str) and len(v) <= 10000 for v in answer.values())):
                    raise ValueError("answer schema")
                receipt["answer"] = answer
        except (subprocess.TimeoutExpired, OSError, ValueError, KeyError) as exc:
            receipt["error"] = type(exc).__name__
        receipt["seconds"] = round(time.monotonic() - start, 3)
        return receipt


def trial(job, cases):
    model, case_id, with_skill, rep = job
    case = cases[case_id]
    body = frozen(case["skill"]) if with_skill else ""
    prompt = "Use no tools. Submit the requested artifact using the supplied output schema.\n"
    if body:
        prompt += "\nApply this workflow within the available text adapter:\n" + body + "\n"
    receipt = {"case": case_id, "condition": "with_skill" if with_skill else "without_skill",
               "rep": rep, "skill_sha256": hashlib.sha256(body.encode()).hexdigest() if body else None}
    receipt["author"] = invoke(model, prompt + "\n" + case["request"], case["format"])
    if case_id == "explanation" and "answer" in receipt["author"]:
        note = receipt["author"]["answer"]["note"]
        prompt = ("Use no tools. You are a first-time shift operator. Answer the supplied questions "
                  "using only the handover note below. Use unknown for anything it does not establish.\n"
                  + json.dumps(note))
        receipt["reader"] = invoke(MODELS[0], prompt, READER_QUESTIONS)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new JSONL file; existing receipts are preserved")
    args = parser.parse_args()
    cases = json.loads((ROOT / "cases.json").read_text())
    jobs = list(itertools.product(MODELS, cases, (False, True), (1, 2, 3)))
    random.Random(61118).shuffle(jobs)
    with args.output.open("x") as out, ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(trial, job, cases) for job in jobs]
        for future in as_completed(futures):
            result = future.result()
            out.write(json.dumps(result, sort_keys=True) + "\n")
            out.flush()
            print(result["case"], result["condition"], result["rep"], result["author"].get("error", "ok"),
                  flush=True)


if __name__ == "__main__":
    main()
