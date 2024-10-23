from sqlalchemy.orm import Session
from datetime import date
from src.database.database import SessionLocal
from src.database.models.database_model import PropertyPriceData


# 영문 price_type을 한글로 변환하는 함수
def convert_price_type_to_english(price_type):
    if price_type == '전세':
        return 'rent'
    elif price_type == '매매':
        return 'sale'
    return price_type


def fill_avg_price_with_index_based_calculation(session: Session):
    # 1. 2022년 1월 10일 기준 데이터 가져오기 (시간 없이 날짜만 사용)
    reference_date = date(2022, 1, 10)

    # 지역별로 2022년 1월 10일에 지수가 100인 데이터를 추출
    reference_prices = session.query(PropertyPriceData).filter(
        PropertyPriceData.date == reference_date,
        PropertyPriceData.index_value == 100
    ).all()

    # 지역별로 100일 때의 avg_price 값을 저장 (region_code를 key로 하고 avg_price를 value로 저장)
    reference_price_dict = {price_data.region_code: price_data.avg_price for price_data in reference_prices}

    # 2. 평균 가격이 'NaN' 또는 None인 데이터 가져오기
    missing_price_data = session.query(PropertyPriceData).filter(
        (PropertyPriceData.avg_price.is_(None)) | (PropertyPriceData.avg_price == 'NaN')
    ).all()

    # 3. NaN 값을 채워 넣기
    for data in missing_price_data:
        if data.region_code in reference_price_dict:
            reference_avg_price = reference_price_dict[data.region_code]
            if reference_avg_price is not None and data.index_value is not None:
                # 지수를 기준으로 비례하여 avg_price를 계산
                data.avg_price = (data.index_value / 100) * reference_avg_price

                # price_type을 변환하여 저장 (전세 -> rent, 매매 -> sale)
                data.price_type = convert_price_type_to_english(data.price_type)

                session.add(data)  # 업데이트된 데이터를 세션에 추가

    # 4. 세션에 변경 사항 반영
    session.commit()
    print("avg_price 값이 NaN인 데이터를 지수 기반으로 채워 넣었습니다.")


def run_data_filling_pipeline():
    """데이터 보강 파이프라인 실행"""
    session = SessionLocal()  # DB 세션 생성
    try:
        fill_avg_price_with_index_based_calculation(session)
    except Exception as e:
        print(f"데이터 보강 중 오류 발생: {e}")
    finally:
        session.close()  # 세션 종료


if __name__ == "__main__":
    run_data_filling_pipeline()
