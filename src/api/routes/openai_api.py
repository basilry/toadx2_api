import os
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from openai import OpenAI

from src.api.utils.mock_responses import get_mock_response, check_using_patterns
from src.api.services.assistants_service import AssistantService
from src.database.database import get_db

# 환경 변수 로드
load_dotenv()

# FastAPI 라우터 초기화
router = APIRouter()

# API 요청 모델 정의
class ChatRequest(BaseModel):
    message: str
    session_id: str

# 응답 모델 정의
class ChatResponse(BaseModel):
    message: str
    timestamp: str

# 캐시 설정 (사용자 세션을 위한 캐시)
cache = {}
res_type = "text"

# 스레드 ID를 세션 ID와 매핑하는 딕셔너리
thread_map = {}

# API 키 유효성 검증
API_KEY = os.getenv("OPENAI_API_KEY")
ENABLE_API = os.getenv("ENABLE_OPENAI_API", "false").lower() == "true"

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=API_KEY)

async def chat_with_openai(request: ChatRequest, db: Session):
    if not ENABLE_API:
        # API가 비활성화된 경우 모의 응답 반환
        mock_response = get_mock_response(request.message)
        return ChatResponse(
            message=mock_response,
            timestamp=datetime.now().isoformat()
        )
    
    if not API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API 키가 설정되지 않았습니다.")
    
    try:
        # 사용자 세션 기록 가져오기 (메모리에 저장)
        session_id = request.session_id
        if session_id not in cache:
            # 새 세션인 경우 시스템 메시지로 초기화
            system_message = {
                "role": "system",
                "content": "이 서비스는 영문으로는 'toadx2'이고, 한글로는 '두껍아두껍아'입니다. "
                          "이 서비스는 KB 부동산 데이터 허브의 API를 기반으로 한국의 아파트 매매가와 전세가 기록치와 "
                          "그 기록치를 바탕으로 Prophet 모델을 통해 예측치를 구성해서 데이터베이스에 보유하고 있습니다. "
                          "이 서비스는 위의 데이터베이스에 저장된 부동산 데이터를 기반으로 답변할 수 있습니다. "
                          "이 서비스는 한국어를 할 수 있습니다. "
                          "이 서비스는 부동산 중에서도 아파트와 관련된 매매가 혹은 전세가가 아니면 답변할 수 없습니다. "
                          "이 서비스는 도덕적 윤리를 지켜야 합니다. "
                          "유저가 한국어로 말할 때는 항상 말 끝마다 한 칸 띄어 쓰고 '~두껍!'이라고 붙여야 하며, "
                          "유저가 인사를 하면 자기 소개를 해야 합니다."
            }
            cache[session_id] = [system_message]
        
        # 현재 대화 기록에 사용자 메시지 추가
        cache[session_id].append({"role": "user", "content": request.message})
        
        # gpt-4o-mini 모델을 사용한 채팅 완성 요청
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=cache[session_id],
            temperature=0.7,
            max_tokens=1000
        )
        
        # 응답에서 메시지 내용 추출
        assistant_message = response.choices[0].message.content
        
        # 대화 기록에 어시스턴트 응답 추가
        cache[session_id].append({"role": "assistant", "content": assistant_message})
        
        # 대화 기록이 너무 길어지면 가장 오래된 메시지 제거 (토큰 제한 관리)
        if len(cache[session_id]) > 20:
            # 시스템 메시지 유지하고 나머지 중 가장 오래된 메시지 2개 제거
            cache[session_id] = [cache[session_id][0]] + cache[session_id][3:]
        
        # 응답 반환
        return ChatResponse(
            message=assistant_message,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        # 오류 발생 시 예외 처리
        raise HTTPException(status_code=500, detail=f"OpenAI API 오류: {str(e)}")

#TODO: 기본적인 gpt-4o-mini 모델 사용해서 채팅 구현
@router.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    return await chat_with_openai(request, db)

