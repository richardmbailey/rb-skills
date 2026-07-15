#!/usr/bin/env python3
"""Validate the deterministic structure of an rb-explain-diff HTML artifact."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_SECTION_IDS = ("background", "intuition", "code", "quiz")
REQUIRED_BACKGROUND_IDS = ("background-beginner", "background-change")
RESOURCE_ATTRIBUTES = {
    "audio": ("src",),
    "embed": ("src",),
    "iframe": ("src",),
    "img": ("src",),
    "object": ("data",),
    "script": ("src",),
    "source": ("src", "srcset"),
    "use": ("href", "xlink:href"),
    "video": ("src", "poster"),
}


class ExplanationHTMLParser(HTMLParser):
    """Collect just enough document structure for useful validation."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: dict[str, str] = {}
        self.duplicate_ids: set[str] = set()
        self.nav_hrefs: set[str] = set()
        self.nav_depth = 0
        self.toc_count = 0
        self.style_depth = 0
        self.script_depth = 0
        self.styles: list[str] = []
        self.scripts: list[str] = []
        self.pre_count = 0
        self.diagram_count = 0
        self.callout_count = 0
        self.viewport_count = 0
        self.tab_count = 0
        self.external_resources: list[str] = []
        self.questions: list[dict[str, object]] = []
        self.question_stack: list[int] = []
        self.element_stack: list[tuple[str, int | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        classes = set(attributes.get("class", "").split())
        question_index: int | None = None

        element_id = attributes.get("id")
        if element_id:
            if element_id in self.ids:
                self.duplicate_ids.add(element_id)
            self.ids[element_id] = tag

        if tag == "nav" and "toc" in classes:
            self.nav_depth += 1
            self.toc_count += 1
        if self.nav_depth and tag == "a":
            href = attributes.get("href", "")
            if href.startswith("#"):
                self.nav_hrefs.add(href[1:])

        if tag == "style":
            self.style_depth += 1
        if tag == "script" and not attributes.get("src"):
            self.script_depth += 1

        if tag == "meta" and attributes.get("name", "").lower() == "viewport":
            self.viewport_count += 1
        if tag == "pre":
            self.pre_count += 1
        if "diagram" in classes:
            self.diagram_count += 1
        if "callout" in classes:
            self.callout_count += 1
        if attributes.get("role", "").lower() in {"tab", "tablist", "tabpanel"}:
            self.tab_count += 1

        if "quiz-question" in classes:
            question_index = len(self.questions)
            self.questions.append(
                {
                    "options": [],
                    "feedback": False,
                    "feedback_live": False,
                    "non_button": False,
                }
            )
            self.question_stack.append(question_index)

        if "quiz-option" in classes:
            if self.question_stack:
                options = self.questions[self.question_stack[-1]]["options"]
                assert isinstance(options, list)
                options.append(attributes.get("data-correct"))
                if tag != "button":
                    self.questions[self.question_stack[-1]]["non_button"] = True
        if "quiz-feedback" in classes and self.question_stack:
            self.questions[self.question_stack[-1]]["feedback"] = True
            if attributes.get("aria-live", "").lower() in {"polite", "assertive"}:
                self.questions[self.question_stack[-1]]["feedback_live"] = True

        self._check_external_resource(tag, attributes)
        self.element_stack.append((tag, question_index))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == "style" and self.style_depth:
            self.style_depth -= 1
        if tag == "script" and self.script_depth:
            self.script_depth -= 1
        if tag == "nav" and self.nav_depth:
            self.nav_depth -= 1

        for index in range(len(self.element_stack) - 1, -1, -1):
            open_tag, question_index = self.element_stack[index]
            if open_tag != tag:
                continue
            del self.element_stack[index:]
            if question_index is not None and self.question_stack:
                if self.question_stack[-1] == question_index:
                    self.question_stack.pop()
            break

    def handle_data(self, data: str) -> None:
        if self.style_depth:
            self.styles.append(data)
        if self.script_depth:
            self.scripts.append(data)

    def _check_external_resource(self, tag: str, attrs: dict[str, str]) -> None:
        resource_link_types = {"icon", "manifest", "modulepreload", "preload", "stylesheet"}
        if tag == "link" and resource_link_types.intersection(
            attrs.get("rel", "").lower().split()
        ):
            value = attrs.get("href", "")
            if value and not value.startswith("data:"):
                self.external_resources.append(f"link[href={value!r}]")

        for attribute in RESOURCE_ATTRIBUTES.get(tag, ()):
            value = attrs.get(attribute, "").strip()
            if not value:
                continue
            if value.startswith(("data:", "#")):
                continue
            parsed = urlparse(value)
            if parsed.scheme or parsed.netloc or not value.startswith("data:"):
                self.external_resources.append(f"{tag}[{attribute}={value!r}]")


def css_preserves_preformatted_whitespace(css: str) -> bool:
    """Return True when a CSS rule targeting pre preserves its whitespace."""
    for selectors, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", css, re.DOTALL):
        if not re.search(r"(?:^|[\s>+~,.#:\[])pre(?:$|[\s>+~,.#:\[])" , selectors):
            continue
        if re.search(r"white-space\s*:\s*(?:pre|pre-wrap)\b", declarations, re.IGNORECASE):
            return True
    return False


def external_css_urls(css: str) -> list[str]:
    """Return CSS url() values that are not embedded data or fragment references."""
    external: list[str] = []
    for match in re.finditer(r"url\(\s*(['\"]?)(.*?)\1\s*\)", css, re.IGNORECASE):
        value = match.group(2).strip()
        if value and not value.startswith(("data:", "#")):
            external.append(value)
    return external


def validate(
    path: Path, *, require_today: bool = True
) -> tuple[list[str], list[str], ExplanationHTMLParser]:
    errors: list[str] = []
    notes: list[str] = []

    if path.parent.name != "explanations":
        errors.append("The HTML file must be inside an explanations directory.")

    filename_match = re.fullmatch(
        r"(\d{4}-\d{2}-\d{2})-explanation-[a-z0-9][a-z0-9-]*\.html",
        path.name,
    )
    if not filename_match:
        errors.append(
            "Filename must match YYYY-MM-DD-explanation-<lowercase-slug>.html."
        )
    else:
        try:
            filename_date = date.fromisoformat(filename_match.group(1))
        except ValueError:
            errors.append("Filename begins with an invalid calendar date.")
        else:
            if require_today and filename_date != date.today():
                errors.append(
                    f"Filename date must be today's local date ({date.today().isoformat()})."
                )

    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"Could not read UTF-8 HTML: {exc}")
        return errors, notes, ExplanationHTMLParser()

    if not re.match(r"\s*<!doctype\s+html\s*>", source, re.IGNORECASE):
        errors.append("Document must begin with <!doctype html>.")

    parser = ExplanationHTMLParser()
    try:
        parser.feed(source)
        parser.close()
    except Exception as exc:  # HTMLParser errors are uncommon but should be visible.
        errors.append(f"HTML parsing failed: {exc}")
        return errors, notes, parser

    for section_id in (*REQUIRED_SECTION_IDS, *REQUIRED_BACKGROUND_IDS):
        if section_id not in parser.ids:
            errors.append(f"Missing required element id={section_id!r}.")
    if parser.duplicate_ids:
        errors.append(
            "Element IDs must be unique; duplicates found: "
            + ", ".join(sorted(parser.duplicate_ids))
        )

    for section_id in REQUIRED_SECTION_IDS:
        if section_id not in parser.nav_hrefs:
            errors.append(f"Table of contents must link to #{section_id}.")

    if parser.toc_count != 1:
        errors.append(
            f"Document must contain one nav.toc table of contents; found {parser.toc_count}."
        )
    if not parser.viewport_count:
        errors.append("Missing viewport meta tag for responsive layout.")
    if not parser.styles:
        errors.append("Missing inline CSS in a <style> element.")
    if not parser.scripts:
        errors.append("Missing inline JavaScript in a <script> element.")
    if parser.external_resources:
        errors.append(
            "External resource dependencies found: "
            + ", ".join(parser.external_resources)
        )
    if parser.tab_count:
        errors.append("Top-level tab roles are not allowed; use one scrolling page.")

    css = "\n".join(parser.styles)
    javascript = "\n".join(parser.scripts)
    if re.search(r"@import\b", css, re.IGNORECASE):
        errors.append("CSS must not use @import.")
    css_urls = external_css_urls(css)
    if css_urls:
        errors.append("CSS references external resources: " + ", ".join(css_urls))
    if "@media" not in css:
        errors.append("CSS must include responsive or reduced-motion media rules.")
    if parser.pre_count < 1:
        errors.append("Code section must include at least one <pre> code block.")
    elif not css_preserves_preformatted_whitespace(css):
        errors.append(
            "CSS must apply white-space: pre or pre-wrap to <pre> code blocks."
        )
    else:
        notes.append(
            f"Confirmed whitespace-preserving CSS for {parser.pre_count} code block(s)."
        )

    if parser.diagram_count < 2:
        errors.append("Include at least two HTML diagrams with class=\"diagram\".")
    if parser.callout_count < 1:
        errors.append("Include at least one callout with class=\"callout\".")

    if len(parser.questions) != 5:
        errors.append(
            f"Quiz must contain exactly five .quiz-question elements; found {len(parser.questions)}."
        )
    for number, question in enumerate(parser.questions, start=1):
        options = question["options"]
        assert isinstance(options, list)
        if len(options) < 2:
            errors.append(f"Quiz question {number} must have at least two options.")
        invalid_values = [value for value in options if value not in {"true", "false"}]
        if invalid_values:
            errors.append(
                f"Quiz question {number} has an option without data-correct=\"true|false\"."
            )
        if options.count("true") != 1:
            errors.append(f"Quiz question {number} must have exactly one correct option.")
        if question["non_button"]:
            errors.append(f"Quiz question {number} options must use <button> elements.")
        if not question["feedback"]:
            errors.append(f"Quiz question {number} is missing .quiz-feedback.")
        elif not question["feedback_live"]:
            errors.append(
                f"Quiz question {number} feedback must include aria-live=\"polite\"."
            )

    if "quiz-option" not in javascript or not re.search(
        r"addEventListener\s*\(", javascript
    ):
        errors.append(
            "Inline JavaScript must attach event listeners to the quiz options."
        )
    if re.search(r"\b(?:fetch|XMLHttpRequest|WebSocket)\b", javascript):
        errors.append("Quiz JavaScript must not load data from external services.")

    if not errors:
        notes.append("Required sections, diagrams, callouts, and five-question quiz are present.")
        notes.append("No external resource dependencies were found.")
    return errors, notes, parser


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate an interactive HTML file produced by the rb-explain-diff skill."
    )
    parser.add_argument("html_file", type=Path)
    parser.add_argument(
        "--allow-historical-date",
        action="store_true",
        help="Allow a valid date other than today when rechecking an older artifact.",
    )
    args = parser.parse_args()

    errors, notes, _ = validate(
        args.html_file.resolve(), require_today=not args.allow_historical_date
    )
    for note in notes:
        print(f"OK: {note}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"PASS: {args.html_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
