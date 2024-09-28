import pandas as pd
from sqlalchemy.orm import Session
from src.preprocessing.data_cleaning import clean_date_column, clean_region_name, remove_time
from src.preprocessing.data_transform import expand_monthly_to_weekly, merge_weekly_and_monthly
from src.api.services.data_service import insert_property_price_data


def process_and_insert_data(session: Session):
    """
    엑셀 파일을 불러와 전처리한 후 데이터베이스에 삽입합니다.
    """
    print("데이터 불러오기...")
    # 월간 평균 매매가 및 전세가 데이터
    monthly_sale_avg_df = pd.read_excel('data/raw/monthly_apartment_sale_cost_avg.xlsx')
    monthly_rent_avg_df = pd.read_excel('data/raw/monthly_apartment_rent_cost_avg.xlsx')

    # 주간 매매 및 전세 지수 데이터
    weekly_sale_index_df = pd.read_excel('data/raw/weekly_apartment_sale_index_short.xlsx')
    weekly_rent_index_df = pd.read_excel('data/raw/weekly_apartment_rent_index_short.xlsx')

    print("데이터 전처리 중...")
    # 데이터 클리닝
    monthly_sale_avg_df = clean_region_name(monthly_sale_avg_df)
    monthly_rent_avg_df = clean_region_name(monthly_rent_avg_df)
    weekly_sale_index_df = clean_region_name(weekly_sale_index_df)
    weekly_rent_index_df = clean_region_name(weekly_rent_index_df)

    # 주간 날짜 생성
    weekly_dates = weekly_sale_index_df['날짜'].drop_duplicates().sort_values()

    # 월간 데이터를 주간 데이터로 변환
    print("월간 데이터를 주간 데이터로 변환 중...")
    weekly_sale_avg = expand_monthly_to_weekly(monthly_sale_avg_df, weekly_dates)
    weekly_rent_avg = expand_monthly_to_weekly(monthly_rent_avg_df, weekly_dates)

    # 주간/월간 데이터 병합
    print("주간/월간 데이터 병합 중...")
    merged_df = merge_weekly_and_monthly(weekly_sale_index_df, weekly_rent_index_df, weekly_sale_avg, weekly_rent_avg)

    # 데이터베이스에 삽입
    print("데이터베이스에 삽입 중...")
    insert_property_price_data(merged_df.to_dict(orient='records'), session)
