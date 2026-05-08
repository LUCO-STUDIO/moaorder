from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ops_alert import AlertLevel, notify


@pytest.mark.asyncio
async def test_notify_no_op_when_url_unset() -> None:
    """No webhook URL → silent no-op (no httpx call attempted)."""
    with patch("app.services.ops_alert.settings") as mock_settings:
        mock_settings.DISCORD_OPS_WEBHOOK_URL = ""
        with patch("app.services.ops_alert.httpx.AsyncClient") as mock_client:
            await notify("test", level=AlertLevel.WARNING)
    mock_client.assert_not_called()


@pytest.mark.asyncio
async def test_notify_posts_to_discord_when_url_set() -> None:
    """URL set → POSTs JSON {content: ...} to the configured webhook."""
    captured: dict = {}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return MagicMock(status_code=204)

    with patch("app.services.ops_alert.settings") as mock_settings:
        mock_settings.DISCORD_OPS_WEBHOOK_URL = "https://discord/webhooks/test"
        with patch("app.services.ops_alert.httpx.AsyncClient", FakeClient):
            await notify(
                "결제 검증 실패",
                level=AlertLevel.CRITICAL,
                context={"payment_id": "pay_123"},
            )

    assert captured["url"] == "https://discord/webhooks/test"
    body = captured["json"]["content"]
    assert "🚨" in body
    assert "CRITICAL" in body
    assert "결제 검증 실패" in body
    assert "payment_id" in body
    assert "pay_123" in body


@pytest.mark.asyncio
async def test_notify_swallows_http_errors() -> None:
    """Network failure must never break the caller."""
    class ExplodingClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            raise RuntimeError("network down")

    with patch("app.services.ops_alert.settings") as mock_settings:
        mock_settings.DISCORD_OPS_WEBHOOK_URL = "https://discord/webhooks/test"
        with patch(
            "app.services.ops_alert.httpx.AsyncClient", ExplodingClient
        ):
            # Must not raise.
            await notify("any", level=AlertLevel.WARNING)


@pytest.mark.asyncio
async def test_notify_truncates_long_message() -> None:
    """Discord caps content at 2000 chars; we guard by trimming to ~1990."""
    captured: dict = {}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json):
            captured["json"] = json
            return MagicMock(status_code=204)

    with patch("app.services.ops_alert.settings") as mock_settings:
        mock_settings.DISCORD_OPS_WEBHOOK_URL = "https://discord/webhooks/test"
        with patch("app.services.ops_alert.httpx.AsyncClient", FakeClient):
            await notify("x" * 5000)

    assert len(captured["json"]["content"]) <= 1990
