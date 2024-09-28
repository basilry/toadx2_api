import warnings
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from src.database.models.kb_real_estate_data_hub import PropertyPriceData, Region
from src.crawling.kb_real_estate_api import (
    get_weekly_apartment_sale_cost_index,
    get_weekly_apartment_rent_cost_index,
    get_monthly_apartment_sale_cost_avg,
    get_monthly_apartment_rent_cost_avg
)

# 경고 무시 설정
warnings.filterwarnings('ignore')

print("=========================================================================")
print("1. API로부터 데이터 불러오기")

# 월간 평균 매매가/전세가 데이터를 API로부터 불러오기
monthly_sale_avg_data = get_monthly_apartment_sale_cost_avg()
monthly_rent_avg_data = get_monthly_apartment_rent_cost_avg()

# 주간 매매 지수/전세 지수 데이터를 API로부터 불러오기
weekly_sale_index_data = get_weekly_apartment_sale_cost_index()
weekly_rent_index_data = get_weekly_apartment_rent_cost_index()

print("=========================================================================")
print("2. 데이터 전처리 및 변환")


# API로부터 받아온 데이터를 처리하는 함수
def process_api_data(api_data, is_weekly=True):
    """API 데이터에서 날짜 리스트와 데이터를 분리"""
    date_list = api_data['dataBody']['data']['날짜리스트']  # 날짜 리스트
    region_data_list = api_data['dataBody']['data']['데이터리스트']  # 지역별 데이터 리스트

    # 처리된 데이터를 담을 리스트 초기화
    processed_data = []

    # 지역별 데이터를 순회하며 처리
    for region_data in region_data_list:
        region_name = region_data['지역명']  # 지역명
        price_data_list = region_data['dataList']  # 가격 데이터 리스트

        # 날짜와 가격 데이터를 병합
        for date_str, price in zip(date_list, price_data_list):
            if is_weekly:
                date = pd.to_datetime(date_str, format='%Y%m%d', errors='coerce')  # 주간 날짜 (YYYYMMDD 형식)
                processed_data.append({
                    '지역명': region_name,
                    '날짜': date,
                    '지수': price  # 주간 데이터는 지수
                })
            else:
                date = pd.to_datetime(date_str, format='%Y%m', errors='coerce')  # 월간 날짜 (YYYYMM 형식)
                processed_data.append({
                    '지역명': region_name,
                    '날짜': date,
                    '평균가': price  # 월간 데이터는 평균가
                })

    # 결과를 데이터프레임으로 반환
    return pd.DataFrame(processed_data)


# 주간 및 월간 데이터를 처리 (is_weekly=True 또는 False로 주간/월간 구분)
weekly_sale_df = process_api_data(weekly_sale_index_data, is_weekly=True)
weekly_rent_df = process_api_data(weekly_rent_index_data, is_weekly=True)
monthly_sale_avg_df = process_api_data(monthly_sale_avg_data, is_weekly=False)
monthly_rent_avg_df = process_api_data(monthly_rent_avg_data, is_weekly=False)

print("데이터 전처리 결과:")
print("주간 매매 지수 데이터:", weekly_sale_df.head())
print("주간 전세 지수 데이터:", weekly_rent_df.head())
print("월간 매매 평균가 데이터:", monthly_sale_avg_df.head())
print("월간 전세 평균가 데이터:", monthly_rent_avg_df.head())

print("=========================================================================")
print("3. 월간 데이터를 주간 단위로 확장 (첫 번째 주와 병합)")


def merge_monthly_with_first_weekly(monthly_df, weekly_df):
    """월간 데이터를 주간 데이터의 첫 번째 주와 병합"""
    # 월간 데이터를 '연월'로 변환 (YYYY-MM 형식)
    monthly_df['연월'] = monthly_df['날짜'].dt.to_period('M')

    # 주간 데이터를 '연월'로 변환 (월간 데이터와 매칭하기 위해)
    weekly_df['연월'] = weekly_df['날짜'].dt.to_period('M')

    # 주간 데이터 중 각 월의 첫 번째 주 데이터만 추출
    first_weekly_df = weekly_df.drop_duplicates(subset=['지역명', '연월'], keep='first')

    # 월간 데이터를 첫 번째 주간 데이터와 병합
    # 여기서 '가격' 대신 '평균가'를 사용
    merged_df = pd.merge(first_weekly_df, monthly_df[['지역명', '연월', '평균가']], on=['지역명', '연월'], how='left',
                         suffixes=('_주간', '_월간'))

    # 불필요한 '연월' 컬럼 제거
    merged_df = merged_df.drop(columns=['연월'])

    return merged_df


# 월간 데이터를 첫 번째 주간 데이터와 병합
weekly_sale_avg = merge_monthly_with_first_weekly(monthly_sale_avg_df, weekly_sale_df)
weekly_rent_avg = merge_monthly_with_first_weekly(monthly_rent_avg_df, weekly_rent_df)

# '가격' 컬럼이 존재하는지 확인 후 이름 변경
if '지수' in weekly_sale_df.columns:
    weekly_sale_df.rename(columns={'지수': '가격_매매'}, inplace=True)
else:
    print("Error: '지수' 컬럼이 주간 매매 데이터에 존재하지 않습니다.")

if '평균가' in weekly_sale_avg.columns:
    weekly_sale_avg.rename(columns={'평균가': '평균매매가'}, inplace=True)
