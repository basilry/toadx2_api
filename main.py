# # 사용자가 제공한 SOUTH_KOREA_PROVINCE_NAME을 참조하여 엑셀 데이터를 처리하는 코드 작성
# import pandas as pd
# import numpy as np
#
# # 파일 경로
# bargain_index_path = 'weekly_apartment_bargain_index_short.xlsx'
# charter_index_path = 'weekly_apartment_charter_index_short.xlsx'
#
# # 엑셀 데이터 불러오기
# bargain_df = pd.read_excel(bargain_index_path)
# charter_df = pd.read_excel(charter_index_path)
#
# # SOUTH_KOREA_PROVINCE_NAME 목록 (상위 행정구역)
# SOUTH_KOREA_PROVINCE_NAME = ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
#                              '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주']
#
# # 1. 데이터 롱 포맷으로 변환 (Wide to Long)
# bargain_long = pd.melt(bargain_df, id_vars=["지역명"], var_name="날짜", value_name="매매가")
# charter_long = pd.melt(charter_df, id_vars=["지역명"], var_name="날짜", value_name="전세가")
#
# # 2. '날짜' 컬럼을 datetime 형식으로 변환
# bargain_long['날짜'] = pd.to_datetime(bargain_long['날짜'], errors='coerce')
# charter_long['날짜'] = pd.to_datetime(charter_long['날짜'], errors='coerce')
#
# # 3. '지역명'과 '날짜'를 기준으로 두 데이터 병합
# merged_df = pd.merge(bargain_long, charter_long, on=["지역명", "날짜"], how="inner")
#
# # 4. 상위 행정구역(시)를 추출하고 '시', '군', '구'로 구분하는 함수 작성
# def extract_province_info(row, current_province):
#     region = row['지역명']
#
#     # 'SOUTH_KOREA_PROVINCE_NAME'에 있는 경우 해당 지역명을 '시'로 설정
#     if any(province in region for province in SOUTH_KOREA_PROVINCE_NAME):
#         current_province = region
#         si = region
#         gun = np.nan  # 군은 없는 경우
#         gu = np.nan   # 구는 없는 경우
#
#     # '구'를 포함하는 지역이면 구로 분류
#     elif '구' in region:
#         si = current_province
#         gun = np.nan  # 군은 없는 경우
#         gu = region
#
#     # '군'을 포함하는 경우 군으로 분류
#     elif '군' in region:
#         si = current_province
#         gun = region
#         gu = np.nan  # 구는 없는 경우
#
#     else:
#         si = current_province
#         gun = np.nan
#         gu = np.nan
#
#     return pd.Series([si, gun, gu])
#
# # 5. 현재 '시' 정보를 저장할 변수
# current_province = None
#
# # 6. '시', '군', '구' 컬럼을 추가하기 위해 함수를 적용
# merged_df[['시', '군', '구']] = merged_df.apply(lambda row: extract_province_info(row, current_province), axis=1)
#
# # 7. 순번 추가
# merged_df['순번'] = range(1, len(merged_df) + 1)
#
# # 8. 필요한 컬럼만 선택하여 새로운 데이터프레임 생성
# final_df_with_provinces = merged_df[['순번', '날짜', '시', '군', '구', '매매가', '전세가']]
#
# # 9. 엑셀 파일로 저장
# final_xlsx_output_path_with_provinces = 'result/merged_real_estate_with_provinces.xlsx'
# final_df_with_provinces.to_excel(final_xlsx_output_path_with_provinces, index=False)
#
# # 파일 경로 반환
# final_xlsx_output_path_with_provinces


import pandas as pd
import numpy as np

# 엑셀 데이터 불러오기
bargain_df = pd.read_excel('weekly_apartment_bargain_index.xlsx')
charter_df = pd.read_excel('weekly_apartment_charter_index.xlsx')

# SOUTH_KOREA_PROVINCE_NAME 목록 (상위 행정구역)
SEOUL_GANGBUK = ['종로구', '중구', '용산구', '성동구', '광진구', '동대문구', '중랑구', '성북구', '강북구', '도봉구', '노원구', '은평구', '서대문구', '마포구']
SEOUL_GANGNAM = ['강남구', '서초구', '송파구', '강동구', '동작구', '관악구', '영등포구', '양천구', '강서구', '구로구', '금천구']
CAPITAL_REGION = ['경기', '인천']

# 1. 데이터 롱 포맷으로 변환 (Wide to Long)
bargain_long = pd.melt(bargain_df, id_vars=["지역명"], var_name="날짜", value_name="매매가")
charter_long = pd.melt(charter_df, id_vars=["지역명"], var_name="날짜", value_name="전세가")

# 2. '날짜' 컬럼을 datetime 형식으로 변환 및 시간 제거 (YYYY-MM-DD 포맷)
bargain_long['날짜'] = pd.to_datetime(bargain_long['날짜'], errors='coerce').dt.date
charter_long['날짜'] = pd.to_datetime(charter_long['날짜'], errors='coerce').dt.date

# 3. '지역명'과 '날짜'를 기준으로 두 데이터 병합
merged_df = pd.merge(bargain_long, charter_long, on=["지역명", "날짜"], how="inner")


# 4. '그 외' 컬럼 추가 ('강북14개구', '강남11개구', '수도권' 구분)
def categorize_region(row):
    region = row['지역명']
    if region in SEOUL_GANGBUK:
        return '강북14개구'
    elif region in SEOUL_GANGNAM:
        return '강남11개구'
    elif any(province in region for province in CAPITAL_REGION):
        return '수도권'
    else:
        return '기타'


merged_df['그 외'] = merged_df.apply(categorize_region, axis=1)

# 5. '군' 컬럼 제거, 필요한 컬럼만 남기기
merged_df = merged_df[['날짜', '지역명', '그 외', '매매가', '전세가']]

# 6. 각 지역별로 데이터를 분리하여 엑셀 시트에 저장
with pd.ExcelWriter('result/regional_real_estate_data.xlsx', engine='xlsxwriter') as writer:
    # 강북 14개구 시트
    gangbuk_df = merged_df[merged_df['그 외'] == '강북14개구']
    gangbuk_df.to_excel(writer, sheet_name='강북14개구', index=False)

    # 강남 11개구 시트
    gangnam_df = merged_df[merged_df['그 외'] == '강남11개구']
    gangnam_df.to_excel(writer, sheet_name='강남11개구', index=False)

    # 수도권 시트
    capital_region_df = merged_df[merged_df['그 외'] == '수도권']
    capital_region_df.to_excel(writer, sheet_name='수도권', index=False)

    # 기타 시트 (서울 수도권 외의 지역)
    etc_df = merged_df[merged_df['그 외'] == '기타']
    etc_df.to_excel(writer, sheet_name='기타', index=False)
