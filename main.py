import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.database import init_db
from app.modules.announcements.router import router as announcements_router
from app.modules.announcements.admin import router as announcements_admin_router
from app.modules.banners.router import router as banners_router
from app.modules.banners.admin import router as banners_admin_router
from app.modules.ads.router import router as ads_router
from app.modules.ads.admin import router as ads_admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Livetse Promotion Service",
    lifespan=lifespan,
)

app.include_router(announcements_router, prefix="/announcements")
app.include_router(announcements_admin_router, prefix="/announcements")
app.include_router(banners_router, prefix="/banners")
app.include_router(banners_admin_router, prefix="/banners")
app.include_router(ads_router, prefix="/ads")
app.include_router(ads_admin_router, prefix="/ads")
