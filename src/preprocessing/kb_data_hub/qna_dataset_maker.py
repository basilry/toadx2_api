import random
import json
from datetime import datetime, timedelta
from sqlalchemy import select
from src.database.models.database_model import Prediction, Region, PropertyPriceData
from src.database.database import get_db  # DB 연결 함수 가져오기


def format_date_natural(date):
    """날짜를 랜덤한 형식으로 변환하는 함수."""
    year = date.year
    month = date.month
    day = date.day

    templates = [
        f"{year}년",
        f"{month}월",  # 무조건 올해
        f"{day}일",  # 무조건 이번 달
        f"{year}년 {month}월",
        f"{year}년 {month}월 {day}일",
        f"{month}월 {day}일"  # 무조건 올해
    ]

    return random.choice(templates)  # 랜덤으로 선택


def parse_time_reference(natural_reference, current_date):
    """자연어 표현을 날짜로 변환하는 함수."""
    if natural_reference in ["옛날", "과거"]:
        return current_date - timedelta(days=365)  # 1년 전 날짜
    elif natural_reference in ["지금", "요즘", "요새"]:
        return current_date  # 오늘 날짜
    elif natural_reference in ["나중에", "미래에", "언젠가"]:
        return current_date + timedelta(days=365)  # 1년 후 날짜
    return current_date


def generate_real_estate_queries():
    # 문장 템플릿
    templates = {
        "sale": [
            "{date}에 {region}의 아파트 매매가격이 어느정도 되죠?",
            "{date}에는 매매가 얼마지? {region}의 기록을 알려줘",
            "{region}지역 {date} 시점의 매매가는 얼마니",
            "{region}의 매매가가 궁금해. {date} 시점에 대해 알려줄래?",
            "매매가격을 알고 싶어. {date}의 {region}을 알려줘",
            "매매가를 알려줘. {region}지역의 {date} 때.",
            "매매가격이 {date} 얼마나 되니?",
            "{date}에 {region}의 매매가를 알려줘",
            "{time_reference} {region}의 아파트 매매가격은 얼마인가요?"  # 자연어 표현 추가
        ],
        "rent": [
            "{date}에 {region}의 아파트 전세가격이 어느정도 되죠?",
            "{date}에는 전세가 얼마지? {region}의 기록을 알려줘",
            "{region}지역 {date} 시점의 전세가는 얼마니",
            "{region}의 전세가가 궁금해. {date} 시점에 대해 알려줄래?",
            "전세가격을 알고 싶어. {date}의 {region}을 알려줘",
            "전세가를 알려줘. {region}지역의 {date} 때.",
            "전세가격이 {date} 얼마나 되니?",
            "{date}에 {region}의 전세가를 알려줘",
            "{time_reference} {region}의 아파트 전세가격은 얼마인가요?"  # 자연어 표현 추가
        ]
    }

    # 현재 날짜
    current_date = datetime.now().date()

    # 결과 저장할 리스트
    final_documents = []
    final_labels = []

    # 데이터베이스 세션 사용
    with next(get_db()) as db:  # get_db() 함수로부터 세션 가져오기
        # 매매 및 전세 아파트 데이터 조회
        price_query = select(PropertyPriceData.date, PropertyPriceData.region_code, PropertyPriceData.price_type)
        price_data = db.execute(price_query).all()

        # 예측 데이터 조회
        prediction_query = select(Prediction.date, Prediction.region_code, Prediction.price_type)
        prediction_data = db.execute(prediction_query).all()

        # 지역 데이터 조회
        region_query = select(Region.region_code, Region.region_name_kor)
        regions = db.execute(region_query).all()

        # 문장 생성
        for row in price_data + prediction_data:  # 가격 데이터와 예측 데이터를 합쳐서 처리
            date = row[0]  # 실제 날짜 (datetime.date 객체)
            region_code = row[1]  # 지역 코드
            price_type = row[2]  # 가격 타입
            region_name = next((r[1] for r in regions if r[0] == region_code), None)  # 지역 이름

            if region_name:  # 지역 이름이 유효한 경우
                # 랜덤으로 자연어 표현 선택
                natural_reference = random.choice(["옛날", "과거", "지금", "요즘", "요새", "나중에", "미래에", "언젠가", ""])
                parsed_date = parse_time_reference(natural_reference, current_date)
                natural_date = format_date_natural(parsed_date)

                # 무작위 선택
                template = random.choice(templates[price_type])  # 가격 타입에 맞는 템플릿 선택

                # 문장 생성
                sentence = template.format(date=natural_date, region=region_name, time_reference=natural_reference)

                # 결과 추가
                final_documents.append(sentence)

                # 레이블 생성 - 자연어 표현에 따른 실제 날짜 값으로 설정
                if natural_reference in ["옛날", "과거"]:
                    time_info = (current_date - timedelta(days=365)).strftime("%Y-%m-%d")  # 1년 전 날짜
                elif natural_reference in ["지금", "요즘", "요새"]:
                    time_info = current_date.strftime("%Y-%m-%d")  # 현재 날짜
                elif natural_reference in ["나중에", "미래에", "언젠가"]:
                    time_info = (current_date + timedelta(days=365)).strftime("%Y-%m-%d")  # 1년 후 날짜
                else:
                    time_info = date.strftime("%Y-%m-%d")  # 실제 데이터 날짜 사용

                label = {
                    "지역": region_name,
                    "매매/전세 여부": price_type,
                    "시간 정보": time_info  # 실제 날짜 값 할당
                }
                final_labels.append(label)

    # 최종 JSON 구조 생성
    final_json = {
        "documents": final_documents,
        "labels": final_labels
    }

    # JSON 파일로 저장
    json_file_path = 'datasets/qna_dataset/nlp_parsing_qna_dataset.json'
    with open(json_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(final_json, json_file, ensure_ascii=False, indent=4)

    return json_file_path


if __name__ == "__main__":
    json_file_path = generate_real_estate_queries()
    print(f"Generated queries saved to {json_file_path}")