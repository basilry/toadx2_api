from src.preprocessing.kor_conversation_based_db.real_estate_qa_transform import generate_qa_from_db, save_qa_to_csv
from src.database.database import SessionLocal


def generate_and_save_qa_data():
    """질문-답변 쌍 생성 및 CSV 저장"""
    session = SessionLocal()  # DB 세션 생성
    try:
        # DB에서 질문-답변 쌍 생성
        qa_pairs = generate_qa_from_db(session)
        # CSV로 저장
        save_qa_to_csv(qa_pairs)
        print("질문-답변 데이터셋을 성공적으로 생성하고 저장했습니다.")
    except Exception as e:
        print(f"질문-답변 데이터 생성 중 오류 발생: {e}")
    finally:
        session.close()  # 세션 종료


def run_qa_pipeline():
    """질문-답변 파이프라인 실행"""
    generate_and_save_qa_data()  # 질문-답변 생성 및 저장


if __name__ == "__main__":
    run_qa_pipeline()
