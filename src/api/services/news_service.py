import os
import requests
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.database.models.database_model import NewsArticle

# Google Custom Search API를 통한 뉴스 검색
def google_search(query):
    api_key = os.getenv('GOOGLE_API_KEY')
    search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={api_key}&cx={search_engine_id}"

    response = requests.get(url)
    results = response.json().get('items', [])
    return [(item['title'], item['link']) for item in results]

# 뉴스 데이터 조회
def get_news_articles(region_name: str, db: Session):
    # 현재 날짜 기준 1달 내 데이터 조회
    one_month_ago = datetime.now().date() - timedelta(days=120)

    query = (
        select(NewsArticle)
        .where(NewsArticle.content.like(f"%{region_name}%"))
        .where(NewsArticle.published_date > one_month_ago)  # 최근 1달 내 데이터
        .limit(4)  # 최대 4개의 뉴스 기사 조회
    )
    query_result = db.execute(query).fetchall()

    result = []
    for record in query_result:
        # 첫 번째 요소만 가져오기 (예: (<PropertyPriceData 객체>,))
        data = record[0]
        print(f"ID: {data.id}, Title: {data.title}, Content: {data.content}, "
              f"Published Date: {data.published_date}")
        result.append({
            "title": data.title,
            "content": data.content,
            "url": data.url,
            "published_date": data.published_date.strftime('%Y-%m-%d')
        })

    if not result:
        return None
    return result 