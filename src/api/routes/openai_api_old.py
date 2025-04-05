import os
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from openai import OpenAI

from src.database.database import get_db
from src.api.utils.mock_responses import get_mock_response, check_using_patterns, get_conversation_response
from src.api.utils.parsers import fill_parsing_defaults, format_price_data, generate_analysis_summary
from src.api.services.property_service import get_property_price
from src.api.services.news_service import get_news_articles, google_search
from src.api.services.assistants_service import AssistantService

# 환경 변수 로드
load_dotenv()

# FastAPI 라우터 초기화
router = APIRouter()

# API 요청 모델 정의
class ChatRequest(BaseModel):
    message: str
    session_id: str

# 캐시 설정 (사용자 세션을 위한 캐시)
cache = {}
res_type = "text"

# 스레드 ID를 세션 ID와 매핑하는 딕셔너리
thread_map = {}

# API 키 유효성 검증
api_key = os.getenv("OPENAI_API_KEY")
enable_api = os.getenv("ENABLE_OPENAI_API", "false").lower() == "true"

# OpenAI 클라이언트 초기화
try:
    client = OpenAI(api_key=api_key)
    # API 키 유효성 테스트
    if enable_api:
        try:
            test_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            print(f"OpenAI API 키 유효성 검증 성공: {test_response.choices[0].message.content}")
            USE_MOCK_RESPONSES = False
            
            # Assistant 서비스 초기화 시도
            try:
                assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
                if assistant_id and assistant_id != "asst_YOUR_ASSISTANT_ID":
                    assistant_service = AssistantService(client=client, assistant_id=assistant_id)
                    assistant_info = assistant_service.get_assistant_info()
                    if assistant_info:
                        print(f"OpenAI Assistant 연결 성공: {assistant_info['name']} (모델: {assistant_info['model']})")
                        USE_ASSISTANT_API = True
                    else:
                        print("Assistant 정보를 가져오는데 실패했습니다. Chat Completion API를 사용합니다.")
                        USE_ASSISTANT_API = False
                else:
                    print("OPENAI_ASSISTANT_ID가 설정되지 않았습니다. Chat Completion API를 사용합니다.")
                    USE_ASSISTANT_API = False
            except Exception as e:
                print(f"Assistant 초기화 오류: {e}. Chat Completion API를 사용합니다.")
                USE_ASSISTANT_API = False
                
        except Exception as e:
            print(f"OpenAI API 키 유효성 검증 실패: {e}")
            USE_MOCK_RESPONSES = True
            USE_ASSISTANT_API = False
    else:
        print("OpenAI API 사용이 비활성화되어 있습니다. 모의 응답을 사용합니다.")
        USE_MOCK_RESPONSES = True
        USE_ASSISTANT_API = False
except Exception as e:
    print(f"OpenAI 클라이언트 초기화 오류: {e}")
    USE_MOCK_RESPONSES = True
    USE_ASSISTANT_API = False

# 1. 초기 응답 반환 함수
def get_initial_response(session_id):
    if session_id not in cache:
        return "안녕하세요! 저는 '두껍이'입니다! 어떤 것을 도와드릴까요?~두껍!"
    return None

