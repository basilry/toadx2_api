import requests
import re

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from src.database.models.database_model import NewsCategory, NewsArticle  # 테이블 임포트
from src.database.database import get_db


# 뉴스 데이터를 크롤링하여 DB에 저장하는 함수
def crawl_and_store_news(db: Session, base_date: str, page: int, size: int):
    try:
        url = f"https://land.naver.com/news/airsList.naver?baseDate={base_date}&page={page}&size={size}"
        response = requests.get(url, timeout=10)
        response_data = response.json()

        # 뉴스 목록을 파싱
        for item in response_data['list']:
            title = item['title']
            link = item['linkUrl']
            summary = item['summaryContent']  # 요약 정보
            thumbnail = item['thumbnail']  # 썸네일 URL
            publish_date_str = item['publishDateTime']
            publish_date = datetime.strptime(publish_date_str, "%Y-%m-%dT%H:%M:%S")

            # 뉴스 세부 내용 페이지로 이동하여 컨텐츠 크롤링
            news_response = requests.get(link)
            news_soup = BeautifulSoup(news_response.text, 'html.parser')
            content = news_soup.find('div', id='contents').get_text().strip()

            # 데이터 전처리: 개행 문자, 특수 문자 제거
            content_clean = re.sub(r'\s+', ' ', content).replace('\n', ' ')
            summary_clean = re.sub(r'\s+', ' ', summary).replace('\n', ' ')

            # 카테고리 찾기 또는 생성
            category_name = item.get('pressCorporationName', 'Unknown')
            category = db.query(NewsCategory).filter_by(name=category_name).first()
            if not category:
                category = NewsCategory(name=category_name)
                db.add(category)
                db.commit()

            # 뉴스가 이미 저장된 경우 스킵
            existing_article = db.query(NewsArticle).filter_by(url=link).first()
            if existing_article:
                continue

            # DB에 뉴스 저장
            news_article = NewsArticle(
                title=title,
                url=link,
                content=content,
                summary=summary,  # 요약 정보 저장
                thumbnail=thumbnail,  # 썸네일 저장
                reg_date=datetime.now(),
                published_date=publish_date,
                category_id=category.id
            )
            db.add(news_article)
            db.commit()

        print(f"Page {page} processed and stored in DB.")

    except Exception as e:
        print(f"An error occurred while processing page {page}: {e}")

# 첫 번째 요청을 통해 total_pages 값을 가져오는 함수
def get_total_pages(base_date: str, size: int):
    url = f"https://land.naver.com/news/airsList.naver?baseDate={base_date}&page=1&size={size}"
    response = requests.get(url)
    response_data = response.json()
    return response_data.get('totalPages', 1)


# 크롤링 작업을 시작하는 함수
def start_crawling(db: Session, start_date: str, total_days: int = 90, size: int = 100):
    base_date = datetime.strptime(start_date, '%Y-%m-%d')

    # 하루씩 감소하면서 3개월 간 데이터 수집
    for day in range(total_days):
        target_date = base_date - timedelta(days=day)  # 하루씩 감소
        formatted_date = target_date.strftime('%Y-%m-%d')

        # 해당 날짜의 totalPages 값을 얻음
        total_pages = get_total_pages(formatted_date, size)

        # 각 날짜마다 totalPages 만큼 페이지별 크롤링
        for page in range(1, total_pages + 1):
            print("=======================================")
            print("Crawling news for", formatted_date, "Page", page)
            crawl_and_store_news(db, formatted_date, page, size)


# 메인 함수로 실행될 때 호출되는 부분
if __name__ == "__main__":
    db = next(get_db())  # DB 세션 가져오기
    # base_date = datetime.today().strftime('%Y-%m-%d')  # 크롤링 시작할 기준 날짜
    base_date = '2024-05-09'
    total_days = 60  # 3개월 간의 데이터를 수집
    start_crawling(db, base_date, total_days)