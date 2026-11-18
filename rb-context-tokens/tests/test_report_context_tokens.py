import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPORTER = Path(__file__).resolve().parents[1] / "scripts" / "report_context_tokens.py"
EARLIER = "2026-01-01T12:00:00.000Z"
LATEST = "2026-01-01T12:01:00.000Z"


def token_event(timestamp, **payload):
    return {
        "timestamp": timestamp,
        "type": "event_msg",
        "payload": {"type": "token_count", **payload},
    }


def measured_event(timestamp, input_tokens):
    return token_event(
        timestamp,
        info={
            "model_context_window": 10_000,
            "last_token_usage": {
                "input_tokens": input_tokens,
                "cached_input_tokens": 80,
                "output_tokens": 25,
                "reasoning_output_tokens": 5,
                "total_tokens": input_tokens + 25,
            },
            "total_token_usage": {"total_tokens": 2000},
        },
    )


class ContextTokenReporterTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.session = Path(directory.name) / "session.jsonl"

    def write_events(self, *events):
        rows = ({"type": "session_meta", "payload": {"thread_source": "user"}}, *events)
        self.session.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def run_reporter(self, *args, expected_exit=0):
        result = subprocess.run(
            [sys.executable, str(REPORTER), "--session", str(self.session), *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, expected_exit, result.stderr)
        self.assertEqual(result.stderr, "")
        return result.stdout

    def test_latest_event_with_null_info_has_separate_history_in_json_and_text(self):
        self.write_events(
            measured_event("2026-01-01T11:59:00.000Z", 700),
            measured_event(EARLIER, 1200),
            token_event("2026-01-01T12:00:30.000Z"),
            token_event(LATEST, info=None),
        )

        report = json.loads(self.run_reporter("--json"))
        self.assertEqual(report["event_timestamp"], LATEST)
        self.assertEqual(report["event_line"], 5)
        self.assertEqual(report["current_measurement_status"], "unavailable")
        self.assertIsNone(report["current_context_tokens"])
        self.assertIsNone(report["current_context_window_percent"])
        self.assertIsNone(report["last_call_total_tokens"])
        recorded = report["last_recorded_measurement"]
        self.assertEqual(recorded["event_timestamp"], EARLIER)
        self.assertEqual(recorded["event_line"], 3)
        self.assertEqual(recorded["input_tokens"], 1200)
        self.assertEqual(recorded["context_window_percent"], 12.0)
        self.assertEqual(recorded["last_call_total_tokens"], 1225)

        current, history = self.run_reporter().split("Last recorded measurement:", 1)
        self.assertIn(f"Token event: {LATEST} (line 5)", current)
        self.assertIn("Current context: unavailable", current)
        self.assertNotIn("1,200", current)
        self.assertIn(f"{EARLIER} (line 3)", history)
        self.assertIn("1,200", history)
        self.assertIn("12.00%", history)

    def test_missing_or_unusable_input_is_never_a_measurement(self):
        incomplete_payloads = (
            {},
            {"info": None},
            {"info": []},
            {"info": {"last_token_usage": None, "total_token_usage": None}},
            {"info": {"last_token_usage": {}}},
            {"info": {"last_token_usage": {"input_tokens": None}}},
            {"info": {"last_token_usage": {"input_tokens": True, "total_tokens": 73}}},
            {"info": {"last_token_usage": {"input_tokens": -1}}},
            {"info": {"last_token_usage": {"input_tokens": "1200"}}},
        )
        for payload in incomplete_payloads:
            with self.subTest(payload=payload):
                self.write_events(token_event(EARLIER), token_event(LATEST, **payload))
                report = json.loads(self.run_reporter("--json"))
                self.assertEqual(report["event_timestamp"], LATEST)
                self.assertEqual(report["current_measurement_status"], "unavailable")
                self.assertIsNone(report["current_context_tokens"])
                self.assertIsNone(report["last_recorded_measurement"])
        self.assertIn("No earlier token measurement is available", self.run_reporter())

    def test_complete_latest_event_preserves_existing_metrics(self):
        self.write_events(token_event(EARLIER, info=None), measured_event(LATEST, 2600))
        report = json.loads(self.run_reporter("--json"))
        self.assertEqual(Path(report["session"]), self.session.resolve())
        self.assertEqual(report["event_timestamp"], LATEST)
        self.assertEqual(report["event_line"], 3)
        self.assertEqual(report["current_measurement_status"], "available")
        self.assertEqual(report["current_context_tokens"], 2600)
        self.assertEqual(report["current_context_window_percent"], 26.0)
        self.assertEqual(report["model_context_window"], 10_000)
        self.assertEqual(report["last_token_usage"]["cached_input_tokens"], 80)
        self.assertEqual(report["total_token_usage"], {"total_tokens": 2000})
        self.assertEqual(report["last_call_total_tokens"], 2625)
        self.assertAlmostEqual(report["last_call_context_window_percent"], 26.25)
        self.assertIsNone(report["last_recorded_measurement"])

        output = self.run_reporter()
        self.assertIn("Current context:\n", output)
        self.assertIn("2,600", output)
        self.assertIn("26.00%", output)
        self.assertIn("Last call:\n", output)
        self.assertIn("Cumulative session usage:\n", output)
        self.assertNotIn("Last recorded measurement", output)

    def test_zero_input_is_usable_even_when_optional_usage_is_missing(self):
        self.write_events(
            measured_event(EARLIER, 1200),
            token_event(LATEST, info={"last_token_usage": {"input_tokens": 0}}),
        )
        report = json.loads(self.run_reporter("--json"))
        self.assertEqual(report["current_measurement_status"], "available")
        self.assertEqual(report["current_context_tokens"], 0)
        self.assertIsNone(report["current_context_window_percent"])
        self.assertIsNone(report["last_recorded_measurement"])

    def test_partial_latest_usage_does_not_take_values_from_history(self):
        self.write_events(
            measured_event(EARLIER, 1200),
            token_event(
                LATEST,
                info={"last_token_usage": {"output_tokens": 40}, "model_context_window": 2000},
            ),
        )
        report = json.loads(self.run_reporter("--json"))
        self.assertEqual(report["current_measurement_status"], "unavailable")
        self.assertIsNone(report["current_context_tokens"])
        self.assertIsNone(report["current_context_window_percent"])
        self.assertEqual(report["model_context_window"], 2000)
        self.assertEqual(report["last_token_usage"]["output_tokens"], 40)
        history = report["last_recorded_measurement"]
        self.assertEqual(history["input_tokens"], 1200)
        self.assertEqual(history["model_context_window"], 10_000)
        self.assertEqual(history["context_window_percent"], 12.0)

        current, earlier = self.run_reporter().split("Last recorded measurement:", 1)
        self.assertIn("Current context: unavailable", current)
        self.assertIn("context window:           2,000", current)
        self.assertIn("output tokens:            40", current)
        self.assertNotIn("1,200", current)
        self.assertIn("output tokens:            25", earlier)

    def test_no_token_events_reports_absence_in_json_and_text(self):
        self.write_events({"type": "response_item", "payload": {}})
        self.assertIn("No token_count events found", self.run_reporter(expected_exit=1))
        report = json.loads(self.run_reporter("--json", expected_exit=1))
        self.assertEqual(Path(report["session"]), self.session.resolve())
        self.assertEqual(report["current_measurement_status"], "no_token_count_events")
        self.assertIsNone(report["event_timestamp"])
        self.assertIsNone(report["current_context_tokens"])
        self.assertIsNone(report["last_recorded_measurement"])


if __name__ == "__main__":
    unittest.main()
