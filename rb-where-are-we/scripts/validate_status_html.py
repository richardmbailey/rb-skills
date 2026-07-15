#!/usr/bin/env python3
"""Validate the deterministic structure of an rb-where-are-we HTML report."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_SECTION_IDS = (
    "executive-summary",
    "goals-roadmap",
    "health",
    "current-phase",
    "system-view",
    "risks",
    "recent-changes",
    "next-steps",
    "evidence",
)
EVIDENCE_STATES = {"verified", "documented", "inferred", "unknown"}
HEALTH_STATES = {"strong", "mixed", "at-risk", "unknown"}
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


class StatusHTMLParser(HTMLParser):
    """Collect the structural signals required by the report contract."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_lang = ""
        self.ids: dict[str, str] = {}
        self.duplicate_ids: set[str] = set()
        self.section_order: list[str] = []
        self.nav_hrefs: set[str] = set()
        self.nav_depth = 0
        self.toc_count = 0
        self.main_count = 0
        self.style_depth = 0
        self.script_depth = 0
        self.styles: list[str] = []
        self.scripts: list[str] = []
        self.pre_count = 0
        self.diagram_count = 0
        self.viewport_count = 0
        self.tab_count = 0
        self.generated_times: list[str] = []
        self.evidence_legend_count = 0
        self.evidence_markers: list[str] = []
        self.health_cards: list[str] = []
        self.check_result_count = 0
        self.evidence_source_count = 0
        self.change_window_count = 0
        self.external_resources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        classes = set(attributes.get("class", "").split())

        if tag == "html":
            self.html_lang = attributes.get("lang", "").strip()

        element_id = attributes.get("id")
        if element_id:
            if element_id in self.ids:
                self.duplicate_ids.add(element_id)
            self.ids[element_id] = tag
            if element_id in REQUIRED_SECTION_IDS:
                self.section_order.append(element_id)

        if tag == "nav" and "toc" in classes:
            self.nav_depth += 1
            self.toc_count += 1
        if self.nav_depth and tag == "a":
            href = attributes.get("href", "")
            if href.startswith("#"):
                self.nav_hrefs.add(href[1:])

        if tag == "main":
            self.main_count += 1
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
        if attributes.get("role", "").lower() in {"tab", "tablist", "tabpanel"}:
            self.tab_count += 1

        if tag == "time" and "report-generated" in classes:
            self.generated_times.append(attributes.get("datetime", ""))
        if "evidence-legend" in classes:
            self.evidence_legend_count += 1
        if "data-evidence" in attributes:
            self.evidence_markers.append(attributes["data-evidence"])
        if "health-card" in classes:
            self.health_cards.append(attributes.get("data-health", ""))
        if "check-result" in classes:
            self.check_result_count += 1
        if "evidence-source" in classes:
            self.evidence_source_count += 1
        if "change-window" in classes:
            self.change_window_count += 1

        self._check_external_resource(tag, attributes)

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
            if not value or value.startswith(("data:", "#")):
                continue
            parsed = urlparse(value)
            if parsed.scheme or parsed.netloc or not value.startswith("data:"):
                self.external_resources.append(f"{tag}[{attribute}={value!r}]")


def css_preserves_preformatted_whitespace(css: str) -> bool:
    """Return True when a CSS rule targeting pre preserves its whitespace."""
    for selectors, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", css, re.DOTALL):
        if not re.search(r"(?:^|[\s>+~,.#:\[])pre(?:$|[\s>+~,.#:\[])", selectors):
            continue
        if re.search(
            r"white-space\s*:\s*(?:pre|pre-wrap)\b", declarations, re.IGNORECASE
        ):
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


