import warnings
import pandas as pd
from datetime import datetime

warnings.filterwarnings('ignore')

print("=========================================================================")
print("1. 데이터 불러오기")
print("월간 평균 매매가/전세가 데이터 선언")
monthly_sale_avg_df = pd.read_excel('data/raw/monthly_apartment_sale_cost_avg.xlsx')
monthly_rent_avg_df = pd.read_excel('data/raw/monthly_apartment_rent_cost_avg.xlsx')

print("주간 매매 지수/전세 지수 데이터 선언")
weekly_sale_index_df = pd.read_excel('data/raw/weekly_apartment_sale_index_short.xlsx')
weekly_rent_index_df = pd.read_excel('data/raw/weekly_apartment_rent_index_short.xlsx')

print("=========================================================================")
print("2. 데이터 전처리")
print("월간 데이터의 날짜 컬럼 추출 및 변환")


def preprocess_monthly_data(df):
    df_long = pd.melt(df, id_vars=['지역명'], var_name='연월', value_name='가격')
    df_long['연월'] = pd.to_datetime(df_long['연월'], format='%Y-%m', errors='coerce')
    # '가격' 컬럼을 숫자형으로 변환
    df_long['가격'] = pd.to_numeric(df_long['가격'], errors='coerce')
    return df_long


monthly_sale_long = preprocess_monthly_data(monthly_sale_avg_df)
monthly_rent_long = preprocess_monthly_data(monthly_rent_avg_df)

print("주간 데이터의 날짜 컬럼 추출 및 변환")


def preprocess_weekly_data(df):
    df_long = pd.melt(df, id_vars=['지역명'], var_name='날짜', value_name='지수')
    df_long['날짜'] = pd.to_datetime(df_long['날짜'], format='%y.%m.%d', errors='coerce')
    # '지수' 컬럼을 숫자형으로 변환
    df_long['지수'] = pd.to_numeric(df_long['지수'], errors='coerce')
    return df_long


weekly_sale_long = preprocess_weekly_data(weekly_sale_index_df)
weekly_rent_long = preprocess_weekly_data(weekly_rent_index_df)

print("날짜 컬럼에서 시간 부분 제거")


def remove_time(df, date_col):
    df[date_col] = df[date_col].dt.normalize()
    return df


weekly_sale_long = remove_time(weekly_sale_long, '날짜')
weekly_rent_long = remove_time(weekly_rent_long, '날짜')

print("지역명 컬럼의 공백 제거")


def clean_region_name(df):
    df['지역명'] = df['지역명'].str.strip()
    return df


weekly_sale_long = clean_region_name(weekly_sale_long)
weekly_rent_long = clean_region_name(weekly_rent_long)
monthly_sale_long = clean_region_name(monthly_sale_long)
monthly_rent_long = clean_region_name(monthly_rent_long)

print("=========================================================================")
print("3. 월간 데이터를 주간 단위로 변환")
weekly_dates = weekly_sale_long['날짜'].drop_duplicates().sort_values()


def expand_monthly_to_weekly(monthly_df):
    monthly_df['연월'] = monthly_df['연월'].dt.to_period('M')
    weekly_df_list = []
    for region in monthly_df['지역명'].unique():
        region_monthly = monthly_df[monthly_df['지역명'] == region]
        region_weekly = pd.DataFrame({'날짜': weekly_dates})
        region_weekly['연월'] = region_weekly['날짜'].dt.to_period('M')
        region_weekly['지역명'] = region
        region_monthly = region_monthly.set_index('연월')
        region_weekly = region_weekly.join(region_monthly['가격'], on='연월')
        region_monthly_next = region_monthly.shift(-1)
        region_monthly_next = region_monthly_next.rename(columns={'가격': '가격_다음달'})
        region_weekly = region_weekly.join(region_monthly_next['가격_다음달'], on='연월')
        region_weekly['가격'] = region_weekly['가격'].fillna(method='ffill')
        region_weekly['가격_다음달'] = region_weekly['가격_다음달'].fillna(region_weekly['가격'])
        total_weeks = region_weekly.groupby('연월')['날짜'].transform('count') - 1
        week_number = region_weekly.groupby('연월').cumcount()
        region_weekly['가격'] = region_weekly['가격'] + \
                              (region_weekly['가격_다음달'] - region_weekly['가격']) * week_number / total_weeks
        weekly_df_list.append(region_weekly[['지역명', '날짜', '가격']])
    weekly_df = pd.concat(weekly_df_list, ignore_index=True)
    return weekly_df


