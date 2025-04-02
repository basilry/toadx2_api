import os
import re
import json
from datetime import datetime, timedelta

import requests
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from src.database.database import get_db
from src.database.models.database_model import PropertyPriceData, Prediction, NewsArticle, Region
from sqlalchemy import select, func, or_
from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessage

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

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 테스트 모드 설정 (API 호출 없이 테스트 가능)
USE_MOCK_RESPONSES = True

# 0. 모의 응답 생성 함수 (테스트용)
def get_mock_response(messages, model="gpt-3.5-turbo"):
    system_msg = next((m for m in messages if m.get("role") == "system"), None)
    user_msg = next((m for m in messages if m.get("role") == "user"), None)
    
    # API 호출을 할지 결정 (USE_MOCK_RESPONSES가 False인 경우만 실제 API 호출)
    try_api_call = not USE_MOCK_RESPONSES and os.getenv("ENABLE_OPENAI_API", "false").lower() == "true"
    
    # 부동산 관련 질문 여부 확인
    if system_msg and "부동산 관련 질문이면 Y" in system_msg.get("content", ""):
        if try_api_call:
            try:
                # 실제로 OpenAI API를 호출하여 메시지가 인사/일상 대화인지 확인
                user_content = user_msg.get("content", "")
                api_response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "사용자의 메시지가 인사(안녕, 반가워, hi, hello 등), 일상 대화, 잡담인 경우 'GREETING'으로 응답하세요. "
                                                    "사용자가 서비스 문의(뭐하는 서비스, 어떤 일 등)를 하는 경우 'SERVICE'로 응답하세요. "
                                                    "사용자 메시지가 부동산과 관련 없는 다른 주제(주식, 날씨, 음식 등)의 경우 'OTHER'로 응답하세요. "
                                                    "사용자 메시지가 부동산과 관련된 내용이면 'REAL_ESTATE'로 응답하세요. "
                                                    "한 단어로만 응답하세요."},
                        {"role": "user", "content": user_content}
                    ]
                )
                
                message_type = api_response.choices[0].message.content.strip()
                
                # 응답 유형에 따라 Y/N 결정
                if message_type in ["GREETING", "SERVICE", "OTHER"]:
                    content = "N"
                else:
                    content = "Y"
                    
            except Exception as e:
                print(f"OpenAI API 호출 오류: {e}")
                # API 호출 실패 시 기존 방식으로 체크
                content = _check_using_patterns(user_msg.get("content", "").lower())
        else:
            # API 호출 안함 - 패턴 매칭 사용
            content = _check_using_patterns(user_msg.get("content", "").lower())
                
    elif system_msg and "정형적 가격" in system_msg.get("content", ""):
        content = "PRICE"
    elif system_msg and "파싱" in system_msg.get("content", ""):
        content = "지역: 서울, \n매매/전세 여부: 매매, \n시간 정보: 현재"
    # 인사나 잡담 응답 처리
    elif system_msg and "부동산 중에서도" in system_msg.get("content", "") and user_msg:
        if try_api_call:
            try:
                user_content = user_msg.get("content", "")
                api_response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "당신은 부동산 정보를 제공하는 챗봇 '두껍이'입니다. "
                                                    "사용자의 메시지를 다음 카테고리로 분류하세요: "
                                                    "1. GREETING: 인사 (안녕, 반가워 등) "
                                                    "2. SERVICE_INQUIRY: 서비스 문의 (뭐하는 서비스, 어떤 일 등) "
                                                    "3. OTHER_TOPIC: 부동산과 관련 없는 주제 (주식, 날씨, 음식 등) "
                                                    "4. THANKS: 감사 표현 (고마워, 감사합니다 등) "
                                                    "5. REAL_ESTATE: 부동산 관련 질문 "
                                                    "6. BOT_ABILITY: 봇의 능력에 관한 질문 "
                                                    "7. OTHER: 기타 카테고리 "
                                                    "한 단어로만 응답하세요."},
                        {"role": "user", "content": user_content}
                    ]
                )
                
                message_category = api_response.choices[0].message.content.strip()
                
                # 카테고리에 따른 응답 생성
                if message_category == "GREETING":
                    content = "안녕하세요! 저는 두껍이입니다. 한국의 아파트 매매가와 전세가에 대한 정보를 알려드릴 수 있어요~두껍!"
                elif message_category == "SERVICE_INQUIRY":
                    content = "저는 한국의 아파트 매매가와 전세가 정보를 알려드리는 두껍이입니다. 지역명과 함께 물어보시면 최신 부동산 가격 정보를 알려드릴게요~두껍!"
                elif message_category == "OTHER_TOPIC":
                    content = "죄송해요, 저는 부동산 정보만 알려드릴 수 있어요. 아파트 매매가나 전세가에 대해 물어봐주세요~두껍!"
                elif message_category == "THANKS":
                    content = "도움이 되어 기쁩니다! 또 궁금한 것이 있으시면 언제든지 물어보세요~두껍!"
                elif message_category == "REAL_ESTATE":
                    content = "부동산에 관심이 있으시군요! 특정 지역의 아파트 매매가나 전세가에 대해 물어보시면 자세히 알려드릴게요~두껍!"
                elif message_category == "BOT_ABILITY":
                    content = "저는 한국의 아파트 매매가와 전세가 정보를 알려드릴 수 있어요. KB 부동산 데이터 허브의 데이터를 기반으로 정보를 제공하고 있습니다~두껍!"
                else:
                    content = "안녕하세요! 한국의 아파트 매매가나 전세가에 대해 궁금한 점이 있으신가요? 지역명을 말씀해주시면 도와드릴게요~두껍!"
                
            except Exception as e:
                print(f"대화 분류 API 호출 오류: {e}")
                # API 호출 실패 시 기존 하드코딩 방식으로 체크
                content = _get_conversation_response(user_msg.get("content", "").lower())
        else:
            # API 호출 안함 - 패턴 매칭 사용
            content = _get_conversation_response(user_msg.get("content", "").lower())
            
    # 최종 응답일 경우 (가격 데이터가 포함된 경우)
    elif user_msg and "가격 데이터" in user_msg.get("content", ""):
        # 사용자 메시지에서 지역과 가격 데이터 추출
        user_content = user_msg.get("content", "")
        region_match = re.search(r"지역:\s*([^가-힣\s]+)", user_content)
        region = region_match.group(1) if region_match else "서울"
        
        # 가격 데이터 정보가 포함된 응답 생성
        content = f"지역 {region}에 대한 분석 결과입니다~두껍!\n"
        content += "데이터에 따르면, 해당 지역의 최근 부동산 가격 추이는 다음과 같습니다:\n"
        
        # 가격 데이터가 있는 경우 해당 데이터 포함
        price_data_match = re.search(r"가격 데이터:\s*\n(.*?)(?:\n\n|$)", user_content, re.DOTALL)
        if price_data_match:
            formatted_price_data = price_data_match.group(1)
            content += f"{formatted_price_data}\n\n"
        
        # 분석 요약 정보 추가
        content += "이 데이터를 기반으로 한 유의미한 통찰:\n"
        content += "최근 평균 가격은 약 12억 7천만원이며, 가격 추이는 하락세를 보이고 있습니다~두껍!"
    else:
        content = "안녕하세요! 저는 두껍이입니다. 부동산 정보에 대해 물어보세요~두껍!"
    
    # ChatCompletion 객체 모의 생성
    mock_message = ChatCompletionMessage(role="assistant", content=content)
    
    class MockChoice:
        def __init__(self, message):
            self.message = message
            self.index = 0
            self.finish_reason = "stop"
        
    mock_choice = MockChoice(message=mock_message)
    
    class MockResponse:
        def __init__(self, choices):
            self.choices = choices
            self.id = "mock-response-id"
            self.model = model
            self.created = int(datetime.now().timestamp())
    
    return MockResponse(choices=[mock_choice])