def parse_generated_time(value: str) -> datetime | None:
    """Parse an ISO date-time, rejecting a date without a time component."""
    if "T" not in value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def validate(
    path: Path, *, require_today: bool = True
) -> tuple[list[str], list[str], StatusHTMLParser]:
    errors: list[str] = []
    notes: list[str] = []

    if path.parent.name != "status" or path.parent.parent.name != "reports":
        errors.append("The HTML file must be inside <repository>/reports/status/.")

    filename_date: date | None = None
    filename_match = re.fullmatch(
        r"(\d{4}-\d{2}-\d{2})-where-are-we-[a-z0-9][a-z0-9-]*\.html",
        path.name,
    )
    if not filename_match:
        errors.append(
            "Filename must match YYYY-MM-DD-where-are-we-<lowercase-slug>.html."
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
        return errors, notes, StatusHTMLParser()

    if not re.match(r"\s*<!doctype\s+html\s*>", source, re.IGNORECASE):
        errors.append("Document must begin with <!doctype html>.")

    parser = StatusHTMLParser()
    try:
        parser.feed(source)
        parser.close()
    except Exception as exc:
        errors.append(f"HTML parsing failed: {exc}")
        return errors, notes, parser

    if not parser.html_lang:
        errors.append("The <html> element must include a language attribute.")
    for section_id in REQUIRED_SECTION_IDS:
        if section_id not in parser.ids:
            errors.append(f"Missing required element id={section_id!r}.")
        if section_id not in parser.nav_hrefs:
            errors.append(f"Table of contents must link to #{section_id}.")
    if parser.duplicate_ids:
        errors.append(
            "Element IDs must be unique; duplicates found: "
            + ", ".join(sorted(parser.duplicate_ids))
        )
    if tuple(parser.section_order) != REQUIRED_SECTION_IDS:
        errors.append("Required report sections must appear in the prescribed order.")

    if parser.toc_count != 1:
        errors.append(
            f"Document must contain one nav.toc table of contents; found {parser.toc_count}."
        )
    if parser.main_count != 1:
        errors.append(f"Document must contain one <main>; found {parser.main_count}.")
    if not parser.viewport_count:
        errors.append("Missing viewport meta tag for responsive layout.")
    if not parser.styles:
        errors.append("Missing inline CSS in a <style> element.")
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
    if not re.search(
        r"@media\s*\([^)]*(?:max-width|min-width|width\s*[<>])", css, re.IGNORECASE
    ):
        errors.append("CSS must include a responsive width media rule.")
    if not re.search(r"@media\s+print\b", css, re.IGNORECASE):
        errors.append("CSS must include a print media rule.")
    if "prefers-reduced-motion" not in css:
        errors.append("CSS must include reduced-motion behaviour.")
    if parser.pre_count and not css_preserves_preformatted_whitespace(css):
        errors.append(
            "CSS must apply white-space: pre or pre-wrap to every <pre> code block."
        )
    elif parser.pre_count:
        notes.append(
            f"Confirmed whitespace-preserving CSS for {parser.pre_count} code block(s)."
        )
    if re.search(r"\b(?:fetch|XMLHttpRequest|WebSocket)\b", javascript):
        errors.append("Inline JavaScript must not load data from external services.")

    if len(parser.generated_times) != 1:
        errors.append(
            f"Document must contain one time.report-generated; found {len(parser.generated_times)}."
        )
    else:
        generated_time = parse_generated_time(parser.generated_times[0])
        if generated_time is None:
            errors.append("time.report-generated must have a valid ISO date-time value.")
        elif filename_date is not None and generated_time.date() != filename_date:
            errors.append("The generation timestamp date must match the filename date.")

    if parser.evidence_legend_count != 1:
        errors.append(
            f"Document must contain one .evidence-legend; found {parser.evidence_legend_count}."
        )
    if len(parser.evidence_markers) < 5:
        errors.append(
            f"Mark at least five major claims with data-evidence; found {len(parser.evidence_markers)}."
        )
    invalid_evidence = sorted(set(parser.evidence_markers) - EVIDENCE_STATES)
    if invalid_evidence:
        errors.append("Invalid data-evidence values: " + ", ".join(invalid_evidence))

    if len(parser.health_cards) != 6:
        errors.append(
            f"Health section must contain six .health-card elements; found {len(parser.health_cards)}."
        )
    invalid_health = sorted(set(parser.health_cards) - HEALTH_STATES)
    if invalid_health:
        errors.append("Invalid data-health values: " + ", ".join(invalid_health))

    if parser.check_result_count < 1:
        errors.append("Evidence appendix must contain at least one .check-result.")
    if parser.evidence_source_count < 1:
        errors.append("Evidence appendix must contain at least one .evidence-source.")
    if parser.change_window_count != 1:
        errors.append(
            f"Recent changes must contain one .change-window; found {parser.change_window_count}."
        )

    if not errors:
        notes.append("All nine progressively detailed report sections are present.")
        notes.append("Evidence labels and six code-health dimensions are present.")
        if parser.diagram_count:
            notes.append(f"Found {parser.diagram_count} HTML diagram(s).")
        notes.append("No external resource dependencies were found.")
    return errors, notes, parser


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate an HTML report produced by rb-where-are-we."
    )
    parser.add_argument("html_file", type=Path)
    parser.add_argument(
        "--allow-historical-date",
        action="store_true",
        help="Allow a valid date other than today when rechecking an older report.",
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
