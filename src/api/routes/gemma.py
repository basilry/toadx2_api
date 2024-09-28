from fastapi import APIRouter, HTTPException
from src.ml_models.gemma2_model import generate_response

router = APIRouter()


# GEMMA2 모델을 사용한 텍스트 예측 API
@router.post("/predict")
async def gemma2_predict(user_message: str):
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    messages = [
        {"role": "user", "content": user_message}
    ]

    # GEMMA2 모델로부터 예측된 응답 생성
    try:
        response = generate_response(messages)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in prediction: {str(e)}")