# 2. 질문 유형 확인하는 함수 (OpenAI API 또는 패턴 매칭 사용)
def gemini_api_confirm_question_kind(text: str):
    global res_type
    
    try:
        # API 호출을 할지 결정 (USE_MOCK_RESPONSES가 False인 경우만 실제 API 호출)
        try_api_call = not USE_MOCK_RESPONSES and os.getenv("ENABLE_OPENAI_API", "false").lower() == "true"
        
        if try_api_call:
            print("API 호출 시도")
            print(text)
            try:
                # OpenAI를 사용하여 질문 유형 확인
                question_kind_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "부동산 관련 질문이면 Y로 대답해주고, 아니면 무조건 N으로 대답해줘"},
                        {"role": "user", "content": text}
                    ]
                )
                
                question_kind = question_kind_response.choices[0].message.content.strip()
                print("질문 유형 확인 결과", question_kind)

                if question_kind == "N":
                    return "N"
                
                # 질문이 PRICE인지 INFO인지 판단
                try:
                    followup_response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "유저의 질문이 부동산 매매가, 전세가 등 '정형적 가격'에 대한 질문이면 'PRICE'를 대답해줘"
                            "유저의 질문이 부동산 정보, 뉴스, 전망 등 '비정형적 내용'에 대한 질문이면 'INFO'로 대답해줘"},
                            {"role": "user", "content": f"유저의 질문: {text}"}
                        ]
                    )
                    
                    followup_kind = followup_response.choices[0].message.content.strip()
                    res_type = "text"
                    return followup_kind
                    
                except Exception as e:
                    print(f"후속 질문 API 호출 오류: {e}")
                    # 후속 질문 API 오류 시 기본값으로 PRICE 반환
                    res_type = "text"
                    return "PRICE"  # 기본적으로 PRICE로 처리
                
            except Exception as e:
                print(f"질문 분류 API 호출 오류: {e}")
                # 패턴 매칭 기반으로 처리
                first_check = check_using_patterns(text.lower())
                
                if first_check == "N":
                    return "N"
                else:
                    # 부동산 관련 키워드 확인하여 PRICE/INFO 구분
                    price_keywords = ["매매", "전세", "가격", "시세", "얼마", "값", "비용", 
                                    "아파트", "집값", "부동산", "가격대", "평균", "중간값", "중위값"]
                    info_keywords = ["뉴스", "전망", "동향", "투자", "추세", "호재", "악재", 
                                    "이슈", "정책", "법률", "규제", "완화", "변화", "예측", "향후"]
                    
                    text_lower = text.lower()
                    if any(keyword in text_lower for keyword in price_keywords):
                        return "PRICE"
                    elif any(keyword in text_lower for keyword in info_keywords):
                        return "INFO"
                    
                    return "PRICE"  # 기본값
        else:
            # 패턴 매칭 기반으로 진행
            first_check = check_using_patterns(text.lower())
            
            if first_check == "N":
                return "N"
            else:
                # 부동산 관련 키워드 확인하여 PRICE/INFO 구분
                price_keywords = ["매매", "전세", "가격", "시세", "얼마", "값", "비용", 
                                "아파트", "집값", "부동산", "가격대", "평균", "중간값", "중위값"]
                info_keywords = ["뉴스", "전망", "동향", "투자", "추세", "호재", "악재", 
                                "이슈", "정책", "법률", "규제", "완화", "변화", "예측", "향후"]
                
                text_lower = text.lower()
                if any(keyword in text_lower for keyword in price_keywords):
                    return "PRICE"
                elif any(keyword in text_lower for keyword in info_keywords):
                    return "INFO"
                
                return "PRICE"  # 기본값
        
    except Exception as e:
        print(f"질문 처리 전체 오류: {e}")
        # 오류 발생 시 기본값 반환
        res_type = "text"
        return "PRICE"  # 기본적으로 PRICE로 처리

