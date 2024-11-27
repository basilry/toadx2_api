import os
import re
from datetime import datetime, timedelta

import requests
from fastapi import APIRouter, Request, Depends
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate, AIMessagePromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy.orm import Session
from src.database.database import get_db
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from src.database.models.database_model import PropertyPriceData, Prediction, NewsArticle, Region
from sqlalchemy import select, func, or_
from langchain_teddynote.messages import stream_response
import google.generativeai as genai

# 환경 변수 로드
load_dotenv()
huggingfaceToken = os.getenv('HUGGINGFACE_TOKEN')

# FastAPI 라우터 초기화
router = APIRouter()

# LangChain 메모리 설정 (대화 기록 관리)
memory = ConversationBufferMemory()

# 캐시 설정 (사용자 세션을 위한 캐시)
cache = {}
res_type = "text"

MODEL_NAME = 'gemini-1.5-flash'

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel(MODEL_NAME)

llm = ChatGoogleGenerativeAI(model=MODEL_NAME)
reqeust_prompt_template = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        "유저의 질문이 부동산 매매가, 전세가 등 '정형적 가격'에 대한 질문이면 'PRICE'를 대답해줘"
        "유저의 질문이 부동산 정보, 뉴스, 전망 등 '비정형적 내용'에 대한 질문이면 'INFO'로 대답해줘"
    ),
    HumanMessagePromptTemplate.from_template(
        "유저의 질문: {input_text}"
    )
    ])
parsing_prompt_template = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        "모든 응답은 반드시 한국어로 작성되어야 합니다. 다음 유저의 질문을 파싱하여 지침에 따라 답변하세요."
        "특수문자는 넣지말고, key-value는 콜론으로 구분하세요"
        "각 값은 쉼표로 구분하세요"
        "파싱 결과:\n"
        "지역: [지역명을 여기에만 입력하세요],\n"
        "매매/전세 여부: [매매 or 전세를 명시하세요],\n"
        "시간 정보: [시간 정보를 여기에만 입력하세요]\n"
    ),
    HumanMessagePromptTemplate.from_template(
        "유저의 질문: {input_text}"
    )
])
response_prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(
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
            "유저가 인사를 하면 자기 소개를 해야 합니다."
        ),
        HumanMessagePromptTemplate.from_template(
            "유저의 질문: {input_text}"
        ),
    ])

# 1. 초기 응답 반환 함수
def get_initial_response(session_id):
    if session_id not in cache:
        return "안녕하세요! 저는 '두껍이'입니다! 어떤 것을 도와드릴까요?~두껍!"
    return None


# 2. Gemini API로 질문 유형 확인하는 함수
def gemini_api_confirm_question_kind(text: str):
    global res_type
    response = gemini_model.generate_content(f"부동산 관련 질문이면 Y로 대답해주고, 아니면 무조건 N으로 대답해줘: {text}")
    print("질문 유형 확인 결과", response.text.strip())
    question_kind = response.text.strip()

    if question_kind == "N":
        return "N"

    request_analysis_chain = LLMChain(
        llm=llm,
        prompt=reqeust_prompt_template,
    )
    followup_kind = request_analysis_chain.invoke({"input_text": text})
    res_type = "text"

    return followup_kind['text'].strip()


