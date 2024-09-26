from sqlalchemy import Column, Integer, Float, String, Date
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import Optional
from datetime import date

# SQLAlchemy Base 선언
Base = declarative_base()


# 1. SQLAlchemy 모델 정의 (데이터베이스 테이블)
class RealEstateData(Base):
    __tablename__ = 'real_estate_data'  # 테이블 이름

    id = Column(Integer, primary_key=True, index=True)  # Primary Key
    region = Column(String, index=True)  # 지역명
    sale_price = Column(Float, nullable=False)  # 매매가
    rent_price = Column(Float, nullable=True)  # 전세가 (nullable)
    date = Column(Date, nullable=False)  # 거래 날짜

    def __repr__(self):
        return f"<RealEstateData(region={self.region}, sale_price={self.sale_price}, date={self.date})>"


# 2. Pydantic 모델 정의 (FastAPI 요청 및 응답 처리)

# 공통 Pydantic 모델
class RealEstateBase(BaseModel):
    region: str  # 지역명
    sale_price: float  # 매매가
    rent_price: Optional[float] = None  # 전세가 (Optional)
    date: date  # 거래 날짜

    class Config:
        orm_mode = True  # ORM 객체를 자동으로 Pydantic 모델로 변환할 수 있도록 설정


# 데이터 생성용 Pydantic 모델 (API 요청 시)
class RealEstateCreate(RealEstateBase):
    pass  # 별도의 추가 필드는 없고, 기본 데이터 구조를 사용


# 데이터 응답용 Pydantic 모델 (API 응답 시)
class RealEstateResponse(RealEstateBase):
    id: int  # 응답 시 ID를 포함
