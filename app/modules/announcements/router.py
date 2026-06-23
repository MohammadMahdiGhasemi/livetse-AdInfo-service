from fastapi import APIRouter

router = APIRouter(tags=["Announcements"])


@router.get("/")
async def get_announcements():
    return {"message": "Announcements endpoint"}