weekly_sale_avg = expand_monthly_to_weekly(monthly_sale_long)
weekly_rent_avg = expand_monthly_to_weekly(monthly_rent_long)

weekly_sale_avg.rename(columns={'가격': '평균매매가'}, inplace=True)
weekly_rent_avg.rename(columns={'가격': '평균전세가'}, inplace=True)

print("=========================================================================")
print("4. 데이터 병합")
merged_sale_df = pd.merge(weekly_sale_long, weekly_sale_avg, on=['지역명', '날짜'], how='left')
merged_rent_df = pd.merge(weekly_rent_long, weekly_rent_avg, on=['지역명', '날짜'], how='left')

merged_df = pd.merge(
    merged_sale_df,
    merged_rent_df[['지역명', '날짜', '지수', '평균전세가']],
    on=['지역명', '날짜'],
    how='left',
    suffixes=('_매매', '_전세')
)

# print("=========================================================================")
# print("5. 실제 매매가/전세가 계산")
# merged_df['실제매매가'] = (merged_df['지수_매매'] / 100) * merged_df['평균매매가']
# merged_df['실제전세가'] = (merged_df['지수_전세'] / 100) * merged_df['평균전세가']

print("=========================================================================")
print("6. 결과 저장")
# result_df = merged_df[['지역명', '날짜', '지수_매매', '지수_전세', '평균매매가', '평균전세가', '실제매매가', '실제전세가']]
result_df = merged_df[['지역명', '날짜', '지수_매매', '지수_전세', '평균매매가', '평균전세가']]

print("시트 순서 지정")
sheet_order = ['전국', '서울', '강북14개구', '종로구', '중구', '용산구', '성동구', '광진구', '동대문구',
               '중랑구', '성북구', '강북구', '도봉구', '노원구', '은평구', '서대문구', '마포구', '강남11개구',
               '양천구', '강서구', '구로구', '금천구', '영등포구', '동작구', '관악구', '서초구', '강남구',
               '송파구', '강동구', '수도권']

print("엑셀로 저장")
now = datetime.now().strftime('%Y%m%d%H%M')

with pd.ExcelWriter(f'data/processed/{now}_result.xlsx', engine='xlsxwriter') as writer:
    for region in sheet_order:
        region_df = result_df[result_df['지역명'] == region].sort_values('날짜').reset_index(drop=True)
        if not region_df.empty:
            # '지역명' 컬럼 제거
            region_df = region_df.drop(columns=['지역명'])
            # 시트 이름에서 허용되지 않는 문자 제거
            valid_sheet_name = ''.join(char for char in region if char not in ('\\', '/', '*', '?', ':', '[', ']'))
            region_df.to_excel(writer, sheet_name=valid_sheet_name, index=False)
    # sheet_order에 없는 나머지 지역 처리 (선택 사항)
    other_regions = [region for region in result_df['지역명'].unique() if region not in sheet_order]
    for region in other_regions:
        region_df = result_df[result_df['지역명'] == region].sort_values('날짜').reset_index(drop=True)
        if not region_df.empty:
            # '지역명' 컬럼 제거
            region_df = region_df.drop(columns=['지역명'])
            valid_sheet_name = ''.join(char for char in region if char not in ('\\', '/', '*', '?', ':', '[', ']'))
            region_df.to_excel(writer, sheet_name=valid_sheet_name, index=False)

print("=========================================================================")
