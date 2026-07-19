from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from .canonical import sha256_file
from .models import SourcePhase


class PlanningError(ValueError):
    pass


PHASE_HEADING = re.compile(r"^(#{1,6})\s+Phase\s+([0-9]+(?:\.[0-9]+)*)\s*[:\-]?\s*(.*)$", re.IGNORECASE)
FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


@dataclass(frozen=True)
class PhaseSelection:
    source: SourcePhase
    later_phase_ids: list[str]


def select_markdown_phase(plan_path: str, requested_phase_id: str) -> PhaseSelection:
    path = Path(plan_path).resolve(strict=True)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    headings: list[tuple[int, int, str, str]] = []
    fence: tuple[str, int] | None = None
    for index, line in enumerate(lines):
        structural_line = line.rstrip("\r\n")
        if fence is not None:
            marker, minimum = fence
            if re.fullmatch(rf" {{0,3}}{re.escape(marker)}{{{minimum},}}[ \t]*", structural_line):
                fence = None
            continue
        fence_match = FENCE_OPEN.match(structural_line)
        if fence_match:
            token = fence_match.group(1)
            fence = (token[0], len(token))
            continue
        match = PHASE_HEADING.match(structural_line)
        if match:
            level = len(match.group(1))
            phase_id = normalize_phase_id(match.group(2))
            heading = line.strip().lstrip("#").strip()
            headings.append((index, level, phase_id, heading))
    requested = normalize_phase_id(requested_phase_id)
    matches = [item for item in headings if item[2] == requested]
    if len(matches) != 1:
        raise PlanningError(f"phase selection must match exactly once; found {len(matches)} for {requested_phase_id}")
    start, level, phase_id, heading = matches[0]
    end = len(lines)
    for candidate_start, candidate_level, _, _ in headings:
        if candidate_start > start and candidate_level <= level:
            end = candidate_start
            break
    selected = "".join(lines[start:end]).replace("\r\n", "\n").replace("\r", "\n")
    later = [candidate_id for candidate_start, candidate_level, candidate_id, _ in headings if candidate_start > start and candidate_level == level]
    return PhaseSelection(
        source=SourcePhase(
            plan_path=str(path), phase_id=phase_id, heading=heading,
            selected_text_hash=hashlib.sha256(selected.encode("utf-8")).hexdigest(), selected_text=selected,
        ),
        later_phase_ids=later,
    )


def normalize_phase_id(value: str) -> str:
    cleaned = value.strip().lower().replace("_", "-")
    return cleaned if cleaned.startswith("phase-") else f"phase-{cleaned}"


def discover_instruction_files(project_root: str, target_paths: list[str]) -> dict[str, str]:
    root = Path(project_root).resolve(strict=True)
    discovered: dict[str, str] = {}
    root_instruction = root / "AGENTS.md"
    if root_instruction.is_file():
        discovered[str(root_instruction.resolve())] = sha256_file(root_instruction)
    for target_value in target_paths:
        target = Path(target_value).resolve(strict=False)
        try:
            relative = target.relative_to(root)
        except ValueError as exc:
            raise PlanningError(f"target outside project root: {target}") from exc
        current = root
        for component in relative.parts[:-1] if target.suffix else relative.parts:
            current = current / component
            instruction = current / "AGENTS.md"
            if instruction.is_file():
                discovered[str(instruction.resolve())] = sha256_file(instruction)
        if target.is_dir():
            control = root / ".rb-safe-operation"
            for instruction in sorted(target.rglob("AGENTS.md")):
                resolved = instruction.resolve(strict=True)
                try:
                    resolved.relative_to(control)
                    continue
                except ValueError:
                    pass
                discovered[str(resolved)] = sha256_file(instruction)
    return dict(sorted(discovered.items()))


def classify_command(executable_path: str, argv: list[str], declared_child_processes: bool) -> list[str]:
    executable = Path(executable_path).name.lower()
    findings: list[str] = []
    if executable in {"sh", "bash", "zsh", "fish", "cmd", "powershell", "pwsh"}:
        findings.append("shell")
    if executable.startswith("python") and any(item in {"-c", "-m"} for item in argv[1:]):
        findings.append("inline_interpreter" if "-c" in argv[1:] else "dynamic_module")
    if executable in {"node", "ruby", "perl"} and any(item in {"-e", "-p"} for item in argv[1:]):
        findings.append("inline_interpreter")
    if executable in {"npm", "pnpm", "yarn", "make", "just", "task", "cargo"}:
        findings.append("task_runner_or_package_script")
    if any(item in {"--plugin", "--require", "--import"} for item in argv):
        findings.append("plugin_or_dynamic_import")
    if not declared_child_processes and executable in {"git", "pytest", "npm", "pnpm", "yarn", "make", "cargo"}:
        findings.append("undeclared_child_process_potential")
    return findings


COMMAND_CLASSIFICATIONS = frozenset({
    "shell",
    "inline_interpreter",
    "dynamic_module",
    "task_runner_or_package_script",
    "plugin_or_dynamic_import",
    "undeclared_child_process_potential",
})


def validate_continuity(current_phase_id: str, later_phase_ids: list[str], authoritative_phase_ids: list[str]) -> None:
    try:
        index = authoritative_phase_ids.index(current_phase_id)
    except ValueError as exc:
        raise PlanningError("current phase is absent from authoritative plan") from exc
    expected = authoritative_phase_ids[index + 1 :]
    if later_phase_ids != expected:
        raise PlanningError(f"later-phase continuity mismatch: expected {expected}, observed {later_phase_ids}")
