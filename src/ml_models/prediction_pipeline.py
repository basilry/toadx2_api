from sqlalchemy.orm import Session
from src.ml_models.prediction_service import run_prophet_model, save_predictions
from src.database.models.kb_real_estate_data_hub import PropertyPriceData, Region
import pandas as pd


def get_region_data(session: Session, region_id: int, price_type: str, time_span: str):
    """
    특정 지역의 주간 또는 월간 데이터를 불러오는 함수
    """
    data = session.query(PropertyPriceData).filter_by(region_id=region_id, price_type=price_type,
                                                      time_span=time_span).all()
    df = pd.DataFrame([(d.date, d.index_value) for d in data], columns=['ds', 'y'])
    return df


def run_prediction_pipeline(session: Session):
    """
    전체 지역에 대해 예측 파이프라인을 실행하는 함수
    """
    regions = session.query(Region).all()

    for region in regions:
        # 1. 주간 매매 가격 예측
        weekly_sale_data = get_region_data(session, region.id, "매매", "주간")
        if not weekly_sale_data.empty:
            weekly_sale_forecast = run_prophet_model(weekly_sale_data, "매매", "주간")
            save_predictions(session, weekly_sale_forecast, region.id, "매매", "주간")

        # 2. 주간 전세 가격 예측
        weekly_rent_data = get_region_data(session, region.id, "전세", "주간")
        if not weekly_rent_data.empty:
            weekly_rent_forecast = run_prophet_model(weekly_rent_data, "전세", "주간")
            save_predictions(session, weekly_rent_forecast, region.id, "전세", "주간")

        # 3. 월간 매매 가격 예측
        monthly_sale_data = get_region_data(session, region.id, "매매", "월간")
        if not monthly_sale_data.empty:
            monthly_sale_forecast = run_prophet_model(monthly_sale_data, "매매", "월간")
            save_predictions(session, monthly_sale_forecast, region.id, "매매", "월간")

        # 4. 월간 전세 가격 예측
        monthly_rent_data = get_region_data(session, region.id, "전세", "월간")
        if not monthly_rent_data.empty:
            monthly_rent_forecast = run_prophet_model(monthly_rent_data, "전세", "월간")
            save_predictions(session, monthly_rent_forecast, region.id, "전세", "월간")

    print("All predictions have been processed.")
