from sqlalchemy.orm import Session
from src.database.models.kb_real_estate_data_hub import PropertyPriceData, Prediction, Region
import pandas as pd


# 영문 price_type을 한글로 변환하는 함수
def convert_price_type_to_korean(price_type):
    if price_type == 'rent':
        return '전세'
    elif price_type == 'sale':
        return '매매'
    return price_type  # 변환이 필요 없는 경우 그대로 반환


# 가격을 억 단위와 만 단위로 변환하는 함수
def format_price_in_krw(price):
    price_rounded = round(price)  # 소수점 반올림
    # 억 단위 계산
    billion_part = price_rounded // 10000
    # 만 단위 계산
    ten_thousand_part = price_rounded % 10000
    if billion_part > 0:
        return f"{billion_part}억 {ten_thousand_part:,}만원"
    else:
        return f"{ten_thousand_part:,}만원"


# 질문-답변 쌍을 생성하는 함수 (request -> input, response -> bot_output)
def generate_qa_pairs(row, is_prediction=False):
    region = row.region.region_name_kor
    price_type = convert_price_type_to_korean(row.price_type)  # price_type 변환
    price = row.predicted_price if is_prediction else row.avg_price
    date = row.date.strftime('%Y년 %m월 %d일')  # date 포맷 변환

    # 가격을 억 단위와 만 단위로 변환
    price_formatted = format_price_in_krw(price) if price is not None else "정보 없음"

    if is_prediction:
        input_text = f"{region}의 {date} 기준 {price_type} 예측 가격은 얼마인가요?"
        bot_output = f"{region}의 {date} 기준 {price_type} 예측 가격은 {price_formatted}입니다~두껍!"
    else:
        input_text = f"{region}의 {date} 기준 {price_type} 가격은 얼마인가요?"
        bot_output = f"{region}의 {date} 기준 {price_type} 가격은 {price_formatted}입니다~두껍!"

    return input_text, bot_output


# 데이터베이스에서 질문-답변 쌍 생성 함수
def generate_qa_from_db(session: Session):
    qa_pairs = []

    # 과거 부동산 가격 데이터 가져오기
    price_data = session.query(PropertyPriceData).join(Region).all()
    for data in price_data:
        if data.avg_price is not None:
            qa_pairs.append(generate_qa_pairs(data, is_prediction=False))

    # 예측 부동산 데이터 가져오기
    prediction_data = session.query(Prediction).join(Region).all()
    for data in prediction_data:
        if data.predicted_price is not None:
            qa_pairs.append(generate_qa_pairs(data, is_prediction=True))

    return qa_pairs


# CSV로 저장하는 함수 (input, bot_output 컬럼명으로 변경)
def save_qa_to_csv(qa_pairs):
    qa_df = pd.DataFrame(qa_pairs, columns=['input', 'bot_output'])
    qa_df.to_csv('datasets/qa_data/real_estate_qa_dataset_from_db.csv', index=False)
    print("Dataset saved as real_estate_qa_dataset_from_db.csv")