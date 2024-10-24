import os
import google.generativeai as genai
from fastapi import APIRouter, Request, Depends
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from src.database.database import get_db
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain import LLMChain, PromptTemplate
from langchain.llms import HuggingFacePipeline
from langchain.memory import ConversationBufferMemory

# 환경 변수 로드
load_dotenv()
huggingfaceToken = os.getenv('HUGGINGFACE_TOKEN')

# FastAPI 라우터 초기화
router = APIRouter()

# LangChain 메모리 설정 (대화 기록 관리)
memory = ConversationBufferMemory()

# 캐시 설정 (사용자 세션을 위한 캐시)
cache = {}


# 1. Gemini API로 질문 여부 확인
def gemini_api_confirm_question_kind(text: str):
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    response = gemini_model.generate_content(f"부동산 관련 질문이면 Y로 대답해주고, 아니면 N으로 대답해줘: {text}")

    return response.text.strip()


# 2. 파인튜닝된 Gemma2 모델을 LangChain에 연결
model_name = "basilry/gemma2-2-2b-it-fine-tuned-korean-real-estate-model"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)
hf_pipeline = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=200,  # 원하는 값으로 설정하세요.
    pad_token_id=tokenizer.eos_token_id  # 필요 시 EOS 토큰 설정
)
llm = HuggingFacePipeline(pipeline=hf_pipeline)

# 3. 고정된 파싱 프롬프트 생성 (LangChain의 PromptTemplate 사용)
parsing_prompt_template = PromptTemplate(
    input_variables=["input_text"],
    template=("""
        질문: {input_text}\n
        파싱 결과:\n
        지역: [지역명을 여기에만 입력하세요]\n
        매매/전세 여부: [매매 or 전세를 명시하세요]\n
        시간 정보: [시간 정보를 여기에만 입력하세요]\n
        """
    )
)

# 4. 파싱을 위한 LLMChain 설정 (Gemma2 모델 사용)
parsing_chain = LLMChain(
    llm=llm,
    prompt=parsing_prompt_template,
    # memory=memory  # 멀티턴 대화를 위한 메모리 사용
)


# 5. 시스템 프롬프트 생성 함수 (Gemini API에 보낼 프롬프트)
def get_gemini_system_prompt(session_id):
    system_prompt = (
        "이 서비스는 영문으로는 'toadx2'이고, 한글로는 '두껍아두껍아'입니다. "
        "이 서비스는 KB 부동산 데이터 허브의 API를 기반으로 한국의 아파트 매매가와 전세가 기록치와 "
        "그 기록치를 바탕으로 Prophet 모델을 통해 예측치를 구성해서 데이터베이스에 보유하고 있습니다. "
        "이 서비스는 위의 데이터베이스에 저장된 부동산 데이터를 기반으로 답변할 수 있습니다. "
        "이 서비스는 한국어를 할 수 있습니다. "
        "이 서비스는 Google's Gemma-2-2b-it 모델을 기반으로 하고 있습니다. "
        "이 서비스는 부동산 중에서도 아파트와 관련된 매매가 혹은 전세가가 아니면 답변할 수 없습니다. "
        "이 서비스는 도덕적 윤리를 지켜야 합니다. "
        "유저가 한국어로 말할 때는 항상 말 끝마다 '~두껍!'이라고 붙여야 하며, "
        "유저가 영어로 말할 때는 항상 말 끝마다 '~ribbit!'이라고 붙여야 합니다."
    )
    return system_prompt


# 6. 초기 응답 (세션별 캐싱된 환영 메시지)
def get_initial_response(session_id):
    if session_id not in cache:
        return "안녕하세요! 저는 '두껍이'입니다! 어떤 것을 도와드릴까요?~두껍!"
    return None


