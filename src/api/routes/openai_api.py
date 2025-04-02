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
        except Exception as e:
            print(f"OpenAI API 키 유효성 검증 실패: {e}")
            USE_MOCK_RESPONSES = True
    else:
        print("OpenAI API 사용이 비활성화되어 있습니다. 모의 응답을 사용합니다.")
        USE_MOCK_RESPONSES = True
except Exception as e:
    print(f"OpenAI 클라이언트 초기화 오류: {e}")
    USE_MOCK_RESPONSES = True

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

# 9. FastAPI '/chat' 엔드포인트
@router.post("/chat")
async def chat(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        user_input = data.get("message")
        session_id = data.get("session_id")

        print(f"사용자 입력: {user_input}")

        # 첫 번째 질문이면 고정된 응답 반환
        if len(session_id) == 0:
            initial_response = get_initial_response(session_id)
            print("최초응답", initial_response)

            return {"type": "text", "response": initial_response, "session_id": session_id}

        print("부동산 질문 처리 함수 호출")
        # 부동산 질문 처리 함수 호출
        response = handle_real_estate_question(user_input, session_id, db)

        print("최종 응답값", response)

        if isinstance(response, dict) and res_type == "price":
            try:
                # OpenAI 호출을 위한 데이터 구성
                if USE_MOCK_RESPONSES:
                    # 데이터베이스에서 가져온 실제 데이터 사용
                    formatted_data = response["formatted_price_data"]
                    region = response["region"]
                    analysis = response["analysis_summary"]
                    
                    # 모의 응답 생성시 실제 데이터 전달
                    mock_message = f"지역 {region}에 대한 분석 결과입니다~두껍!\n"
                    mock_message += f"데이터에 따르면, 해당 지역의 최근 부동산 가격 추이는 다음과 같습니다:\n"
                    mock_message += f"{formatted_data}\n\n"
                    mock_message += f"이 데이터를 기반으로 한 유의미한 통찰:\n"
                    mock_message += f"{analysis}~두껍!"
                    
                    # 모의 응답 객체 생성
                    final_response = type('obj', (object,), {
                        'choices': [
                            type('obj', (object,), {
                                'message': type('obj', (object,), {
                                    'content': mock_message
                                })
                            })
                        ]
                    })
                else:
                    final_response = client.chat.completions.create(
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
                            {"role": "user", "content": f"유저의 질문: {user_input}\n"
                             f"다음 데이터를 분석하여 한국어로 답변하세요:\n"
                             f"지역: {response['region']}\n"
                             f"가격 데이터:\n"
                             f"{response['formatted_price_data']}\n"},
                            {"role": "assistant", "content": f"지역 {response['region']}에 대한 분석 결과입니다~두껍!\n"
                             f"데이터에 따르면, 해당 지역의 최근 부동산 가격 추이는 다음과 같습니다:\n"
                             f"{response['formatted_price_data']}\n\n"
                             f"이 데이터를 기반으로 한 유의미한 통찰:\n"
                             f"{response['analysis_summary']}~두껍!"}
                        ]
                    )

                # 최종 응답 반환 - model_response 제거하고 요약 정보만 반환
                return {
                    "type": res_type,
                    "response": {
                        "region": response['region'],
                        "analysis_summary": response['analysis_summary'],
                        "date_range": f"{response['formatted_price_data'].split('날짜: ')[1].split(',')[0]} ~ {response['formatted_price_data'].split('날짜: ')[-1].split(',')[0]}",
                        "trend": "하락" if "하락" in response['analysis_summary'] else ("상승" if "상승" in response['analysis_summary'] else "안정"),
                        "deal_type": "매매" if "sale" in response['formatted_price_data'] else "전세",
                        "avg_price": response['avg_price']
                    },
                    "session_id": session_id
                }
            except Exception as e:
                print(f"최종 응답 생성 오류: {e}")
                # 오류 발생 시 기본 응답 반환
                return {
                    "type": res_type,
                    "response": {
                        "region": response['region'],
                        "analysis_summary": response['analysis_summary'],
                        "date_range": "최근 3개월",
                        "trend": "하락" if "하락" in response['analysis_summary'] else ("상승" if "상승" in response['analysis_summary'] else "안정"),
                        "deal_type": "매매" if "sale" in response['formatted_price_data'] else "전세",
                        "avg_price": response['avg_price']
                    },
                    "session_id": session_id
                }
        # 뉴스 혹은 일반 정보 처리
        return {"type": res_type, "response": response, "session_id": session_id}
    except Exception as e:
        print(f"API 엔드포인트 오류: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류가 발생했습니다: {str(e)}")