# 8. 수정된 부동산 질문 핸들러
def handle_real_estate_question(user_input, session_id, db: Session):
    global res_type
    try:
        # 질문 유형 확인
        kind = gemini_api_confirm_question_kind(user_input)
        print("부동산 관련 질문 여부 확인", kind)

        # 질문이 부동산과 관련 없는 경우
        if kind == "N":
            res_type = "conversation"  # 일반 대화는 conversation 타입으로 설정
            try:
                if USE_MOCK_RESPONSES:
                    response = get_mock_response([
                        {"role": "system", "content": "이 서비스는 영문으로는 'toadx2'이고, 한글로는 '두껍아두껍아'입니다. "
                        "이 서비스는 KB 부동산 데이터 허브의 API를 기반으로 한국의 아파트 매매가와 전세가 기록치와 "
                        "그 기록치를 바탕으로 Prophet 모델을 통해 예측치를 구성해서 데이터베이스에 보유하고 있습니다. "
                        "이 서비스는 위의 데이터베이스에 저장된 부동산 데이터를 기반으로 답변할 수 있습니다. "
                        "이 서비스는 한국어를 할 수 있습니다. "
                        "이 서비스는 부동산 중에서도 아파트와 관련된 매매가 혹은 전세가가 아니면 답변할 수 없습니다. "
                        "이 서비스는 도덕적 윤리를 지켜야 합니다. "
                        "유저가 한국어로 말할 때는 항상 말 끝마다 한 칸 띄어 쓰고 '~두껍!'이라고 붙여야 하며, "
                        "유저가 영어로 말할 때는 항상 말 끝마다 '~ribbit!'이라고 붙여야 합니다."
                        "유저가 인사를 하면 자기 소개를 해야 합니다."},
                        {"role": "user", "content": f"유저의 질문: {user_input}"}
                    ])
                else:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "이 서비스는 영문으로는 'toadx2'이고, 한글로는 '두껍아두껍아'입니다. "
                            "이 서비스는 KB 부동산 데이터 허브의 API를 기반으로 한국의 아파트 매매가와 전세가 기록치와 "
                            "그 기록치를 바탕으로 Prophet 모델을 통해 예측치를 구성해서 데이터베이스에 보유하고 있습니다. "
                            "이 서비스는 위의 데이터베이스에 저장된 부동산 데이터를 기반으로 답변할 수 있습니다. "
                            "이 서비스는 한국어를 할 수 있습니다. "
                            "이 서비스는 부동산 중에서도 아파트와 관련된 매매가 혹은 전세가가 아니면 답변할 수 없습니다. "
                            "이 서비스는 도덕적 윤리를 지켜야 합니다. "
                            "유저가 한국어로 말할 때는 항상 말 끝마다 한 칸 띄어 쓰고 '~두껍!'이라고 붙여야 하며, "
                            "유저가 영어로 말할 때는 항상 말 끝마다 '~ribbit!'이라고 붙여야 합니다."
                            "유저가 인사를 하면 자기 소개를 해야 합니다."},
                            {"role": "user", "content": f"유저의 질문: {user_input}"}
                        ]
                    )
                
                return response.choices[0].message.content
            except Exception as e:
                print(f"OpenAI API 오류: {e}")
                return "죄송합니다. 지금은 서비스 이용이 어렵습니다. 잠시 후 다시 시도해주세요~두껍!"

        print(2222)

        # 파싱 응답
        try:
            if USE_MOCK_RESPONSES:
                parsed_result_response = get_mock_response([
                    {"role": "system", "content": "모든 응답은 반드시 한국어로 작성되어야 합니다. 다음 유저의 질문을 파싱하여 지침에 따라 답변하세요."
                    "특수문자는 넣지말고, key-value는 콜론으로 구분하세요"
                    "각 값은 쉼표로 구분하세요"
                    "파싱 결과:\n"
                    "지역: [지역명을 여기에만 입력하세요],\n"
                    "매매/전세 여부: [매매 or 전세를 명시하세요],\n"
                    "시간 정보: [시간 정보를 여기에만 입력하세요]\n"},
                    {"role": "user", "content": f"유저의 질문: {user_input}"}
                ])
            else:
                parsed_result_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "모든 응답은 반드시 한국어로 작성되어야 합니다. 다음 유저의 질문을 파싱하여 지침에 따라 답변하세요."
                        "특수문자는 넣지말고, key-value는 콜론으로 구분하세요"
                        "각 값은 쉼표로 구분하세요"
                        "파싱 결과:\n"
                        "지역: [지역명을 여기에만 입력하세요],\n"
                        "매매/전세 여부: [매매 or 전세를 명시하세요],\n"
                        "시간 정보: [시간 정보를 여기에만 입력하세요]\n"},
                        {"role": "user", "content": f"유저의 질문: {user_input}"}
                    ]
                )
            
            parsed_text = parsed_result_response.choices[0].message.content
            print("모델 응답결과 :", parsed_text)
        except Exception as e:
            print(f"파싱 API 오류: {e}")
            parsed_text = "지역: 서울, 매매/전세 여부: 매매, 시간 정보: 현재"
        
        # 텍스트 추출 및 파싱
        parsed_result = fill_parsing_defaults(parsed_text)
        print("전세/매매가 여부 파싱", parsed_result)

        # 질문이 매매가/전세가 관련일 경우
        if kind == "PRICE":
            region = parsed_result.get("지역", "전국")
            deal_type = parsed_result.get("매매/전세 여부", "매매")
            date_info = parsed_result.get("시간 정보", "현재")

            print("매매가 안쪽", region, deal_type, date_info)

            try:
                # 매매가/전세가 DB 조회
                price_data, avg_price = get_property_price(region, deal_type, date_info, db)
                print("매매가 데이터 조회 결과", price_data)
                if not price_data:
                    return "데이터를 찾을 수 없습니다~두껍!"

                # 데이터 포맷팅 및 요약 생성
                formatted_price_data = format_price_data(region, price_data)
                analysis_summary = generate_analysis_summary(price_data)

                print(price_data)
                res_type = "price"

                return {
                    "region": region,
                    "formatted_price_data": formatted_price_data,
                    "analysis_summary": analysis_summary,
                    "avg_price": avg_price
                }
            except Exception as e:
                print(f"데이터 처리 오류: {e}")
                return f"데이터 처리 중 오류가 발생했습니다~두껍! ({str(e)})"

        # 질문이 정보/뉴스 관련일 경우
        elif kind == "INFO":
            region_name = parsed_result["지역"] or "전국"

            try:
                # 뉴스 DB 조회
                news_data = get_news_articles(region_name, db)
                if not news_data:
                    # 구글 검색으로 대체
                    search_results = google_search(user_input)
                    if search_results:
                        res_type = "news"

                        return {
                            "region": region_name,
                            "news": search_results
                        }
                    return "관련 뉴스 및 정보를 찾을 수 없습니다.~두껍!"

                res_type = "info"

                return news_data
            except Exception as e:
                print(f"뉴스 데이터 처리 오류: {e}")
                return "뉴스 정보를 가져오는 중 오류가 발생했습니다~두껍!"

        # 부동산 관련이 아니면 고정된 프롬프트로 reject
        return "부동산 관련 질문만 대답할 수 있습니다!~두껍!"
    except Exception as e:
        print(f"질문 처리 중 오류 발생: {e}")
        return "죄송합니다. 현재 서비스에 문제가 있습니다. 잠시 후 다시 시도해주세요~두껍!"

