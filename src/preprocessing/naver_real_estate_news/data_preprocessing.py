from sqlalchemy.orm import Session
from src.database.models.database_model import NewsArticle  # 뉴스 기사 테이블
from src.database.database import get_db


# 데이터 전처리 함수
def clean_text(text: str) -> str:
    # 개행 문자 및 불필요한 공백 제거
    text = text.replace("\n", " ").replace("\r", " ").strip()
    # 다중 공백을 단일 공백으로 변환
    text = ' '.join(text.split())
    return text


# DB에서 뉴스 데이터를 조회하고 전처리하는 함수
def process_news_articles(db: Session):
    # 모든 뉴스 기사를 가져옴
    news_articles = db.query(NewsArticle).all()

    # 각 뉴스 기사에 대해 전처리 수행
    for article in news_articles:
        # 전처리
        article.title = clean_text(article.title)
        article.summary = clean_text(article.summary)
        article.content = clean_text(article.content)

        # 변경 사항을 DB에 저장
        db.commit()

    print(f"총 {len(news_articles)}개의 뉴스 기사가 전처리되었습니다.")


# 전처리 파이프라인 실행 함수
def run_preprocessing_pipeline():
    db = next(get_db())  # DB 세션 가져오기
    process_news_articles(db)  # 데이터 전처리 수행


# 메인 실행 부분
if __name__ == "__main__":
    run_preprocessing_pipeline()