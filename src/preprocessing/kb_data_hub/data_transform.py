import pandas as pd
from sqlalchemy.orm import Session


# 월간 데이터를 주간 데이터로 변환
def expand_monthly_to_weekly(monthly_df, weekly_dates):
    """
    월간 데이터를 주간 데이터로 확장합니다.
    주간 날짜가 월간 데이터에 해당하는 값을 받으며, 결측치는 선형 보간 방식으로 처리합니다.
    """
    monthly_df['연월'] = monthly_df['연월'].dt.to_period('M')
    weekly_df_list = []

    for region in monthly_df['지역명'].unique():
        region_monthly = monthly_df[monthly_df['지역명'] == region]
        region_weekly = pd.DataFrame({'날짜': weekly_dates})
        region_weekly['연월'] = region_weekly['날짜'].dt.to_period('M')
        region_weekly['지역명'] = region

        # 월간 데이터와 주간 데이터 병합
        region_monthly = region_monthly.set_index('연월')
        region_weekly = region_weekly.join(region_monthly['가격'], on='연월')

        # 다음 달 데이터를 가져와서 선형 보간
        region_monthly_next = region_monthly.shift(-1)
        region_monthly_next = region_monthly_next.rename(columns={'가격': '가격_다음달'})
        region_weekly = region_weekly.join(region_monthly_next['가격_다음달'], on='연월')

        # 첫 번째 주차의 가격을 채우고 나머지를 선형 보간
        region_weekly['가격'] = region_weekly['가격'].fillna(method='ffill')
        region_weekly['가격_다음달'] = region_weekly['가격_다음달'].fillna(region_weekly['가격'])
        total_weeks = region_weekly.groupby('연월')['날짜'].transform('count') - 1
        week_number = region_weekly.groupby('연월').cumcount()

        # 주차별로 가격을 선형적으로 계산
        region_weekly['가격'] = region_weekly['가격'] + \
                              (region_weekly['가격_다음달'] - region_weekly['가격']) * week_number / total_weeks

        weekly_df_list.append(region_weekly[['지역명', '날짜', '가격']])

    # 주간 데이터 통합
    weekly_df = pd.concat(weekly_df_list, ignore_index=True)
    return weekly_df


# 주간/월간 데이터 병합
def merge_weekly_and_monthly(weekly_sale_long, weekly_rent_long, weekly_sale_avg, weekly_rent_avg):
    """
    주간 데이터와 월간 데이터를 병합합니다.
    """
    weekly_sale_avg.rename(columns={'가격': '평균매매가'}, inplace=True)
    weekly_rent_avg.rename(columns={'가격': '평균전세가'}, inplace=True)

    # 주간 매매 및 전세 지수 데이터와 평균 가격 데이터 병합
    merged_sale_df = pd.merge(weekly_sale_long, weekly_sale_avg, on=['지역명', '날짜'], how='left')
    merged_rent_df = pd.merge(weekly_rent_long, weekly_rent_avg, on=['지역명', '날짜'], how='left')

    # 매매와 전세 데이터를 하나의 데이터프레임으로 병합
    merged_df = pd.merge(
        merged_sale_df,
        merged_rent_df[['지역명', '날짜', '지수', '평균전세가']],
        on=['지역명', '날짜'],
        how='left',
        suffixes=('_매매', '_전세')
    )

    return merged_df
