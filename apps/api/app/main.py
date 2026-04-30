from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.auth import router as auth_router
from app.api.email_auth import router as email_auth_router
from app.api.checkout import router as checkout_router
from app.api.notifications import router as notifications_router
from app.api.orders import router as orders_router
from app.api.owner_orders import router as owner_orders_router
from app.api.dashboard import router as dashboard_router
from app.api.groups import router as groups_router
from app.api.health import router as health_router
from app.api.home import router as home_router
from app.api.onboarding import router as onboarding_router
from app.api.public import router as public_router
from app.api.stores import router as stores_router
from app.api.subscriptions import router as subscriptions_router
from app.api.uploads import router as uploads_router
from app.api.users import router as users_router
from app.api.webhooks import router as webhooks_router
from app.core.config import settings
from app.core.middleware import RequestIdMiddleware

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="모아오더 API", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(email_auth_router, prefix="/api")
app.include_router(onboarding_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(stores_router, prefix="/api")
app.include_router(subscriptions_router, prefix="/api")
app.include_router(groups_router, prefix="/api")
app.include_router(public_router, prefix="/api")
app.include_router(uploads_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(home_router, prefix="/api")
app.include_router(checkout_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(owner_orders_router, prefix="/api")
app.include_router(webhooks_router, prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "서버 내부 오류가 발생했습니다",
                "detail": None,
                "request_id": request_id,
            }
        },
    )
