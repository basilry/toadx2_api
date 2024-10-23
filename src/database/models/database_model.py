from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Boolean, Index, Text
from sqlalchemy.orm import relationship
from src.database.database import Base


# 지역 테이블
class Region(Base):
    __tablename__ = "kb_region"

    region_code = Column(String, primary_key=True, index=True)  # 지역 코드 (전국: 0000000000 등)
    region_name_kor = Column(String, unique=True, index=True)  # 지역명 (서울, 강남 등)
    region_name_eng = Column(String, unique=True, index=True)  # 지역명 (Seoul, Gangnam etc.)

    # 연관된 부동산 데이터
    property_prices = relationship("PropertyPriceData", back_populates="region")
    predictions = relationship("Prediction", back_populates="region")


# 부동산 가격 데이터 테이블
class PropertyPriceData(Base):
    __tablename__ = "kb_property_price_data"

    id = Column(Integer, primary_key=True, index=True)
    region_code = Column(String, ForeignKey('kb_region.region_code'))
    region = relationship("Region", back_populates="property_prices")

    date = Column(Date, index=True)  # 주간 또는 월간 날짜
    price_type = Column(String, index=True)  # "매매" 또는 "전세"
    index_value = Column(Float, nullable=True)  # 가격 지수
    avg_price = Column(Float, nullable=True)  # 평균 가격
    is_interpolated = Column(Boolean, default=False)  # 보간 여부 (True/False)

    __table_args__ = (
        Index('ix_region_date_type_timespan', 'region_code', 'date', 'price_type'),
    )


# 예측 데이터 테이블
class Prediction(Base):
    __tablename__ = "kb_prediction"

    id = Column(Integer, primary_key=True, index=True)
    region_code = Column(String, ForeignKey('kb_region.region_code'))
    region = relationship("Region", back_populates="predictions")

    date = Column(Date, index=True)  # 예측 날짜
    price_type = Column(String)  # "매매" 또는 "전세"

    # 예측된 값
    predicted_index = Column(Float, nullable=True)  # 예측된 가격 지수 (optional)
    predicted_price = Column(Float, nullable=True)  # 예측된 평균 가격 (optional)

    # 예측 정확도
    prediction_accuracies = Column(Float, nullable=True)  # 예측 정확도 (선택 사항)


# 법정동 코드 테이블
class LegalDongCode(Base):
    __tablename__ = "legal_dong_code"

    code = Column(String, primary_key=True, index=True)  # 법정동 코드
    name = Column(String, index=True)  # 법정동 이름
    is_active = Column(Boolean, default=True)  # 법정동 폐지 여부 (존재: True, 폐지: False)


# 카테고리 테이블
class NewsCategory(Base):
    __tablename__ = "news_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)

    # 관계 설정: 카테고리 하나가 여러 기사를 가질 수 있음
    articles = relationship("NewsArticle", back_populates="category")


# 뉴스 기사 테이블
class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    url = Column(String, unique=True, nullable=False)  # 뉴스 기사 URL
    content = Column(Text, nullable=False)  # 뉴스 본문
    summary = Column(Text, nullable=True)  # 기사 요약 정보 (summaryContent)
    thumbnail = Column(String, nullable=True)  # 썸네일 URL
    reg_date = Column(Date, nullable=True)  # 발행일 정보 (publishDateTime)
    published_date = Column(Date, nullable=True)
    category_id = Column(Integer, ForeignKey("news_categories.id"))  # 카테고리 외래키

    # 카테고리와의 관계 설정
    category = relationship("NewsCategory", back_populates="articles")