from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_real_estate_data():
    # 부동산 관련 데이터를 반환하는 로직
    return {"data": "Real estate data"}
