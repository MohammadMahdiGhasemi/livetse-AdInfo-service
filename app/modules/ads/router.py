from fastapi import APIRouter

router = APIRouter(tags=["Ads"])


@router.get("/")
async def get_ads():
    return {"message": "Ads endpoint"}
