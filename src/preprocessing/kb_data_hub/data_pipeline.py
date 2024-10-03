from src.preprocessing.kb_data_hub.api_integration import process_and_insert_data_with_interpolation
from src.preprocessing.kb_data_hub.data_filling import fill_avg_price_with_index_based_calculation
from src.database.database import SessionLocal


def run_pipeline():
    session = SessionLocal()  # DB 세션 생성
    try:
        # 1. API 데이터 수집 및 DB 삽입 실행
        process_and_insert_data_with_interpolation(session)
        print("API 데이터를 성공적으로 처리하고 DB에 저장했습니다.")

        # 2. NaN avg_price 값 보강
        fill_avg_price_with_index_based_calculation(session)
        print("NaN avg_price 데이터를 지수 기반으로 보강 완료했습니다.")
    except Exception as e:
        print(f"데이터 처리 중 오류 발생: {e}")
    finally:
        session.close()  # 세션 종료


if __name__ == "__main__":
    run_pipeline()
