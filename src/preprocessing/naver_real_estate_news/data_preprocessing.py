import csv
import os
import re

from sqlalchemy.orm import Session
from src.database.models.database_model import NewsArticle  # 뉴스 기사 테이블
from src.database.database import get_db
from transformers import BartForConditionalGeneration, PreTrainedTokenizerFast
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()
huggingfaceToken = os.getenv('HUGGINGFACE_TOKEN')

# KoBART 요약 모델 및 토크나이저 불러오기
model = BartForConditionalGeneration.from_pretrained('gogamza/kobart-summarization', use_auth_token=huggingfaceToken)
tokenizer = PreTrainedTokenizerFast.from_pretrained('gogamza/kobart-summarization', use_auth_token=huggingfaceToken)


def generate_summary_kobart(text):
    # 텍스트를 토크나이즈
    inputs = tokenizer([text], max_length=1024, return_tensors='pt', truncation=True)
    # 모델을 통해 요약 생성
    summary_ids = model.generate(inputs['input_ids'], max_length=150, min_length=40, num_beams=4, length_penalty=2.0, early_stopping=True)
    # 토크나이즈된 요약을 텍스트로 변환
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return summary


# 데이터 전처리 함수
def clean_text(text: str) -> str:
    soup = BeautifulSoup(text, 'html.parser')
    text = soup.get_text(separator=" ")  # HTML 태그 제거

    text = re.sub(r'&nbsp;', ' ', text)  # &nbsp; 제거
    text = re.sub(r'\s+', ' ', text)     # 여러 공백을 하나로
    text = re.sub(r'[\r\n\t]', ' ', text) # \r, \n, \t 제거

    return text.strip()


# DB에서 뉴스 데이터를 조회하고 전처리하는 함수
def process_news_articles(db: Session):
    # 모든 뉴스 기사를 가져옴
    news_articles = db.query(NewsArticle).all()

    # 각 뉴스 기사에 대해 전처리 수행
    for article in news_articles:
        # 전처리
        article.title = clean_text(article.title)
        article.content = clean_text(article.content)

        # 요약 재 생성
        article.summary = generate_summary_kobart(article.content)
        print(article.summary)

        # 변경 사항을 DB에 저장
        db.commit()

    print(f"총 {len(news_articles)}개의 뉴스 기사가 전처리되었습니다.")


# 데이터셋을 train, validation, test로 나누는 함수
def split_dataset(db: Session, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15):
    # 모든 뉴스 기사를 발행일 기준으로 정렬하여 가져옴
    news_articles = db.query(NewsArticle).order_by(NewsArticle.published_date).all()

    total_count = len(news_articles)

    # 데이터셋의 각 비율 계산
    train_count = int(total_count * train_ratio)
    val_count = int(total_count * val_ratio)
    test_count = total_count - train_count - val_count

    # 데이터셋을 분할
    train_set = news_articles[:train_count]
    val_set = news_articles[train_count:train_count + val_count]
    test_set = news_articles[train_count + val_count:]

    print(f"Train set: {len(train_set)} items")
    print(f"Validation set: {len(val_set)} items")
    print(f"Test set: {len(test_set)} items")

    return train_set, val_set, test_set


# CSV 파일로 저장하는 함수
def save_to_csv(data, filename):
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Title', 'URL', 'Summary', 'Content', 'Published Date'])  # 헤더 작성
        for article in data:
            writer.writerow([article.title, article.url, article.summary, article.content, article.published_date])


# 전처리 파이프라인 실행 함수
def run_preprocessing_pipeline():
    db = next(get_db())  # DB 세션 가져오기
    process_news_articles(db)  # 데이터 전처리 수행

    # 데이터셋을 나누는 작업 진행
    train_set, val_set, test_set = split_dataset(db)

    # CSV로 저장
    save_to_csv(train_set, 'train_data.csv')
    save_to_csv(val_set, 'val_data.csv')
    save_to_csv(test_set, 'test_data.csv')


# 메인 실행 부분
if __name__ == "__main__":
    run_preprocessing_pipeline()