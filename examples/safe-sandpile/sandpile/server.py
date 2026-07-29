"""Loopback-only web server for the sandpile demonstration."""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from typing import Any
from urllib.parse import urlsplit

from .analysis import summarize_avalanches
from .model import SandpileModel


WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
MAX_BODY_BYTES = 16_384
MAX_STEP_COUNT = 5_000
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}


class RequestError(ValueError):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        super().__init__(message)
        self.status = status


def _required_integer(
    payload: dict[str, Any],
    key: str,
    minimum: int,
    maximum: int,
) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise RequestError(f"{key} must be an integer")
    if not minimum <= value <= maximum:
        raise RequestError(f"{key} must be between {minimum} and {maximum}")
    return value


def _required_number(
    payload: dict[str, Any],
    key: str,
    minimum: float,
    maximum: float,
) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RequestError(f"{key} must be a number")
    value = float(value)
    if not minimum <= value <= maximum:
        raise RequestError(f"{key} must be between {minimum:g} and {maximum:g}")
    return value


class AppState:
    def __init__(self, model: SandpileModel | None = None, xmin: int = 1) -> None:
        self.lock = threading.Lock()
        self.model = model or SandpileModel(
            central_noise_radius=1,
            model_type="slope",
            angle_of_repose_degrees=40.0,
        )
        self.xmin = xmin

    def response(self) -> dict[str, object]:
        sizes = [event.size for event in self.model.avalanches]
        return {
            "model": self.model.snapshot(),
            "analysis": summarize_avalanches(sizes, xmin=self.xmin),
            "limits": {
                "minimum_size": SandpileModel.MIN_SIZE,
                "maximum_size": SandpileModel.MAX_SIZE,
                "maximum_step_count": MAX_STEP_COUNT,
                "maximum_central_noise_radius": SandpileModel.MAX_CENTRAL_NOISE_RADIUS,
                "minimum_repose_angle_degrees": SandpileModel.MIN_REPOSE_ANGLE_DEGREES,
                "maximum_repose_angle_degrees": SandpileModel.MAX_REPOSE_ANGLE_DEGREES,
            },
        }

    def step(
        self,
        count: int,
        xmin: int | None = None,
        drop_mode: str | None = None,
        central_noise_radius: int | None = None,
    ) -> dict[str, object]:
        with self.lock:
            if xmin is not None:
                self.xmin = xmin
            if drop_mode is not None or central_noise_radius is not None:
                self.model.set_source(
                    drop_mode=drop_mode or self.model.drop_mode,
                    central_noise_radius=(
                        self.model.central_noise_radius
                        if central_noise_radius is None
                        else central_noise_radius
                    ),
                )
            self.model.add_grains(count)
            return self.response()

    def reset(
        self,
        size: int,
        seed: int,
        drop_mode: str,
        xmin: int,
        central_noise_radius: int = 0,
        model_type: str = "btw",
        angle_of_repose_degrees: float = 40.0,
    ) -> dict[str, object]:
        with self.lock:
            self.model = SandpileModel(
                size=size,
                seed=seed,
                drop_mode=drop_mode,
                central_noise_radius=central_noise_radius,
                model_type=model_type,
                angle_of_repose_degrees=angle_of_repose_degrees,
            )
            self.xmin = xmin
            return self.response()