# 패턴 매칭을 통한 메시지 유형 확인 (API 호출 실패 시 대체 함수)
def _check_using_patterns(text):
    greeting_patterns = ["안녕", "반가", "hi", "hello", "hey", "하이", "ㅎㅇ", "방가"]
    service_inquiry_patterns = ["뭐하는", "어떤 일", "서비스", "무엇을", "기능", "할 수 있"]
    other_topics = ["주식", "날씨", "게임", "음식", "영화", "취미", "스포츠"]
    daily_conversation = ["고마", "감사", "thank", "땡큐", "반가", "잘 지냈"]
    
    # 인사말이나 일상 대화인 경우 N 반환
    if any(pattern in text for pattern in greeting_patterns) or \
       any(pattern in text for pattern in service_inquiry_patterns) or \
       any(topic in text for topic in other_topics) or \
       any(expr in text for expr in daily_conversation):
        return "N"
    
    # 기본적으로 Y 반환 (부동산 관련 질문으로 판단)
    return "Y"

# 대화형 응답 생성 (API 호출 실패 시 대체 함수)
def _get_conversation_response(text):
    # 인사말 패턴 체크
    if any(pattern in text for pattern in ["안녕", "반가", "hi", "hello", "ㅎㅇ", "하이"]):
        return "안녕하세요! 저는 두껍이입니다. 한국의 아파트 매매가와 전세가에 대한 정보를 알려드릴 수 있어요~두껍!"
    # 서비스 문의 체크
    elif any(pattern in text for pattern in ["뭐하는", "어떤 일", "서비스", "무엇을", "기능"]):
        return "저는 한국의 아파트 매매가와 전세가 정보를 알려드리는 두껍이입니다. 지역명과 함께 물어보시면 최신 부동산 가격 정보를 알려드릴게요~두껍!"
    # 다른 주제 문의 체크
    elif any(topic in text for topic in ["주식", "날씨", "게임", "음식", "영화"]):
        return "죄송해요, 저는 부동산 정보만 알려드릴 수 있어요. 아파트 매매가나 전세가에 대해 물어봐주세요~두껍!"
    # 감사 표현에 대한 응답
    elif any(thanks in text for thanks in ["고마", "감사", "thank", "땡큐"]):
        return "도움이 되어 기쁩니다! 또 궁금한 것이 있으시면 언제든지 물어보세요~두껍!"
    # 부동산에 대한 일반적인 질문
    elif any(estate_term in text for estate_term in ["부동산", "집값", "아파트", "전세", "매매"]):
        return "부동산에 관심이 있으시군요! 특정 지역의 아파트 매매가나 전세가에 대해 물어보시면 자세히 알려드릴게요~두껍!"
    # 봇의 능력에 관한 질문
    elif any(ability in text for ability in ["할 수 있", "알려줄 수 있", "뭘 알고", "뭘 알려"]):
        return "저는 한국의 아파트 매매가와 전세가 정보를 알려드릴 수 있어요. KB 부동산 데이터 허브의 데이터를 기반으로 정보를 제공하고 있습니다~두껍!"
    # 기타 일상 대화
    else:
        return "안녕하세요! 한국의 아파트 매매가나 전세가에 대해 궁금한 점이 있으신가요? 지역명을 말씀해주시면 도와드릴게요~두껍!"

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
            try:
                # OpenAI를 사용하여 질문 유형 확인
                question_kind_response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
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
                        model="gpt-3.5-turbo",
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
                first_check = _check_using_patterns(text.lower())
                
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
            first_check = _check_using_patterns(text.lower())
            
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

