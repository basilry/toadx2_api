import os
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from fastapi import APIRouter, HTTPException, Request
from dotenv import load_dotenv
from cachetools import TTLCache

load_dotenv()
huggingfaceToken = os.getenv('HUGGINGFACE_TOKEN')

router = APIRouter()

# 캐시 설정
cache = TTLCache(maxsize=100, ttl=1800)

# # 모델 및 토크나이저 로드 (Google Drive 경로 설정)
# tokenizer = AutoTokenizer.from_pretrained("/content/drive/MyDrive/gemma2-2-2b-it-fine-tuned-korean-model")
# model = AutoModelForCausalLM.from_pretrained("/content/drive/MyDrive/gemma2-2-2b-it-fine-tuned-korean-model")
#
# # 프롬프트 캐싱 로직
# def get_prompt(session_id):
#     if session_id in cache:
#         return cache[session_id]  # 캐시된 프롬프트 반환
#     else:
#         system_prompt = {
#             "role": "system",
#             "content": (
#                 "이 서비스는 영문으로는 'toadx2'이고, 한글로는 '두껍아두껍아'입니다. "
#                 "이 서비스는 KB 부동산 데이터 허브의 API를 기반으로 한국의 아파트 매매가와 전세가 기록치와 "
#                 "그 기록치를 바탕으로 Prophet 모델을 통해 예측치를 구성해서 데이터베이스에 보유하고 있습니다. "
#                 "이 서비스는 위의 데이터베이스에 저장된 부동산 데이터를 기반으로 답변할 수 있습니다. "
#                 "이 서비스는 한국어를 할 수 있습니다. "
#                 "이 서비스는 Google's Gemma2-2-2b-it 모델을 기반으로 하고 있습니다. "
#                 "이 서비스는 부동산 중에서도 아파트와 관련된 매매가 혹은 전세가가 아니면 답변할 수 없습니다. "
#                 "이 서비스는 도덕적 윤리를 지켜야 합니다. "
#                 "유저가 한국어로 말할 때는 항상 말 끝마다 '~두껍!'이라고 붙여야 하며, "
#                 "유저가 영어로 말할 때는 항상 말 끝마다 '~ribbit!'이라고 붙여야 합니다."
#             )
#         }
#         cache[session_id] = system_prompt
#         return system_prompt


# 자연어 파라미터 처리 함수
def extract_parameters(question: str):
    # 부동산 관련 키워드가 있는지 확인하고 파라미터 추출
    if "아파트" in question and ("매매" in question or "전세" in question):
        return "estate"
    return "normal"


# '/chat' API: 메인 요청 핸들러
@router.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data.get("message")
    session_id = data.get("session_id")

    print(request)
    print(data, user_input, session_id)

    # 질문에서 파라미터 추출
    question_type = extract_parameters(user_input)

    # 부동산 관련 질문이면 처리, 그렇지 않으면 일반 질문 처리
    if question_type == "estate":
        # prompt = get_prompt(session_id)
        response = f"서울 강남구의 최근 매매가는 12억입니다~두껍!"
    else:
        # prompt = get_prompt(session_id)
        prompt = ''
        # response = f"{prompt['content']} {user_input} ~두껍!"

    # return {"response": response, "session_id": session_id}
    return {"message": "Chat response"}