# 함수 추가: 질문 유형 확인
def check_question_type(message):
    """
    사용자의 질문이 부동산 가격 관련인지, 일반 정보 관련인지, 혹은 그 외인지 확인합니다.
    """
    # 패턴으로 확인
    if check_using_patterns(message):
        # 가격 여부 확인 (가격, 얼마, 원, 시세 등의 용어로 판단)
        price_keywords = ["가격", "시세", "매매가", "전세가", "얼마", "원", "만원", "억"]
        for keyword in price_keywords:
            if keyword in message:
                return "PRICE"
        
        # 가격 관련 키워드가 없으면 일반 부동산 정보로 분류
        return "INFO"
    
    # 패턴에 해당하지 않으면 부동산 관련 질문이 아님
    return "N"

# 함수 추가: 비부동산 질문 처리
def handle_non_real_estate_question(message):
    """
    부동산 관련이 아닌 일반 질문을 처리합니다.
    """
    if USE_MOCK_RESPONSES:
        return "죄송합니다. 저는 부동산 정보만 안내해드릴 수 있습니다~두껍!"
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "이 서비스는 영문으로는 'toadx2'이고, 한글로는 '두껍아두껍아'입니다. "
                 "이 서비스는 KB 부동산 데이터 허브의 API를 기반으로 한국의 아파트 매매가와 전세가 기록치와 "
                 "그 기록치를 바탕으로 Prophet 모델을 통해 예측치를 구성해서 데이터베이스에 보유하고 있습니다. "
                 "이 서비스는 위의 데이터베이스에 저장된 부동산 데이터를 기반으로 답변할 수 있습니다. "
                 "이 서비스는 한국어를 할 수 있습니다. "
                 "이 서비스는 부동산 중에서도 아파트와 관련된 매매가 혹은 전세가가 아니면 답변할 수 없습니다. "
                 "이 서비스는 도덕적 윤리를 지켜야 합니다. "
                 "유저가 한국어로 말할 때는 항상 말 끝마다 한 칸 띄어 쓰고 '~두껍!'이라고 붙여야 하며, "
                 "유저가 영어로 말할 때는 항상 말 끝마다 '~ribbit!'이라고 붙여야 합니다. "
                 "모든 문장은 자연스러운 띄어쓰기를 적용하고, 가독성을 높이는 방식으로 작성해야 합니다."},
                {"role": "user", "content": message}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"비부동산 질문 처리 오류: {e}")
        return "죄송합니다. 부동산 정보만 안내해드릴 수 있습니다~두껍!"

