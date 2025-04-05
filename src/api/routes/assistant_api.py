import os
from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from src.database.database import get_db
from src.api.services.assistants_service import AssistantService

# 환경 변수 로드
load_dotenv()

# FastAPI 라우터 초기화
router = APIRouter()

# API 요청 모델 정의
class AssistantChatRequest(BaseModel):
    message: str
    thread_id: str = None

# 스레드 ID를 저장하기 위한 세션 캐시
thread_cache = {}

# Assistant 서비스 초기화
try:
    assistant_service = AssistantService()
    assistant_info = assistant_service.get_assistant_info()
    print(f"OpenAI Assistant 연결 성공: {assistant_info['name']} (모델: {assistant_info['model']})")
except Exception as e:
    print(f"OpenAI Assistant 초기화 오류: {e}")
    assistant_service = None

@router.get("/info")
async def get_assistant_info():
    """
    현재 설정된 Assistant 정보를 반환합니다.
    """
    if not assistant_service:
        raise HTTPException(status_code=500, detail="Assistant 서비스가 초기화되지 않았습니다.")
    
    info = assistant_service.get_assistant_info()
    if not info:
        raise HTTPException(status_code=500, detail="Assistant 정보를 가져오는데 실패했습니다.")
    
    return info

@router.post("/chat")
async def assistant_chat(request: AssistantChatRequest, db: Session = Depends(get_db)):
    """
    Assistant API를 통해 사용자 메시지를 처리하고 응답합니다.
    """
    if not assistant_service:
        raise HTTPException(status_code=500, detail="Assistant 서비스가 초기화되지 않았습니다.")
    
    thread_id = request.thread_id
    user_message = request.message
    
    try:
        # Assistant에 질문하고 응답 받기
        response, new_thread_id = assistant_service.get_response(user_message, thread_id)
        
        return {
            "type": "assistant", 
            "response": response, 
            "thread_id": new_thread_id
        }
    except Exception as e:
        print(f"Assistant API 처리 오류: {e}")
        raise HTTPException(status_code=500, detail=f"처리 중 오류가 발생했습니다: {str(e)}") 