# 파싱된 결과에 기본값을 추가하는 함수 수정
def fill_parsing_defaults(parsed_result):
    # 파싱 결과가 문자열이 아닌 딕셔너리인지 확인
    if isinstance(parsed_result, dict) and "text" in parsed_result:
        # 'text' 필드에서 문자열을 파싱
        parsed_text = parsed_result["text"]

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

    else:
        # 만약 파싱 결과가 딕셔너리가 아닐 경우 경고 메시지 출력 후 기본값 반환
        print(f"Warning: parsed_result is not a dictionary. Parsed_result: {parsed_result}")
        return {
            "지역": "전국",
            "매매/전세 여부": "매매",
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
    print(111)
    current_date = datetime.now().date()

    # date_info가 '현재'이면 최근 1달 내 데이터를 조회
    if date_info == "" or date_info == "현재":
        start_date = current_date - timedelta(days=30)
        end_date = current_date
        table = PropertyPriceData  # 현재 시점 데이터는 PropertyPriceData에서 조회
    else:
        # date_info가 특정 날짜인 경우 해당 날짜를 기준으로 처리
        parsed_date = datetime.strptime(date_info, "%Y-%m-%d").date()

        if parsed_date > current_date:
            # 미래 데이터는 Prediction 테이블에서 조회
            start_date = parsed_date
            end_date = parsed_date
            table = Prediction  # 미래 시점 데이터는 Prediction 테이블에서 조회
        else:
            # 과거 또는 현재 데이터는 PropertyPriceData에서 조회
            start_date = parsed_date - timedelta(days=30)
            end_date = parsed_date
            table = PropertyPriceData  # 과거 시점 데이터는 PropertyPriceData에서 조회

    # 공백을 기준으로 단어 분리
    keywords = [word.replace("시", "").replace("구", "").replace("도", "") for word in region_name.split()]
    print("region 쪼개기", keywords)

    # 각 키워드를 %감싸서 LIKE 조건을 생성
    like_conditions = [Region.region_name_kor.like(f"%{keyword}%") for keyword in keywords]

    # region_name_kor 컬럼 조인해서 조회 필요
    # DB에서 매매가/전세가 데이터를 조회
    query = (
        select(table)
        .join(Region, table.region_code == Region.region_code)
        .where(or_(*like_conditions))
        .where(table.price_type == price_type)
        .where(func.to_char(table.date, 'YYYY-MM-DD') >= start_date.strftime('%Y-%m-%d'))  # 시작 날짜
        .where(func.to_char(table.date, 'YYYY-MM-DD') <= end_date.strftime('%Y-%m-%d'))
        .limit(4)  # 최대 4개 데이터 조회
    )

    query_result = db.execute(query).fetchall()

    result = []
    for record in query_result:
        # 첫 번째 요소만 가져오기 (예: (<PropertyPriceData 객체>,))
        data = record[0]
        print(f"ID: {data.id}, Region Code: {data.region_code}, Date: {data.date}, "
              f"Price Type: {data.price_type}, Index Value: {data.index_value}, "
              f"Avg Price: {data.avg_price}, Interpolated: {data.is_interpolated}")
        result.append({
            "region": data.region_code,
            "date": data.date.strftime('%Y-%m-%d'),
            "deal_type": data.price_type,
            "price": data.avg_price
        })

    print("쿼리결과 :", result)

    if not result:
        return None  # 데이터가 없을 경우 처리

    return result


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


# 파싱된 결과에서 공백 및 개행 제거 함수
def clean_parsing_result(parsed_text: str):
    # 정규식을 사용해 불필요한 공백 및 개행 제거
    cleaned_text = re.sub(r'\s+', ' ', parsed_text).strip()
    return cleaned_text


# 8. 수정된 부동산 질문 핸들러
def handle_real_estate_question(user_input, session_id, db: Session):
    global res_type
    # 질문 유형 확인
    kind = gemini_api_confirm_question_kind(user_input)
    print("부동산 관련 질문 여부 확인", kind)

    # 질문이 부동산과 관련 없는 경우
    if kind == "N":
        response_chain = LLMChain(
            llm=llm,
            prompt=response_prompt_template,
        )
        response = response_chain.invoke({"input_text": user_input})

        return response["text"]

    print(2222)

    # gemma2 파인튜닝 모델에게 프롬프트 전달
    chain = LLMChain(
        llm=llm,
        prompt=parsing_prompt_template,
    )
    parsed_result = chain.invoke({"input_text": user_input})
    stream_response("모델 응답결과 :", parsed_result)

    parsed_result = fill_parsing_defaults(parsed_result)
    print("전세/매매가 여부 파싱", parsed_result)

    # 질문이 매매가/전세가 관련일 경우
    if kind == "PRICE":
        region = parsed_result.get("지역", "전국")
        deal_type = parsed_result.get("매매/전세 여부", "매매")
        date_info = parsed_result.get("시간 정보", "현재")

        print("매매가 안쪽", region, deal_type, date_info)

        # 매매가/전세가 DB 조회
        price_data = get_property_price(region, deal_type, date_info, db)
        print("매매가 데이터 조회 결과", price_data)
        if not price_data:
            return "데이터를 찾을 수 없습니다~두껍!"

        print(price_data)
        res_type = "price"

        return price_data

    # 질문이 정보/뉴스 관련일 경우
    elif kind == "INFO":
        region_name = parsed_result["지역"] or "전국"

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

    # 부동산 관련이 아니면 고정된 프롬프트로 reject
    return "부동산 관련 질문만 대답할 수 있습니다!~두껍!"


# 9. FastAPI '/chat' 엔드포인트
@router.post("/chat")
async def chat(request: Request, db: Session = Depends(get_db)):
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

    response_chain = LLMChain(
        llm=llm,
        prompt=response_prompt_template,
    )
    final_response = response_chain.invoke({"input_text": response})

    # 최종 응답 반환
    return {"type": res_type, "model_response": final_response['text'], "response": response, "session_id": session_id}