else:
    print("Error: '평균가' 컬럼이 월간 매매 데이터에 존재하지 않습니다.")

if '지수' in weekly_rent_df.columns:
    weekly_rent_df.rename(columns={'지수': '가격_전세'}, inplace=True)
else:
    print("Error: '지수' 컬럼이 주간 전세 데이터에 존재하지 않습니다.")

if '평균가' in weekly_rent_avg.columns:
    weekly_rent_avg.rename(columns={'평균가': '평균전세가'}, inplace=True)
else:
    print("Error: '평균가' 컬럼이 월간 전세 데이터에 존재하지 않습니다.")

print("=========================================================================")
print("4. 데이터 병합 및 DB에 삽입")


# 지역 데이터를 저장하는 함수 (지역이 없을 경우 새로 추가)
def store_region(session: Session, region_name: str):
    region = session.query(Region).filter_by(region_name=region_name).first()
    if not region:
        region = Region(region_name=region_name)
        session.add(region)
        session.commit()
        session.refresh(region)
    return region.id


# 부동산 데이터를 저장하는 함수 (중복 데이터 확인 후 삽입)
def store_property_data(session: Session, region_id: int, date: datetime, price_type: str, time_span: str,
                        index_value: float, avg_price: float = None, is_interpolated: bool = False):
    # 기존 데이터가 있는지 확인
    existing_data = session.query(PropertyPriceData).filter_by(
        region_id=region_id,
        date=date,
        price_type=price_type,
        time_span=time_span
    ).first()

    # 중복 데이터가 없을 경우 데이터 삽입
    if not existing_data:
        property_data = PropertyPriceData(
            region_id=region_id,
            date=date,
            price_type=price_type,
            time_span=time_span,
            index_value=index_value,
            avg_price=avg_price,
            is_interpolated=is_interpolated  # 보간 여부 추가
        )
        session.add(property_data)
        session.commit()
        print(f"Inserted new data for {region_id}, {date} - {price_type}, {time_span}")
    else:
        print(f"Data already exists for {region_id}, {date} - Skipping")


# 데이터를 처리하고 DB에 삽입하는 함수
def process_and_insert_data_with_interpolation(session: Session):
    # 주간 매매/전세 지수와 월간 매매/전세 평균 가격을 병합
    merged_sale_df = pd.merge(weekly_sale_df, weekly_sale_avg, on=['지역명', '날짜'], how='left')
    merged_rent_df = pd.merge(weekly_rent_df, weekly_rent_avg, on=['지역명', '날짜'], how='left')

    # 병합된 데이터를 최종적으로 병합
    merged_df = pd.merge(
        merged_sale_df,
        merged_rent_df[['지역명', '날짜', '가격_전세', '평균전세가']],
        on=['지역명', '날짜'],
        how='left',
        suffixes=('_매매', '_전세')
    )

    # NaT 값 확인 및 필터링 (날짜가 없는 행은 제외)
    merged_df = merged_df.dropna(subset=['날짜'])

    # 보간 여부를 기록할 컬럼 추가 (초기값은 False)
    merged_df['is_interpolated_매매'] = False
    merged_df['is_interpolated_전세'] = False

    # 결측치 보간 (avg_price)
    # 기준이 되는 시점(2022.1.10)을 설정하고 보간을 진행합니다.

    # 매매 평균가 보간
    merged_df['avg_price_매매'] = merged_df['평균매매가']
    merged_df['avg_price_매매'] = merged_df['avg_price_매매'].interpolate(method='linear', limit_direction='forward',
                                                                      axis=0)

    # 보간된 값이 원래 결측치였던 값이면, is_interpolated를 True로 설정
    merged_df.loc[merged_df['평균매매가'].isna(), 'is_interpolated_매매'] = True

    # 전세 평균가 보간
    merged_df['avg_price_전세'] = merged_df['평균전세가']
    merged_df['avg_price_전세'] = merged_df['avg_price_전세'].interpolate(method='linear', limit_direction='forward',
                                                                      axis=0)

    # 보간된 값이 원래 결측치였던 값이면, is_interpolated를 True로 설정
    merged_df.loc[merged_df['평균전세가'].isna(), 'is_interpolated_전세'] = True

    # 보간 결과 확인
    print("보간 결과 확인:")
    print(merged_df[['날짜', '지역명', 'avg_price_매매', 'avg_price_전세', 'is_interpolated_매매', 'is_interpolated_전세']].head())

    # 병합된 데이터를 데이터베이스에 저장
    for _, row in merged_df.iterrows():
        print(333)
        region_id = store_region(session, row['지역명'])

        # 매매 데이터 저장
        store_property_data(
            session,
            region_id,
            row['날짜'],
            '매매',
            '주간',
            row['가격_매매'],
            row['avg_price_매매'],  # 보간된 평균 매매가
            is_interpolated=row['is_interpolated_매매']  # 보간 여부를 반영
        )

        # 전세 데이터 저장
        store_property_data(
            session,
            region_id,
            row['날짜'],
            '전세',
            '주간',
            row['가격_전세'],
            row['avg_price_전세'],  # 보간된 평균 전세가
            is_interpolated=row['is_interpolated_전세']  # 보간 여부를 반영
        )

    print("모든 데이터를 성공적으로 DB에 삽입했습니다.")
