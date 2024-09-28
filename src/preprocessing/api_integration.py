from datetime import datetime
from sqlalchemy.orm import Session
from src.api.models.kb_real_estate_data_hub import PropertyPriceData, Region
from src.crawling.kb_real_estate_api import get_real_estate_data


# 지역을 저장하고 지역 ID를 반환하는 함수
def store_region(session: Session, region_name: str):
    region = session.query(Region).filter_by(region_name=region_name).first()
    if not region:
        region = Region(region_name=region_name)
        session.add(region)
        session.commit()
        session.refresh(region)
    return region.id


# 부동산 데이터를 저장하는 함수
def store_property_data(session: Session, region_id: int, date: datetime, price_type: str, time_span: str,
                        index_value: float, avg_price: float):
    # 중복 데이터 확인 (지역, 날짜, 매매/전세)
    existing_data = session.query(PropertyPriceData).filter_by(
        region_id=region_id,
        date=date,
        price_type=price_type,
        time_span=time_span
    ).first()

    # 중복된 데이터가 없을 경우에만 삽입
    if not existing_data:
        property_data = PropertyPriceData(
            region_id=region_id,
            date=date,
            price_type=price_type,
            time_span=time_span,
            index_value=index_value,
            avg_price=avg_price
        )
        session.add(property_data)
        session.commit()
        print(f"Inserted new data for {region_id}, {date}")
    else:
        print(f"Data already exists for {region_id}, {date} - Skipping")


# API로부터 데이터를 가져와서 DB에 저장하는 함수
def process_and_insert_data(session: Session, price_type="매매", time_span="주간"):
    # API로부터 데이터 가져오기
    real_estate_data = get_real_estate_data()

    # 날짜 리스트
    date_list = real_estate_data['dataBody']['data']['날짜리스트']

    # 데이터 리스트 처리
    for region_data in real_estate_data['dataBody']['data']['데이터리스트']:
        region_name = region_data['지역명']  # 지역명
        price_data_list = region_data['dataList']  # 가격 지수 리스트

        # 지역을 저장하고 지역 ID 가져오기
        region_id = store_region(session, region_name)

        # 날짜 리스트와 매칭되는 가격 데이터 저장
        for date_str, price_index in zip(date_list, price_data_list):
            date = datetime.strptime(date_str, '%Y%m%d')
            index_value = price_index

            # 평균 가격이 데이터에 없으므로 None 처리
            avg_price = None

            # 부동산 데이터 저장
            store_property_data(session, region_id, date, price_type, time_span, index_value, avg_price)

    print("API 데이터를 성공적으로 DB에 삽입했습니다.")