# 파싱된 결과에 기본값을 추가하는 함수 수정
def fill_parsing_defaults(parsed_text):
    try:
        # 불필요한 공백 및 개행 제거
        parsed_text = re.sub(r"\s+", " ", parsed_text)
        print(parsed_text)

        # 각 필드 추출
        region_match = re.search(r"지역:\s*([가-힣\s]+)", parsed_text)
        deal_type_match = re.search(r"매매/전세 여부:\s*(매매|전세)", parsed_text)
        time_info_match = re.search(r"시간 정보:\s*([0-9년월일\s]+)", parsed_text)

        # 추출된 값이 없으면 기본값으로 대체
        region = region_match.group(1).strip() if region_match else "전국"
        deal_type = deal_type_match.group(1) if deal_type_match else "매매"
        time_info = time_info_match.group(1).strip() if time_info_match else "현재"

        print("================파싱결과====================")
        print(region, deal_type, time_info)

        return {
            "지역": region,
            "매매/전세 여부": 'sale' if deal_type == '매매' else 'rent',
            "시간 정보": time_info
        }
    except Exception as e:
        print(f"파싱 오류: {e}")
        # 오류 발생 시 기본값 반환
        return {
            "지역": "전국",
            "매매/전세 여부": "sale",
            "시간 정보": "현재"
        }

# 4. Google Custom Search API를 통한 뉴스 검색
def google_search(query):
    api_key = os.getenv('GOOGLE_API_KEY')
    search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={api_key}&cx={search_engine_id}"

    response = requests.get(url)
    results = response.json().get('items', [])
    return [(item['title'], item['link']) for item in results]