class SandpileHandler(BaseHTTPRequestHandler):
    server_version = "SafeSandpile/1.0"

    @property
    def app_state(self) -> AppState:
        return self.server.app_state  # type: ignore[attr-defined,no-any-return]

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"{self.address_string()} - {format_string % args}")

    def _security_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'")

    def _send_bytes(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
        self._send_bytes(status, body, "application/json; charset=utf-8")

    def _read_json(self) -> dict[str, Any]:
        content_type = self.headers.get_content_type()
        if content_type != "application/json":
            raise RequestError("Content-Type must be application/json", HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise RequestError("Content-Length is required", HTTPStatus.LENGTH_REQUIRED)
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise RequestError("Content-Length must be an integer") from exc
        if length < 0 or length > MAX_BODY_BYTES:
            raise RequestError("request body is too large", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        try:
            payload = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RequestError("request body must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise RequestError("request body must be a JSON object")
        return payload

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path == "/api/state":
            with self.app_state.lock:
                self._send_json(HTTPStatus.OK, self.app_state.response())
            return
        static = STATIC_FILES.get(path)
        if static is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "resource not found"})
            return
        filename, content_type = static
        try:
            body = (WEB_ROOT / filename).read_bytes()
        except OSError:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "static resource unavailable"})
            return
        self._send_bytes(HTTPStatus.OK, body, content_type)

    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/step":
                unknown = set(payload) - {
                    "count",
                    "xmin",
                    "drop_mode",
                    "central_noise_radius",
                }
                if unknown:
                    raise RequestError(f"unknown fields: {', '.join(sorted(unknown))}")
                count = _required_integer(payload, "count", 1, MAX_STEP_COUNT)
                xmin = payload.get("xmin")
                if xmin is not None:
                    xmin = _required_integer(payload, "xmin", 1, 1_000_000)
                drop_mode = payload.get("drop_mode")
                if drop_mode is not None and drop_mode not in {"random", "center"}:
                    raise RequestError("drop_mode must be 'random' or 'center'")
                central_noise_radius = payload.get("central_noise_radius")
                if central_noise_radius is not None:
                    central_noise_radius = _required_integer(
                        payload,
                        "central_noise_radius",
                        0,
                        SandpileModel.MAX_CENTRAL_NOISE_RADIUS,
                    )
                response = self.app_state.step(
                    count=count,
                    xmin=xmin,
                    drop_mode=drop_mode,
                    central_noise_radius=central_noise_radius,
                )
            elif path == "/api/reset":
                required = {"size", "seed", "drop_mode", "xmin"}
                allowed = required | {
                    "central_noise_radius",
                    "model_type",
                    "angle_of_repose_degrees",
                }
                if not required <= set(payload) or not set(payload) <= allowed:
                    missing = sorted(required - set(payload))
                    unknown = sorted(set(payload) - allowed)
                    details = []
                    if missing:
                        details.append(f"missing: {', '.join(missing)}")
                    if unknown:
                        details.append(f"unknown: {', '.join(unknown)}")
                    raise RequestError("reset fields are invalid (" + "; ".join(details) + ")")
                size = _required_integer(payload, "size", SandpileModel.MIN_SIZE, SandpileModel.MAX_SIZE)
                seed = payload["seed"]
                if isinstance(seed, bool) or not isinstance(seed, int):
                    raise RequestError("seed must be an integer")
                drop_mode = payload["drop_mode"]
                if drop_mode not in {"random", "center"}:
                    raise RequestError("drop_mode must be 'random' or 'center'")
                xmin = _required_integer(payload, "xmin", 1, 1_000_000)
                central_noise_radius = payload.get("central_noise_radius", 0)
                if "central_noise_radius" in payload:
                    central_noise_radius = _required_integer(
                        payload,
                        "central_noise_radius",
                        0,
                        SandpileModel.MAX_CENTRAL_NOISE_RADIUS,
                    )
                model_type = payload.get("model_type", "btw")
                if model_type not in {"btw", "slope"}:
                    raise RequestError("model_type must be 'btw' or 'slope'")
                angle_of_repose_degrees = payload.get("angle_of_repose_degrees", 40.0)
                if "angle_of_repose_degrees" in payload:
                    angle_of_repose_degrees = _required_number(
                        payload,
                        "angle_of_repose_degrees",
                        SandpileModel.MIN_REPOSE_ANGLE_DEGREES,
                        SandpileModel.MAX_REPOSE_ANGLE_DEGREES,
                    )
                response = self.app_state.reset(
                    size=size,
                    seed=seed,
                    drop_mode=drop_mode,
                    xmin=xmin,
                    central_noise_radius=central_noise_radius,
                    model_type=model_type,
                    angle_of_repose_degrees=angle_of_repose_degrees,
                )
            else:
                raise RequestError("resource not found", HTTPStatus.NOT_FOUND)
        except RequestError as exc:
            self._send_json(exc.status, {"error": str(exc)})
            return
        except (TypeError, ValueError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self._send_json(HTTPStatus.OK, response)


class SandpileServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], app_state: AppState) -> None:
        super().__init__(address, SandpileHandler)
        self.app_state = app_state


def make_server(port: int = 8000, state: AppState | None = None) -> SandpileServer:
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65_535:
        raise ValueError("port must be an integer between 0 and 65535")
    return SandpileServer(("127.0.0.1", port), state or AppState())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the loopback-only sandpile web application")
    parser.add_argument("--port", type=int, default=8000, help="loopback TCP port (default: 8000)")
    args = parser.parse_args()
    server = make_server(port=args.port)
    host, port = server.server_address
    print(f"Sandpile application available at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
