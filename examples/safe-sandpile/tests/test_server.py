from http.client import HTTPConnection
import json
from pathlib import Path
import sys
import threading
import unittest


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from sandpile.model import SandpileModel  # noqa: E402
from sandpile.server import AppState, make_server  # noqa: E402


class SandpileServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = make_server(port=0, state=AppState(SandpileModel(size=6, seed=11)))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method: str, path: str, payload: object | None = None, content_type: str = "application/json"):
        connection = HTTPConnection("127.0.0.1", self.port, timeout=3)
        body = None if payload is None else json.dumps(payload)
        headers = {} if body is None else {"Content-Type": content_type}
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        result = response.status, dict(response.getheaders()), raw
        connection.close()
        return result

    def test_serves_local_interface_and_security_headers(self) -> None:
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Sandpile avalanche laboratory", body)
        self.assertIn(b'id="pile-3d"', body)
        self.assertIn(b"Central source with optional jitter", body)
        self.assertIn(b"Central jitter radius", body)
        self.assertIn(b"Physical slope pile", body)
        self.assertIn(b"Angle of repose", body)
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        for path in ("/app.js", "/styles.css"):
            status, _, body = self.request("GET", path)
            self.assertEqual(status, 200)
            self.assertTrue(body)

    def test_state_step_and_reset_endpoints(self) -> None:
        status, _, raw = self.request("POST", "/api/reset", {"size": 5, "seed": 19, "drop_mode": "center", "xmin": 2})
        self.assertEqual(status, 200)
        payload = json.loads(raw)
        self.assertEqual(payload["model"]["total_added"], 0)
        self.assertEqual(payload["limits"]["maximum_central_noise_radius"], 32)
        status, _, raw = self.request("POST", "/api/step", {"count": 20, "xmin": 2})
        self.assertEqual(status, 200)
        payload = json.loads(raw)
        self.assertEqual(payload["model"]["total_added"], 20)
        self.assertEqual(payload["model"]["mass_balance_residual"], 0)
        self.assertEqual(payload["analysis"]["power_law_fit"]["xmin"], 2)
        status, _, raw = self.request("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["model"]["total_added"], 20)

    def test_step_applies_selected_source_without_resetting_the_pile(self) -> None:
        status, _, raw = self.request(
            "POST",
            "/api/reset",
            {"size": 8, "seed": 19, "drop_mode": "random", "xmin": 2},
        )
        self.assertEqual(status, 200)

        status, _, raw = self.request(
            "POST",
            "/api/step",
            {
                "count": 30,
                "xmin": 2,
                "drop_mode": "center",
                "central_noise_radius": 2,
            },
        )

        self.assertEqual(status, 200)
        payload = json.loads(raw)
        self.assertEqual(payload["model"]["drop_mode"], "center")
        self.assertEqual(payload["model"]["central_noise_radius"], 2)
        self.assertEqual(payload["model"]["total_added"], 30)
        self.assertGreater(
            len(
                {
                    (event["row"], event["column"])
                    for event in payload["model"]["recent_avalanches"]
                }
            ),
            1,
        )
        self.assertTrue(
            all(
                (event["row"] - 4) ** 2 + (event["column"] - 4) ** 2 <= 2 ** 2
                for event in payload["model"]["recent_avalanches"]
            )
        )

    def test_invalid_central_noise_is_rejected_without_mutating_state(self) -> None:
        _, _, before_raw = self.request("GET", "/api/state")
        before = json.loads(before_raw)["model"]

        status, _, raw = self.request(
            "POST",
            "/api/step",
            {"count": 1, "drop_mode": "center", "central_noise_radius": 33},
        )

        self.assertEqual(status, 400)
        self.assertIn("central_noise_radius", json.loads(raw)["error"])
        _, _, after_raw = self.request("GET", "/api/state")
        after = json.loads(after_raw)["model"]
        self.assertEqual(after["total_added"], before["total_added"])
        self.assertEqual(after["drop_mode"], before["drop_mode"])

    def test_reset_selects_physical_slope_model_and_reports_real_height(self) -> None:
        status, _, raw = self.request(
            "POST",
            "/api/reset",
            {
                "size": 17,
                "seed": 43,
                "drop_mode": "center",
                "central_noise_radius": 1,
                "model_type": "slope",
                "angle_of_repose_degrees": 40,
                "xmin": 2,
            },
        )
        self.assertEqual(status, 200)

        status, _, raw = self.request(
            "POST",
            "/api/step",
            {"count": 1_000, "drop_mode": "center", "central_noise_radius": 1},
        )

        self.assertEqual(status, 200)
        payload = json.loads(raw)
        self.assertEqual(payload["model"]["model_type"], "slope")
        self.assertEqual(payload["model"]["angle_of_repose_degrees"], 40.0)
        self.assertEqual(payload["model"]["layer_height_cells"], 0.1)
        self.assertGreater(payload["model"]["maximum_height_layers"], 3)
        self.assertLessEqual(payload["model"]["maximum_slope_degrees"], 40.0 + 1e-9)
        self.assertEqual(payload["model"]["mass_balance_residual"], 0)

    def test_invalid_repose_angle_is_rejected_without_replacing_experiment(self) -> None:
        _, _, before_raw = self.request("GET", "/api/state")
        before = json.loads(before_raw)["model"]

        status, _, raw = self.request(
            "POST",
            "/api/reset",
            {
                "size": 17,
                "seed": 43,
                "drop_mode": "center",
                "model_type": "slope",
                "angle_of_repose_degrees": 60.1,
                "xmin": 2,
            },
        )

        self.assertEqual(status, 400)
        self.assertIn("angle_of_repose_degrees", json.loads(raw)["error"])
        _, _, after_raw = self.request("GET", "/api/state")
        after = json.loads(after_raw)["model"]
        self.assertEqual(after["model_type"], before["model_type"])
        self.assertEqual(after["angle_of_repose_degrees"], before["angle_of_repose_degrees"])
        self.assertEqual(after["total_added"], before["total_added"])
        self.assertEqual(after["grid"], before["grid"])

    def test_invalid_requests_are_rejected_without_mutating_state(self) -> None:
        _, _, before_raw = self.request("GET", "/api/state")
        before = json.loads(before_raw)["model"]["total_added"]
        status, _, raw = self.request("POST", "/api/step", {"count": 5001})
        self.assertEqual(status, 400)
        self.assertIn("between", json.loads(raw)["error"])
        status, _, _ = self.request("POST", "/api/step", {"count": 1}, content_type="text/plain")
        self.assertEqual(status, 415)
        _, _, after_raw = self.request("GET", "/api/state")
        self.assertEqual(json.loads(after_raw)["model"]["total_added"], before)

    def test_unlisted_and_traversal_paths_are_not_served(self) -> None:
        for path in ("/missing", "/../sandpile/model.py", "/%2e%2e/sandpile/model.py"):
            status, _, raw = self.request("GET", path)
            self.assertEqual(status, 404)
            self.assertEqual(json.loads(raw)["error"], "resource not found")


if __name__ == "__main__":
    unittest.main()
