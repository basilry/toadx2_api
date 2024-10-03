from sqlalchemy.orm import Session
from datetime import datetime
from src.database.models.kb_real_estate_data_hub import PropertyPriceData, Region, Prediction

# 데이터베이스 세션 가져오기
# `session`은 SQLAlchemy 세션을 의미하며, 데이터베이스와 상호작용을 합니다.

def generate_qa_from_db(session: Session):
    # 질문-답변 쌍을 저장할 리스트
    qa_pairs = []

    # 1. 지역별 부동산 가격 데이터를 조회
    price_data = session.query(PropertyPriceData).join(Region).all()

    print(price_data)

    # 2. 가격 데이터를 바탕으로 질문-답변 생성
    for data in price_data:
        region_name = data.region.region_name_kor  # 지역명
        price_type = data.price_type  # 매매 또는 전세
        avg_price = data.avg_price  # 평균 가격
        date = data.date  # 날짜

        # 질문과 답변 생성
        question = f"{region_name}의 {date.strftime('%Y-%m-%d')} 기준 {price_type} 가격은 얼마인가요?"
        answer = f"{region_name}의 {date.strftime('%Y-%m-%d')} 기준 {price_type} 가격은 {avg_price}만원입니다~두껍!"

        # 리스트에 추가
        qa_pairs.append((question, answer))

    # 3. 예측 데이터를 바탕으로 추가 질문-답변 생성
    prediction_data = session.query(Prediction).join(Region).all()

    for data in prediction_data:
        region_name = data.region.region_name_kor  # 지역명
        price_type = data.price_type  # 매매 또는 전세
        predicted_price = data.predicted_price  # 예측된 가격
        date = data.date  # 예측 날짜

        # 예측 질문과 답변 생성
        question = f"{region_name}의 {date.strftime('%Y-%m-%d')} 기준 {price_type} 예측 가격은 얼마인가요?"
        answer = f"{region_name}의 {date.strftime('%Y-%m-%d')} 기준 {price_type} 예측 가격은 {predicted_price}만원입니다~두껍!"

        # 리스트에 추가
        qa_pairs.append((question, answer))

    return qa_pairs

# 생성된 질문-답변 쌍을 CSV 파일로 저장
def save_qa_to_csv(qa_pairs):
    import pandas as pd
    qa_df = pd.DataFrame(qa_pairs, columns=['질문', '답변'])
    qa_df.to_csv('real_estate_qa_dataset_from_db.csv', index=False)
    print("Dataset saved as real_estate_qa_dataset_from_db.csv")

# 예시 세션 생성 및 실행
# with Session(engine) as session:
#     qa_pairs = generate_qa_from_db(session)
#     save_qa_to_csv(qa_pairs)
