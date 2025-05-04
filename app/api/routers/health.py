from fastapi import APIRouter

router = APIRouter()

@router.get("/", summary="Health check")
async def health_check() -> dict:
    """
    Эндпоинт для проверки «живости» сервера.
    Возвращает {"status": "ok"} при удачном подключении.
    """
    return {"status": "ok"}