from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.database import check_db, close_db, init_db
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.services.upload_client import upload_client
from app.modules.announcements.router import router as announcements_router
from app.modules.announcements.admin import router as announcements_admin_router
from app.modules.banners.router import router as banners_router
from app.modules.banners.admin import router as banners_admin_router
from app.modules.ads.router import router as ads_router
from app.modules.ads.admin import router as ads_admin_router

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await upload_client.start()
    try:
        yield
    finally:
        await upload_client.close()
        await close_db()


app = FastAPI(
    title="Livetse Promotion Service",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    debug=False,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )


@app.get("/health/live", tags=["Health"], include_in_schema=False)
async def liveness():
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/health/ready", tags=["Health"], include_in_schema=False)
async def readiness():
    try:
        await check_db()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ready"}


app.include_router(announcements_router, prefix="/announcements")
app.include_router(announcements_admin_router, prefix="/announcements")
app.include_router(banners_router, prefix="/banners")
app.include_router(banners_admin_router, prefix="/banners")
app.include_router(ads_router, prefix="/ads")
app.include_router(ads_admin_router, prefix="/ads")
