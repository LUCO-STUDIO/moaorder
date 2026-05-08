import os

# Must be set before any app imports so rate limiting is disabled in tests
os.environ["TESTING"] = "true"

import uuid
from typing import AsyncGenerator, Optional
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


@pytest.fixture(scope="session")
def event_loop_policy():
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(settings.DATABASE_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="session")
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db(session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session
        await session.rollback()


async def kakao_login(
    client: AsyncClient,
    *,
    nickname: str = "테스트유저",
    region: str = "서울",
    kakao_id: Optional[str] = None,
) -> str:
    """Drive the two-step kakao signup → return the session cookie token.

    /auth/kakao/exchange now returns a signup_token (no cookie) for new users;
    the cookie is only issued after /auth/kakao/complete-signup confirms terms,
    privacy, age, and region (PIPA §15, §22-2). This helper hides that flow so
    tests don't need to know about it.
    """
    kakao_info = {
        "kakao_id": kakao_id or f"test_{uuid.uuid4().hex[:8]}",
        "nickname": nickname,
        "profile_image": None,
    }
    with patch(
        "app.api.auth.exchange_kakao_code",
        new_callable=AsyncMock,
        return_value=kakao_info,
    ):
        exchange_resp = await client.post(
            "/api/auth/kakao/exchange", json={"code": "test_code"}
        )
    assert exchange_resp.status_code == 200, f"exchange failed: {exchange_resp.text}"
    body = exchange_resp.json()

    # Returning customer — cookie already issued.
    if body.get("status") == "registered":
        return exchange_resp.cookies["moaorder_token"]

    complete_resp = await client.post(
        "/api/auth/kakao/complete-signup",
        json={
            "signup_token": body["signup_token"],
            "name": nickname,
            "birthdate": "19900101",
            "agree_terms": True,
            "agree_privacy": True,
            "region": region,
        },
    )
    assert complete_resp.status_code == 200, f"complete-signup failed: {complete_resp.text}"
    return complete_resp.cookies["moaorder_token"]