# 6. 매매가/전세가 데이터 조회
def get_property_price(region_name: str, price_type: str, date_info: str, db: Session):
    if "month" in date_info:
        # ... 기존 코드 유지
        pass
    else:
        try:
            # "현재"인 경우 오늘 날짜 기준 한 달 전후로 설정
            if date_info == "현재":
                today = datetime.now().date()
                target_date = today - timedelta(days=30)  # 1달 전
                end_date = today + timedelta(days=30)     # 1달 후
                print(f"현재 날짜 기준 데이터 조회: 시작일={target_date}, 종료일={end_date}")
            else:
                # date_info가 구체적인 날짜인 경우
                target_date = datetime.strptime(date_info, "%Y-%m-%d").date()
                end_date = target_date + timedelta(days=90)  # 3개월 후

            # 지역 이름으로 지역 코드 찾기
            regions = [region_name]
            print(f"매매가 안쪽 {regions} {price_type}")
            
            # 쿼리 생성 및 실행
            query = (
                select(PropertyPriceData)
                .join(Region, PropertyPriceData.region_code == Region.region_code)
                .where(
                    or_(*[Region.region_name_kor.like(f"%{name}%") for name in regions]),
                    PropertyPriceData.price_type == price_type,
                    PropertyPriceData.date >= target_date,
                    PropertyPriceData.date <= end_date
                )
                .limit(10)
            )
            
            results = db.execute(query).scalars().all()
            
            # 결과 출력 (디버깅용)
            for row in results:
                print(f"ID: {row.id}, Region Code: {row.region_code}, Date: {row.date}, Price Type: {row.price_type}, "
                    f"Index Value: {row.index_value}, Avg Price: {row.avg_price}, Interpolated: {row.is_interpolated}")
            
            # 결과를 리스트로 변환
            data = []
            total_price = 0  # 평균 가격 계산을 위한 변수
            
            for row in results:
                data.append({
                    'region': row.region_code,
                    'date': row.date.strftime('%Y-%m-%d'),
                    'deal_type': row.price_type,
                    'price': row.avg_price
                })
                total_price += row.avg_price  # 가격 합산
            
            avg_price = total_price / len(data) if data else 0  # 평균 가격 계산
            
            print(f"쿼리결과 : {data}")
            return data, avg_price
        except Exception as e:
            print(f"데이터 처리 중 오류 발생: {e}")
            # 오류 발생 시 현재 날짜 기준으로 조회
            try:
                today = datetime.now().date()
                start_date = today - timedelta(days=30)  # 1달 전
                end_date = today + timedelta(days=30)    # 1달 후
                print(f"오류 발생으로 현재 기준 데이터 조회: 시작일={start_date}, 종료일={end_date}")
                
                # 쿼리 재실행
                query = (
                    select(PropertyPriceData)
                    .join(Region, PropertyPriceData.region_code == Region.region_code)
                    .where(
                        or_(*[Region.region_name_kor.like(f"%{name}%") for name in regions]),
                        PropertyPriceData.price_type == price_type,
                        PropertyPriceData.date >= start_date,
                        PropertyPriceData.date <= end_date
                    )
                    .limit(10)
                )
                
                results = db.execute(query).scalars().all()
                
                # 결과를 리스트로 변환
                data = []
                total_price = 0
                
                for row in results:
                    data.append({
                        'region': row.region_code,
                        'date': row.date.strftime('%Y-%m-%d'),
                        'deal_type': row.price_type,
                        'price': row.avg_price
                    })
                    total_price += row.avg_price
                
                avg_price = total_price / len(data) if data else 0
                
                print(f"쿼리결과(오류 복구): {data}")
                return data, avg_price
            except Exception as nested_e:
                print(f"복구 시도 중 추가 오류 발생: {nested_e}")
                return [], 0

# 7. 뉴스 데이터 조회
def get_news_articles(region_name: str, db: Session):
    # 현재 날짜 기준 1달 내 데이터 조회
    one_month_ago = datetime.now().date() - timedelta(days=120)

    query = (
        select(NewsArticle)
        .where(NewsArticle.content.like(f"%{region_name}%"))
        .where(NewsArticle.published_date > one_month_ago)  # 최근 1달 내 데이터
        .limit(4)  # 최대 4개의 뉴스 기사 조회
    )
    query_result = db.execute(query).fetchall()

    result = []
    for record in query_result:
        # 첫 번째 요소만 가져오기 (예: (<PropertyPriceData 객체>,))
        data = record[0]
        print(f"ID: {data.id}, Title: {data.title}, Content: {data.content}, "
              f"Published Date: {data.published_date}")
        result.append({
            "title": data.title,
            "content": data.content,
            "url": data.url,
            "published_date": data.published_date.strftime('%Y-%m-%d')
        })

    if not result:
        return None
    return result

# 데이터 포맷팅 함수
def format_price_data(region_name, price_data):
    """
    부동산 가격 데이터를 포맷하는 함수.
    """
    formatted_price_data = []
    for item in price_data:
        formatted_price_data.append(
            f"- 날짜: {item['date']}, 거래 유형: {item['deal_type']}, 평균 가격: {item['price'] * 10000:,}원"
        )
    return "\n".join(formatted_price_data)

# 분석 요약 생성 함수
def generate_analysis_summary(price_data):
    """
    가격 데이터를 분석하고 요약 생성.
    """
    avg_price = sum(item['price'] for item in price_data) / len(price_data)
    trend = "상승" if price_data[-1]['price'] > price_data[0]['price'] else "하락"
    return f"최근 평균 가격은 {avg_price * 10000:,.0f}원이며, 가격 추이는 {trend}세입니다."

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
                        model="gpt-3.5-turbo",
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
                    model="gpt-3.5-turbo",
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
                        model="gpt-3.5-turbo",
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

