#!/usr/bin/env python3
"""Create a new LLM-wiki from wiki-template and reconfigure its subject shell."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


TEXT_SUFFIXES = {".md", ".py", ".yml", ".yaml"}
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SAFE_TAG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "wiki"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def replace_all(root: Path, replacements: dict[str, str]) -> None:
    raw_dir = root / "sources" / "raw"
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        if is_under(path, raw_dir):
            continue
        text = read_text(path)
        updated = text
        for old, new in replacements.items():
            updated = updated.replace(old, new)
        if updated != text:
            write_text(path, updated)


def replace_line(path: Path, prefix: str, new_line: str) -> None:
    lines = read_text(path).splitlines()
    changed = False
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = new_line
            changed = True
            break
    if changed:
        write_text(path, "\n".join(lines).rstrip() + "\n")


def reset_reports(root: Path) -> None:
    reports_dir = root / "reports"
    for subdir_name in ["ingest", "lint", "review"]:
        subdir = reports_dir / subdir_name
        subdir.mkdir(parents=True, exist_ok=True)
        for child in subdir.iterdir():
            if child.name == ".gitkeep":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        (subdir / ".gitkeep").touch()


def run_tool(root: Path, *command: str) -> None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, *command],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    output = (completed.stdout + completed.stderr).strip()
    if output:
        print(output)
    if completed.returncode != 0:
        raise RuntimeError(f"{' '.join(command)} failed with exit code {completed.returncode}")


def write_setup_note(root: Path, args: argparse.Namespace) -> None:
    setup_path = root / "SETUP.md"
    setup_path.write_text(
        "\n".join(
            [
                f"# {args.title} Setup",
                "",
                f"- Subject: {args.subject}",
                f"- Domain tag: `{args.tag}`",
                f"- Created from template: `{args.template}`",
                f"- Base directory: `{root}`",
                "",
                "# Next Steps",
                "",
                "1. Drop initial source files into `inbox/`.",
                "2. Use `$rb-wiki-ingest` to process the inbox.",
                "3. Use `$rb-wiki-maintenance` to run quick maintenance after edits.",
                "4. Set up conservative automations when the wiki is ready for scheduled upkeep.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def configure_wiki(root: Path, args: argparse.Namespace) -> None:
    subject_tag = args.tag
    overview_title = f"{args.title} Overview"
    overview_description = f"A high-level map of {args.title} and its source-backed operating model."

    replace_all(
        root,
        {
            "wiki-template": subject_tag,
            "Wiki Template Overview": overview_title,
            "Wiki Template": args.title,
            "this wiki template": args.title,
            "This wiki template": args.title,
            "the wiki template": args.title,
            "The template": args.title,
            "subject-specific": args.subject,
        },
    )

    readme = root / "README.md"
    if readme.exists():
        replace_line(readme, "# ", f"# {args.title}")
        text = read_text(readme)
        text = re.sub(
            r"This directory is .*?\n",
            lambda _match: f"{args.description}\n",
            text,
            count=1,
        )
        write_text(readme, text)

    agents = root / "AGENTS.md"
    if agents.exists():
        text = read_text(agents)
        text = re.sub(
            r"The goal is to compile raw sources into durable, cited, cross-linked knowledge about .*\.",
            lambda _match: (
                "The goal is to compile raw sources into durable, cited, cross-linked "
                f"knowledge about {args.subject}."
            ),
            text,
            count=1,
        )
        write_text(agents, text)

    overview = root / "wiki" / "overview.md"
    if overview.exists():
        replace_line(overview, "title: ", f"title: {yaml_quote(overview_title)}")
        replace_line(overview, "description: ", f"description: {yaml_quote(overview_description)}")
        text = read_text(overview)
        text = re.sub(
            r"\n.*? is an initial source-backed knowledge system.*?\n",
            lambda _match: f"\n{args.description}\n",
            text,
            count=1,
        )
        write_text(overview, text)

    log = root / "wiki" / "log.md"
    if log.exists():
        text = read_text(log)
        text = re.sub(
            r"Initialized .* skeleton\.",
            lambda _match: f"Initialized the {args.title} skeleton from wiki-template.",
            text,
            count=1,
        )
        write_text(log, text)

    template_note = root / "TEMPLATE.md"
    if template_note.exists():
        template_note.unlink()
    write_setup_note(root, args)


def copy_template(template: Path, destination: Path) -> None:
    if not template.is_dir():
        raise RuntimeError(f"template does not exist: {template}")
    if destination.exists():
        raise RuntimeError(f"destination already exists: {destination}")
    shutil.copytree(
        template,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "processed"),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a new LLM-wiki from wiki-template")
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--parent", required=True, type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--tag")
    parser.add_argument("--description")
    args = parser.parse_args(argv)
    args.template = args.template.expanduser().resolve()
    args.parent = args.parent.expanduser().resolve()
    args.tag = args.tag or slugify(args.subject)
    args.description = args.description or f"{args.title} is a local-first LLM-wiki for {args.subject}."
    if Path(args.name).name != args.name:
        parser.error("--name must be a single directory name, not a path")
    if not SAFE_NAME_RE.match(args.name):
        parser.error("--name may contain only letters, numbers, dots, underscores, and hyphens")
    if not SAFE_TAG_RE.match(args.tag):
        parser.error("--tag must be lowercase kebab-case, using only letters, numbers, and hyphens")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    destination = args.parent / args.name
    try:
        copy_template(args.template, destination)
        reset_reports(destination)
        configure_wiki(destination, args)
        run_tool(destination, "tools/build_index.py")
        run_tool(destination, "tools/build_graph.py")
        run_tool(destination, "tools/source_registry.py", "validate")
        run_tool(destination, "tools/lint.py", "--quick")
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print(f"PASS: created {destination}")
    print(f"Title: {args.title}")
    print(f"Subject: {args.subject}")
    print(f"Tag: {args.tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