# 7. 부동산 질문 핸들러
def handle_real_estate_question(user_input, session_id, db: Session):
    # 1단계: Gemini API로 질문 유형 확인
    kind = gemini_api_confirm_question_kind(user_input)

    print(kind)

    if kind == "N":
        return "저는 대한민국의 아파트와 관련된 내용만 이야기 할 수 있어요!~두껍!"

    # 2단계: Gemma2 모델로 파싱 (LLMChain 사용)
    parsed_result = parsing_chain.run(input_text=user_input)

    print(parsed_result)

    # # 3단계: DB 및 API 조회 후 결과 처리 (DB 조회 및 국토교통부 API 호출 로직 추가 가능)
    # # 이 부분에 DB 또는 OpenAPI를 통해 실시간 데이터를 조회하는 로직을 추가할 수 있습니다.
    #
    # # 4단계: Gemini API로 최종 멀티턴 대화 생성
    # system_prompt = get_gemini_system_prompt(session_id)
    # chat_history = memory.load_memory_variables(session_id)  # 대화 기록 가져오기
    #
    # genai_response = genai.GenerativeModel('gemini-1.5-flash').generate_content(
    #     system_prompt + "\n".join(chat_history)
    # )
    #
    # # 최종 응답 반환
    # return genai_response.text.strip()


# 8. FastAPI '/chat' 엔드포인트
@router.post("/chat")
async def chat(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    user_input = data.get("message")
    session_id = data.get("session_id")

    print(f"사용자 입력: {user_input}")

    # 첫 번째 질문이면 고정된 응답 반환
    initial_response = get_initial_response(session_id)
    print(initial_response)
    if len(session_id) == 0:
        return {"response": initial_response, "session_id": session_id}

    print(111)
    # 부동산 질문 처리 함수 호출
    response = handle_real_estate_question(user_input, session_id, db)

    # 최종 응답 반환
    return {"response": response, "session_id": session_id}


#
# # 시스템 프롬프트 캐싱 로직 (Gemini API로 보낼 프롬프트)
# def get_gemini_system_prompt(session_id):
#     if session_id in cache:
#         return cache[session_id]
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
#
#
#
# # 멀티턴 대화 상태를 관리하는 함수
# def handle_multi_turn_conversation(user_input, session_id, chat_history):
#     if session_id not in chat_history:
#         chat_history[session_id] = []  # 세션별로 대화 기록 초기화
#
#     # 새로운 유저 입력 추가
#     chat_history[session_id].append({"role": "user", "content": user_input})
#
#     return chat_history
#
#
# # '/chat' API 핸들러
# @router.post("/chat")
# async def chat(request: Request, db: Session = Depends(get_db)):
#     data = await request.json()
#     user_input = data.get("message")
#     session_id = data.get("session_id")
#
#     # 대화 기록을 관리할 dictionary (멀티턴 대화를 위해 사용)
#     chat_history = {}
#
#     print(f"사용자 입력: {user_input}")
#
#     # 첫 번째 질문이면 고정된 응답 반환
#     initial_response = get_initial_response(session_id)
#     if len(session_id) == 0:
#         return {"response": initial_response, "session_id": session_id}
#
#     # 부동산 질문 여부 파악
#     kind = gemini_api_confirm_question_kind(user_input)
#
#     if kind == "N":
#         print("부동산 관련 질문이 아닙니다.")
#         return {"response": "나는 대한민국 아파트와 관련된 내용만 이야기 할 수 있다~두껍!", "session_id": session_id}
#
#     # 고정 파싱 프롬프트 생성
#     parsing_prompt = generate_parsing_prompt(user_input)
#
#     # 모델에 입력 전달 (파싱 역할 수행)
#     inputs = tokenizer(parsing_prompt, return_tensors="pt")
#     outputs = model.generate(
#         inputs.input_ids,
#         max_new_tokens=200,
#         repetition_penalty=1.5,  # 반복 방지
#         do_sample=False
#     )
#
#     # 모델 응답 디코딩
#     generated_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
#
#     print(f"파싱된 응답: {generated_response}")
#
#     # 멀티턴 대화 처리
#     chat_history = handle_multi_turn_conversation(user_input, session_id, chat_history)
#
#     # Gemini API에 보낼 시스템 프롬프트 생성
#     system_prompt = get_gemini_system_prompt(session_id)["content"]
#
#     # 최종 대화 기록을 포함하여 Gemini API로 보냄
#     gemini_response = genai.GenerativeModel('gemini-1.5-flash').generate_content(
#         system_prompt + "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history[session_id]])
#     )
#
#     return {"response": gemini_response.text.strip(), "session_id": session_id}
