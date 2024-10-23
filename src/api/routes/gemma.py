import json
import os
import re
from sqlalchemy.orm import Session

from fastapi import APIRouter, Request
from dotenv import load_dotenv
from cachetools import TTLCache
from fastapi import Depends
from src.database.database import get_db
from src.database.models.database_model import Region

load_dotenv()
huggingfaceToken = os.getenv('HUGGINGFACE_TOKEN')

router = APIRouter()

# 캐시 설정
cache = TTLCache(maxsize=100, ttl=1800)
from transformers import AutoTokenizer, AutoModelForCausalLM

model_name = "basilry/gemma2-2-2b-it-fine-tuned-korean-real-estate-model"
# model_name = "google/gemma-2-9b-it"
tokenizer = AutoTokenizer.from_pretrained(model_name, use_auth_token=huggingfaceToken)
model = AutoModelForCausalLM.from_pretrained(model_name, use_auth_token=huggingfaceToken)


def get_initial_response(session_id):
    if session_id not in cache:
        return "안녕하세요! 저는 '두껍이'입니다! 어떤 것을 도와드릴까요?~두껍!"
    return None


# 프롬프트 캐싱 로직
def get_prompt(session_id):
    if session_id in cache:
        return cache[session_id]  # 캐시된 프롬프트 반환
    else:
        system_prompt = {
            "role": "system",
            "content": (
                "사용자가 입력한 한국어 문장을 분석하여 '지역', '매매 혹은 전세 여부', '현재, 과거, 미래 여부'를 파싱하십시오. "
                "파싱할 수 없는 경우에는 해당 필드에 'N'을 반환하십시오. "
                "유저의 질문에 해당하는 정보만을 추출하고, 임의로 답변을 생성하지 않습니다. "
                "한국어로 된 입력만을 처리하며, 응답은 간단하고 명확하게 이루어집니다."
            )
        }
        cache[session_id] = system_prompt
        return system_prompt


# DB에서 region_name_kor 유효성 검사
def validate_response(parsed_response: str, db: Session):
    try:
        # 문자열을 JSON으로 변환
        parsed_json = json.loads(parsed_response)
    except json.JSONDecodeError:
        # 만약 유효한 JSON 형식이 아니면 기본 에러를 반환
        return {"error": "유효하지 않은 JSON 형식입니다.", "raw_response": parsed_response}

    # '지역' 필드가 있는지 확인하고 유효성 검사
    if "지역" in parsed_json:
        region = db.query(Region).filter(Region.region_name_kor == parsed_json["지역"]).first()
        if region is None:
            parsed_json["지역"] = None

    return parsed_json


# 프롬프트 생성 및 입력 준비
def create_prompt(user_input, session_id):
    # 고정된 시스템 프롬프트 가져오기
    prompt = get_prompt(session_id)["content"]

    # 모델에게 전달할 프롬프트
    full_prompt = f"{prompt}\n다음은 유저가 한 질문입니다: {user_input}"
    return full_prompt, prompt  # 시스템 프롬프트도 반환하여 후처리에서 사용할 수 있게 함


# '/chat' API 핸들러
@router.post("/chat")
async def chat(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    user_input = data.get("message")
    session_id = data.get("session_id")

    print(f"사용자 입력: {user_input}")

    # 첫 번째 질문이면 고정된 응답 반환
    initial_response = get_initial_response(session_id)
    if len(session_id) == 0:
        return {"response": initial_response, "session_id": session_id}

    # 프롬프트 생성
    full_prompt, system_prompt = create_prompt(user_input, session_id)

    # 모델에 입력 전달
    inputs = tokenizer(full_prompt, return_tensors="pt")
    outputs = model.generate(
        inputs.input_ids,
        max_new_tokens=200,
        repetition_penalty=1.5,  # 반복 방지
        # top_p=0.8,  # 샘플링 설정
        do_sample=False
    )

    # 모델 응답 디코딩
    generated_response = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # 시스템 프롬프트 부분을 제거하여 유저 응답만 남기기
    cleaned_response = generated_response.replace(system_prompt, "").strip()

    # 패턴 제거
    cleaned_response = re.sub(r'질문:.*|답변:.*|예시:.*|보고서.*|응원합니다.*', '', cleaned_response)

    print(f"모델 응답: {cleaned_response}")

    # 필요시 추가 로직 적용
    validated_response = validate_response(cleaned_response, db)

    return {"response": cleaned_response, "session_id": session_id}
