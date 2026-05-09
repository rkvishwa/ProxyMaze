import asyncio
import json
from contextlib import suppress

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.scheduler import scheduler_loop
from app.state import AppState


class RawHttpTestServer:
    def __init__(self, handler):
        self._handler = handler
        self._server = None
        self.port = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle_client, "127.0.0.1", 0)
        socket = self._server.sockets[0]
        self.port = socket.getsockname()[1]

    async def close(self) -> None:
        if self._server is None:
            return
        self._server.close()
        await self._server.wait_closed()

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            request_line = await reader.readline()
            if not request_line:
                return

            method, path, _ = request_line.decode().strip().split()
            headers: dict[str, str] = {}
            while True:
                line = await reader.readline()
                if line in (b"", b"\r\n", b"\n"):
                    break
                name, value = line.decode().split(":", 1)
                headers[name.lower()] = value.strip()

            content_length = int(headers.get("content-length", "0") or 0)
            body = await reader.readexactly(content_length) if content_length else b""

            status_code, response_headers, response_body = await self._handler(
                method, path, headers, body
            )
            await self._write_response(writer, status_code, response_headers, response_body)
        finally:
            writer.close()
            with suppress(Exception):
                await writer.wait_closed()

    async def _write_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        response_headers: dict[str, str],
        response_body,
    ) -> None:
        if response_body is None:
            payload = b""
        elif isinstance(response_body, (dict, list)):
            payload = json.dumps(response_body).encode()
            response_headers = {
                "Content-Type": "application/json",
                **response_headers,
            }
        elif isinstance(response_body, str):
            payload = response_body.encode()
        else:
            payload = response_body

        status_text = {
            200: "OK",
            201: "Created",
            204: "No Content",
            404: "Not Found",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
            504: "Gateway Timeout",
        }.get(status_code, "OK")

        merged_headers = {
            "Content-Length": str(len(payload)),
            "Connection": "close",
            **response_headers,
        }
        header_blob = "".join(f"{name}: {value}\r\n" for name, value in merged_headers.items())
        writer.write(
            f"HTTP/1.1 {status_code} {status_text}\r\n{header_blob}\r\n".encode() + payload
        )
        with suppress(Exception):
            await writer.drain()


class ProxyBackend:
    def __init__(self) -> None:
        self.routes: dict[str, dict[str, float | int | dict | str]] = {}
        self.server = RawHttpTestServer(self._handler)

    async def start(self) -> None:
        await self.server.start()

    async def close(self) -> None:
        await self.server.close()

    def url_for(self, proxy_id: str) -> str:
        return f"{self.server.base_url}/proxy/{proxy_id}"

    def set_proxy(
        self,
        proxy_id: str,
        *,
        status_code: int = 200,
        delay_seconds: float = 0.0,
    ) -> None:
        self.routes[f"/proxy/{proxy_id}"] = {
            "status_code": status_code,
            "delay_seconds": delay_seconds,
            "body": {"proxy_id": proxy_id, "status": status_code},
        }

    async def _handler(self, method: str, path: str, headers: dict[str, str], body: bytes):
        route = self.routes.get(path)
        if route is None:
            return 404, {}, {"detail": "not found"}

        delay_seconds = float(route.get("delay_seconds", 0.0))
        if delay_seconds:
            await asyncio.sleep(delay_seconds)

        return int(route["status_code"]), {}, route["body"]


class WebhookCapture:
    def __init__(self, response_codes: list[int]) -> None:
        self.response_codes = response_codes[:]
        self.attempts: list[dict] = []
        self.successful_payloads: list[dict] = []
        self.server = RawHttpTestServer(self._handler)

    async def start(self) -> None:
        await self.server.start()

    async def close(self) -> None:
        await self.server.close()

    @property
    def url(self) -> str:
        return f"{self.server.base_url}/hook"

    async def _handler(self, method: str, path: str, headers: dict[str, str], body: bytes):
        payload = json.loads(body.decode()) if body else {}
        status_code = self.response_codes.pop(0) if self.response_codes else 200
        self.attempts.append(
            {
                "method": method,
                "path": path,
                "headers": headers,
                "status_code": status_code,
                "payload": payload,
            }
        )
        if status_code < 500:
            self.successful_payloads.append(payload)
        return status_code, {}, {"ok": True}


