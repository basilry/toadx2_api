import pandas as pd
from sqlalchemy.orm import Session
from src.database.database import engine
from src.database.models.kb_real_estate_data_hub import LegalDongCode

# 파일 경로
file_path = 'datasets/ministry_of_land/legal_dong_list.txt'

# Step 1: 법정동 코드 파일 읽기
def load_legal_dong_codes(file_path):
    # 텍스트 파일을 DataFrame으로 읽기 (탭으로 구분된 데이터, 인코딩은 cp949 시도)
    try:
        df = pd.read_csv(file_path, delimiter='\t', dtype=str, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, delimiter='\t', dtype=str, encoding='cp949')

    # 필요한 컬럼만 선택 (법정동 코드, 이름, 폐지 여부)
    df = df[['법정동코드', '법정동명', '폐지여부']]

    # 폐지여부가 '존재'이면 True, '폐지'이면 False로 변환
    df['is_active'] = df['폐지여부'].apply(lambda x: True if x == '존재' else False)

    # 컬럼명 변경
    df = df.rename(columns={'법정동코드': 'code', '법정동명': 'name'})

    return df

# Step 2: 데이터베이스에 삽입
def insert_legal_dong_codes(df):
    session = Session(bind=engine)

    try:
        for _, row in df.iterrows():
            # LegalDongCode 인스턴스 생성
            dong_code = LegalDongCode(
                code=row['code'],
                name=row['name'],
                is_active=row['is_active']
            )

            # 세션에 추가
            session.add(dong_code)

        # 데이터베이스에 커밋
        session.commit()
        print("데이터 삽입 완료!")

    except Exception as e:
        session.rollback()  # 오류 발생 시 롤백
        print(f"오류 발생: {e}")

    finally:
        session.close()  # 세션 종료

# 전체 파이프라인 실행
if __name__ == "__main__":
    # Step 1: 파일에서 법정동 코드 로드
    df = load_legal_dong_codes(file_path)

    # Step 2: 데이터베이스에 삽입
    insert_legal_dong_codes(df)
