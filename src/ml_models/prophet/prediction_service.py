from prophet import Prophet
import pandas as pd
from sqlalchemy.orm import Session
from src.database.models.database_model import Prediction


# 데이터 처리 및 예측 함수
def run_prophet_model(data: pd.DataFrame, price_type: str, time_span: str):
    """
    prophet 모델을 사용하여 예측을 실행하는 함수
    data: 예측할 데이터프레임 (날짜, 가격 지수)
    price_type: 매매 또는 전세
    time_span: 주간 또는 월간
    """
    model = Prophet(daily_seasonality=False, weekly_seasonality=True if time_span == '주간' else False,
                    yearly_seasonality=True)
    model.fit(data[['ds', 'y']])

    future = model.make_future_dataframe(periods=12, freq='W' if time_span == '주간' else 'M')
    forecast = model.predict(future)
    return forecast[['ds', 'yhat']]


# 예측 결과 저장
def save_predictions(session: Session, predictions: pd.DataFrame, region_id: int, price_type: str, time_span: str):
    """
    예측 결과를 DB에 저장하는 함수
    predictions: prophet 모델의 예측 결과
    region_id: 예측한 지역의 ID
    price_type: 매매 또는 전세
    time_span: 주간 또는 월간
    """
    for index, row in predictions.iterrows():
        prediction = Prediction(
            region_id=region_id,
            date=row['ds'],
            price_type=price_type,
            time_span=time_span,
            predicted_value=row['yhat']
        )
        session.add(prediction)
    session.commit()
    print(f"Predictions saved for region_id: {region_id}, {price_type}, {time_span}")
