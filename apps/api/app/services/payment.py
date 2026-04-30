import hashlib
import hmac

import httpx

from app.core.config import settings

PORTONE_API_BASE = "https://api.portone.io"


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify PortOne V2 webhook signature (HMAC-SHA256 of raw body)."""
    # PortOne V2 sends "v1={hex_digest}" in x-portone-signature header
    sig_value = signature.removeprefix("v1=")
    expected = hmac.new(
        settings.PORTONE_API_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, sig_value)


async def get_payment(payment_id: str) -> dict:
    """Fetch payment details from PortOne V2 API."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{PORTONE_API_BASE}/payments/{payment_id}",
            headers={"Authorization": f"PortOne {settings.PORTONE_API_SECRET}"},
            timeout=10.0,
        )
    if resp.status_code != 200:
        raise ValueError(f"PortOne API 오류: {resp.status_code} {resp.text}")
    return resp.json()