async def wait_for(assertion, timeout: float = 6.0, interval: float = 0.05):
    deadline = asyncio.get_running_loop().time() + timeout
    last_error = None
    while asyncio.get_running_loop().time() < deadline:
        try:
            result = await assertion()
            return result
        except AssertionError as error:
            last_error = error
            await asyncio.sleep(interval)

    if last_error is not None:
        raise last_error
    raise AssertionError("condition was not met before timeout")


@pytest.fixture
async def live_client():
    app.state.app_state = AppState()
    state = app.state.app_state
    state.scheduler_task = asyncio.create_task(scheduler_loop(state))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    state.scheduler_task.cancel()
    with suppress(asyncio.CancelledError):
        await state.scheduler_task
    app.state.app_state = None


@pytest.mark.asyncio
async def test_background_monitoring_wakes_immediately_and_recovers_without_false_alert(
    live_client,
):
    proxy_backend = ProxyBackend()
    await proxy_backend.start()

    try:
        for index in range(10):
            proxy_backend.set_proxy(f"px-{index:03d}", status_code=200)

        await asyncio.sleep(0.05)

        response = await live_client.post(
            "/config",
            json={"check_interval_seconds": 1, "request_timeout_ms": 150},
        )
        assert response.status_code == 200

        response = await live_client.post(
            "/proxies",
            json={
                "replace": True,
                "proxies": [proxy_backend.url_for(f"px-{index:03d}") for index in range(10)],
            },
        )
        assert response.status_code == 201

        async def assert_all_up():
            current = (await live_client.get("/proxies")).json()
            assert current["up"] == 10
            assert current["down"] == 0
            assert all(proxy["status"] == "up" for proxy in current["proxies"])
            assert all(proxy["last_checked_at"] for proxy in current["proxies"])
            return current

        await wait_for(assert_all_up)

        proxy_backend.set_proxy("px-003", status_code=500)

        async def assert_single_failure_detected():
            current = (await live_client.get("/proxies")).json()
            by_id = {proxy["id"]: proxy for proxy in current["proxies"]}
            assert current["up"] == 9
            assert current["down"] == 1
            assert round(current["failure_rate"], 4) == 0.1
            assert by_id["px-003"]["status"] == "down"
            assert by_id["px-003"]["consecutive_failures"] >= 1
            return current

        await wait_for(assert_single_failure_detected)

        alerts = (await live_client.get("/alerts")).json()
        assert alerts == []

        proxy_backend.set_proxy("px-003", status_code=200)

        async def assert_recovered():
            current = (await live_client.get("/proxies")).json()
            by_id = {proxy["id"]: proxy for proxy in current["proxies"]}
            assert current["up"] == 10
            assert current["down"] == 0
            assert by_id["px-003"]["status"] == "up"
            assert by_id["px-003"]["consecutive_failures"] == 0
            return current

        await wait_for(assert_recovered)
    finally:
        await proxy_backend.close()