# 9. FastAPI '/chat' 엔드포인트
@router.post("/chat")
async def chat(chat_request: ChatRequest, db: Session = Depends(get_db)):
    message = chat_request.message
    session_id = chat_request.session_id

    # 사용자의 세션 ID가 캐시에 없으면 초기화
    if session_id not in cache:
        cache[session_id] = {"messages": [], "confirmed": False, "kind": None}

    # 메시지가 비어있으면 에러 응답
    if not message:
        return {"type": "error", "response": "메시지가 비어있습니다."}

    # 입력 메시지 추가
    cache[session_id]["messages"].append({"role": "user", "content": message})

    # 어시스턴트 API가 활성화되어 있고, 질문이 부동산과 관련 없거나 Assistant API를 사용하도록 설정된 경우
    if USE_ASSISTANT_API:
        # 세션 ID에 대응하는 스레드 ID가 없으면 새로 생성
        if session_id not in thread_map:
            thread = assistant_service.create_thread()
            thread_map[session_id] = thread.id
        
        thread_id = thread_map[session_id]
        
        # 부동산 관련 질문이 아닌 경우
        if cache[session_id]["kind"] == "N":
            response = assistant_service.send_message(thread_id, message)
            return {"type": "assistant", "response": response["content"][0].text.value}
    
    # 부동산 관련 질문인지 확인
    if not cache[session_id]["confirmed"]:
        question_type = check_question_type(message)
        # 부동산 관련 질문이 아닌 경우
        if question_type == "N":
            cache[session_id]["kind"] = "N"
            cache[session_id]["confirmed"] = True
            
            # Assistant API 사용이 활성화된 경우 Assistant로 응답
            if USE_ASSISTANT_API:
                thread_id = thread_map[session_id]
                response = assistant_service.send_message(thread_id, message)
                return {"type": "assistant", "response": response["content"][0].text.value}
            
            # 모의 응답 또는 OpenAI API 사용
            response = handle_non_real_estate_question(message)
            return {"type": "assistant", "response": response}
            
        # 부동산 관련 질문인 경우
        cache[session_id]["kind"] = question_type
        cache[session_id]["confirmed"] = True
        
    # 부동산 가격 관련 질문 처리
    if cache[session_id]["kind"] == "PRICE":
        try:
            # 파싱
            parsing_result = parse_user_input(message)
            region = parsing_result.get("region", "")
            deal_type = parsing_result.get("deal_type", "")
            date_info = parsing_result.get("date_info", "")
            
            # 기본값 설정
            result = fill_parsing_defaults(parsing_result)
            region = result["region"]
            deal_type = result["deal_type"]
            date_info = result["date_info"]
            
            # 부동산 가격 데이터 조회
            price_data = get_property_price(db, region, deal_type, date_info)
            if not price_data or len(price_data) == 0:
                return {"type": "error", "response": f"{region}의 {deal_type} 데이터를 찾을 수 없습니다."}
            
            # 데이터 포맷팅
            formatted_data = format_price_data(price_data)
            avg_price = formatted_data["avg_price"]
            start_date = formatted_data["start_date"]
            end_date = formatted_data["end_date"]
            trend = formatted_data["trend"]
            
            # 분석 요약 생성
            analysis_summary = generate_analysis_summary(formatted_data)
            
            # 최종 응답 생성 (Assistant API 사용 또는 일반 응답)
            if USE_ASSISTANT_API:
                try:
                    thread_id = thread_map[session_id]
                    
                    # 어시스턴트에게 구조화된 데이터 제공
                    context_message = f"""
                    부동산 가격 정보에 대한 질문입니다. 다음 정보를 바탕으로 친절하게 응답해주세요:
                    - 지역: {region}
                    - 거래 유형: {deal_type}
                    - 기간: {start_date}부터 {end_date}까지
                    - 평균 가격: {avg_price}
                    - 가격 추세: {trend}
                    - 분석 요약: {analysis_summary}
                    
                    사용자 원래 질문: {message}
                    """
                    
                    response = assistant_service.send_message(thread_id, context_message)
                    return {
                        "type": "assistant",
                        "response": response["content"][0].text.value,
                        "region": region,
                        "analysis_summary": analysis_summary,
                        "date_range": f"{start_date} ~ {end_date}",
                        "trend": trend,
                        "deal_type": deal_type,
                        "avg_price": avg_price
                    }
                except Exception as e:
                    print(f"Assistant API 응답 생성 오류: {e}")
                    # 오류 발생 시 기존 방식으로 응답 생성
            
            # 기존 방식으로 응답 생성
            return {
                "type": "assistant",
                "response": get_mock_response(message, region, deal_type, avg_price, trend, formatted_data),
                "region": region,
                "analysis_summary": analysis_summary,
                "date_range": f"{start_date} ~ {end_date}",
                "trend": trend,
                "deal_type": deal_type,
                "avg_price": avg_price
            }
            
        except Exception as e:
            print(f"부동산 가격 응답 생성 오류: {e}")
            return {"type": "error", "response": f"응답을 생성하는 중 오류가 발생했습니다: {e}"}
    
    # 부동산 정보 관련 질문 처리
    elif cache[session_id]["kind"] == "INFO":
        try:
            # 파싱
            parsing_result = parse_user_input(message)
            region = parsing_result.get("region", "")
            
            # 기본값 설정
            result = fill_parsing_defaults(parsing_result)
            region = result["region"]
            
            # 뉴스 기사 조회
            news_data = get_news_articles(region)
            if not news_data or len(news_data) == 0:
                return {"type": "error", "response": f"{region}의 부동산 관련 뉴스를 찾을 수 없습니다."}
            
            # 구글 검색 수행
            search_results = google_search(f"{region} 부동산 시장")
            
            # 뉴스 및 검색 결과 결합
            combined_data = {
                "news": news_data[:3],  # 상위 3개 뉴스만 사용
                "search": search_results[:3]  # 상위 3개 검색 결과만 사용
            }
            
            # 최종 응답 생성 (Assistant API 사용 또는 일반 응답)
            if USE_ASSISTANT_API:
                try:
                    thread_id = thread_map[session_id]
                    
                    # 뉴스 항목 포맷팅
                    news_items = "\n".join([f"- {item['title']} ({item['date']}): {item['summary']}" for item in combined_data["news"]])
                    
                    # 검색 결과 포맷팅
                    search_items = "\n".join([f"- {item['title']}: {item['snippet']}" for item in combined_data["search"]])
                    
                    # 어시스턴트에게 구조화된 데이터 제공
                    context_message = f"""
                    부동산 정보에 대한 질문입니다. 다음 정보를 바탕으로 친절하게 응답해주세요:
                    - 지역: {region}
                    
                    최근 뉴스:
                    {news_items}
                    
                    관련 정보:
                    {search_items}
                    
                    사용자 원래 질문: {message}
                    """
                    
                    response = assistant_service.send_message(thread_id, context_message)
                    return {
                        "type": "assistant",
                        "response": response["content"][0].text.value,
                        "region": region
                    }
                except Exception as e:
                    print(f"Assistant API 응답 생성 오류: {e}")
                    # 오류 발생 시 기존 방식으로 응답 생성
            
            # 기존 방식으로 응답 생성
            return {
                "type": "assistant",
                "response": get_conversation_response(message, region, combined_data),
                "region": region
            }
            
        except Exception as e:
            print(f"부동산 정보 응답 생성 오류: {e}")
            return {"type": "error", "response": f"응답을 생성하는 중 오류가 발생했습니다: {e}"}
    
    # 기타 질문 처리
    else:
        response = handle_non_real_estate_question(message)
        return {"type": "assistant", "response": response}

