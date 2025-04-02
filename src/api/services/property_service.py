from datetime import datetime, timedelta
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from src.database.models.database_model import PropertyPriceData, Prediction, Region

# 부동산 가격 데이터 조회 함수
def get_property_price(region_name: str, price_type: str, date_info: str, db: Session):
    if "month" in date_info:
        # ... 기존 코드 유지
        pass
    else:
        try:
            # "현재"인 경우 오늘 날짜 기준 한 달 전후로 설정
            if date_info == "현재":
                today = datetime.now().date()
                target_date = today - timedelta(days=30)  # 1달 전
                end_date = today + timedelta(days=30)     # 1달 후
                print(f"현재 날짜 기준 데이터 조회: 시작일={target_date}, 종료일={end_date}")
            else:
                # date_info가 구체적인 날짜인 경우
                target_date = datetime.strptime(date_info, "%Y-%m-%d").date()
                end_date = target_date + timedelta(days=90)  # 3개월 후

            # 지역 이름으로 지역 코드 찾기
            regions = [region_name]
            print(f"매매가 안쪽 {regions} {price_type}")
            
            # 실제 데이터 쿼리 (kb_property_price_data)
            actual_query = (
                select(PropertyPriceData)
                .join(Region, PropertyPriceData.region_code == Region.region_code)
                .where(
                    or_(*[Region.region_name_kor.like(f"%{name}%") for name in regions]),
                    PropertyPriceData.price_type == price_type,
                    PropertyPriceData.date >= target_date,
                    PropertyPriceData.date <= end_date
                )
            )
            
            actual_results = db.execute(actual_query).scalars().all()
            
            # 예측 데이터 쿼리 (kb_prediction)
            prediction_query = (
                select(Prediction)
                .join(Region, Prediction.region_code == Region.region_code)
                .where(
                    or_(*[Region.region_name_kor.like(f"%{name}%") for name in regions]),
                    Prediction.price_type == price_type,
                    Prediction.date >= target_date,
                    Prediction.date <= end_date
                )
            )
            
            prediction_results = db.execute(prediction_query).scalars().all()
            
            # 결과를 딕셔너리로 변환 (날짜를 키로 사용)
            data_dict = {}
            
            # 실제 데이터 먼저 추가 (우선순위가 높음)
            for row in actual_results:
                date_str = row.date.strftime('%Y-%m-%d')
                data_dict[date_str] = {
                    'region': row.region_code,
                    'date': date_str,
                    'deal_type': row.price_type,
                    'price': row.avg_price,
                    'is_prediction': False
                }
            
            # 예측 데이터 추가 (실제 데이터와 중복되지 않는 날짜만)
            for row in prediction_results:
                date_str = row.date.strftime('%Y-%m-%d')
                if date_str not in data_dict:
                    price_value = row.predicted_price if row.predicted_price is not None else 0
                    data_dict[date_str] = {
                        'region': row.region_code,
                        'date': date_str,
                        'deal_type': row.price_type,
                        'price': price_value,
                        'is_prediction': True
                    }
            
            # 딕셔너리를 리스트로 변환
            data = list(data_dict.values())
            
            # 평균 가격 계산
            total_price = sum(item['price'] for item in data) if data else 0
            avg_price = total_price / len(data) if data else 0
            
            print(f"쿼리결과: {data}")
            return data, avg_price
            
        except Exception as e:
            print(f"데이터 처리 중 오류 발생: {e}")
            # 오류가 발생해도 빈 결과 대신 다시 시도
            try:
                today = datetime.now().date()
                start_date = today - timedelta(days=30)  # 1달 전
                end_date = today + timedelta(days=30)    # 1달 후
                print(f"오류 발생으로 현재 기준 데이터 조회: 시작일={start_date}, 종료일={end_date}")
                
                # 실제 데이터 쿼리 (kb_property_price_data)
                actual_query = (
                    select(PropertyPriceData)
                    .join(Region, PropertyPriceData.region_code == Region.region_code)
                    .where(
                        or_(*[Region.region_name_kor.like(f"%{name}%") for name in regions]),
                        PropertyPriceData.price_type == price_type,
                        PropertyPriceData.date >= start_date,
                        PropertyPriceData.date <= end_date
                    )
                )
                
                actual_results = db.execute(actual_query).scalars().all()
                
                # 예측 데이터 쿼리 (kb_prediction)
                prediction_query = (
                    select(Prediction)
                    .join(Region, Prediction.region_code == Region.region_code)
                    .where(
                        or_(*[Region.region_name_kor.like(f"%{name}%") for name in regions]),
                        Prediction.price_type == price_type,
                        Prediction.date >= start_date,
                        Prediction.date <= end_date
                    )
                )
                
                prediction_results = db.execute(prediction_query).scalars().all()
                
                # 결과를 딕셔너리로 변환 (날짜를 키로 사용)
                data_dict = {}
                
                # 실제 데이터 먼저 추가 (우선순위가 높음)
                for row in actual_results:
                    date_str = row.date.strftime('%Y-%m-%d')
                    data_dict[date_str] = {
                        'region': row.region_code,
                        'date': date_str,
                        'deal_type': row.price_type,
                        'price': row.avg_price,
                        'is_prediction': False
                    }
                
                # 예측 데이터 추가 (실제 데이터와 중복되지 않는 날짜만)
                for row in prediction_results:
                    date_str = row.date.strftime('%Y-%m-%d')
                    if date_str not in data_dict:
                        price_value = row.predicted_price if row.predicted_price is not None else 0
                        data_dict[date_str] = {
                            'region': row.region_code,
                            'date': date_str,
                            'deal_type': row.price_type,
                            'price': price_value,
                            'is_prediction': True
                        }
                
                # 딕셔너리를 리스트로 변환
                data = list(data_dict.values())
                
                # 평균 가격 계산
                total_price = sum(item['price'] for item in data)
                avg_price = total_price / len(data) if data else 0
                
                print(f"쿼리결과(오류 복구): {data}")
                return data, avg_price
            except Exception as nested_e:
                print(f"복구 시도 중 추가 오류 발생: {nested_e}")
                return [], 0 