@pytest.mark.asyncio
async def test_webhook_retry_resolution_and_rebreach_lifecycle(live_client):
    proxy_backend = ProxyBackend()
    capture = WebhookCapture(response_codes=[500, 500, 200, 200, 200])
    await proxy_backend.start()
    await capture.start()

    try:
        for index in range(10):
            proxy_backend.set_proxy(f"px-{index:03d}", status_code=200)

        await live_client.post(
            "/config",
            json={"check_interval_seconds": 1, "request_timeout_ms": 150},
        )
        await live_client.post("/webhooks", json={"url": capture.url, "ignored": "ok"})
        await live_client.post(
            "/proxies",
            json={
                "replace": True,
                "proxies": [proxy_backend.url_for(f"px-{index:03d}") for index in range(10)],
            },
        )

        async def assert_initially_healthy():
            current = (await live_client.get("/proxies")).json()
            assert current["up"] == 10
            assert current["down"] == 0
            return current

        await wait_for(assert_initially_healthy)

        proxy_backend.set_proxy("px-001", status_code=500)
        proxy_backend.set_proxy("px-002", status_code=502)
        proxy_backend.set_proxy("px-003", status_code=200, delay_seconds=0.4)

        async def assert_breach_active():
            alerts = (await live_client.get("/alerts")).json()
            assert len(alerts) == 1
            alert = alerts[0]
            assert alert["status"] == "active"
            assert round(alert["failure_rate"], 4) == 0.3
            assert alert["total_proxies"] == 10
            assert alert["failed_proxies"] == 3
            assert set(alert["failed_proxy_ids"]) == {"px-001", "px-002", "px-003"}
            return alert

        fired_alert = await wait_for(assert_breach_active)

        async def assert_fired_webhook_delivered_once():
            fired = [payload for payload in capture.successful_payloads if payload.get("event") == "alert.fired"]
            assert len(fired) == 1
            payload = fired[0]
            assert payload["alert_id"] == fired_alert["alert_id"]
            assert payload["failed_proxies"] == 3
            assert set(payload["failed_proxy_ids"]) == {"px-001", "px-002", "px-003"}
            return payload

        fired_payload = await wait_for(assert_fired_webhook_delivered_once)
        assert len(capture.attempts) >= 3
        assert all(
            attempt["headers"].get("content-type") == "application/json"
            for attempt in capture.attempts[:3]
        )

        await asyncio.sleep(1.2)
        fired_events = [
            payload for payload in capture.successful_payloads if payload.get("event") == "alert.fired"
        ]
        assert len(fired_events) == 1

        current_pool = (await live_client.get("/proxies")).json()
        assert current_pool["down"] == 3
        assert round(current_pool["failure_rate"], 4) == 0.3

        proxy_backend.set_proxy("px-001", status_code=200)
        proxy_backend.set_proxy("px-002", status_code=200)
        proxy_backend.set_proxy("px-003", status_code=200, delay_seconds=0.0)

        async def assert_resolved():
            alerts = (await live_client.get("/alerts")).json()
            assert len(alerts) == 1
            alert = alerts[0]
            assert alert["status"] == "resolved"
            assert alert["alert_id"] == fired_alert["alert_id"]
            assert alert["resolved_at"] is not None
            return alert

        resolved_alert = await wait_for(assert_resolved)

        async def assert_resolved_webhook():
            resolved = [
                payload
                for payload in capture.successful_payloads
                if payload.get("event") == "alert.resolved"
            ]
            assert len(resolved) == 1
            payload = resolved[0]
            assert payload["alert_id"] == resolved_alert["alert_id"]
            assert payload["resolved_at"] == resolved_alert["resolved_at"]
            return payload

        await wait_for(assert_resolved_webhook)

        proxy_backend.set_proxy("px-004", status_code=503)
        proxy_backend.set_proxy("px-005", status_code=504)

        async def assert_rebreach_created():
            alerts = (await live_client.get("/alerts")).json()
            assert len(alerts) == 2
            first, second = alerts
            assert first["status"] == "resolved"
            assert second["status"] == "active"
            assert second["alert_id"] != first["alert_id"]
            assert second["failed_proxies"] == 2
            assert set(second["failed_proxy_ids"]) == {"px-004", "px-005"}
            return alerts

        alerts = await wait_for(assert_rebreach_created)
        fired_events = [
            payload for payload in capture.successful_payloads if payload.get("event") == "alert.fired"
        ]
        assert len(fired_events) == 2
        assert fired_events[0]["alert_id"] == fired_payload["alert_id"]
        assert fired_events[1]["alert_id"] == alerts[1]["alert_id"]
        assert capture.successful_payloads[0]["event"] == "alert.fired"
        assert capture.successful_payloads[1]["event"] == "alert.resolved"
        assert capture.successful_payloads[2]["event"] == "alert.fired"
    finally:
        await proxy_backend.close()
        await capture.close()
