from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from src.config.database import Base


# 지역 테이블 (지역 정보만 저장)
class Region(Base):
    __tablename__ = "kb_region"

    id = Column(Integer, primary_key=True, index=True)
    region_name = Column(String, unique=True, index=True)  # 지역명 (서울, 강남 등)

    # 연관된 부동산 데이터 (1:N 관계)
    property_prices = relationship("PropertyPriceData", back_populates="region")
    predictions = relationship("Prediction", back_populates="region")


# 부동산 가격 데이터 테이블 (매매/전세 지수와 평균 가격)
class PropertyPriceData(Base):
    __tablename__ = "kb_property_price_data"

    id = Column(Integer, primary_key=True, index=True)
    region_id = Column(Integer, ForeignKey('kb_region.id'))  # 지역 ID (FK)
    region = relationship("Region", back_populates="property_prices")  # 관계 설정 (지역과 연관)

    date = Column(Date, index=True)  # 주간 또는 월간 날짜
    price_type = Column(String, index=True)  # "매매" 또는 "전세"
    time_span = Column(String, index=True)  # "주간" 또는 "월간"
    index_value = Column(Float, nullable=True)  # 가격 지수
    avg_price = Column(Float, nullable=True)  # 평균 가격

    # 새로운 필드: 보간 여부
    is_interpolated = Column(String, default="N")  # 보간 여부 ("Y" 또는 "N")


# 예측 데이터 테이블 (예측 결과 저장)
class Prediction(Base):
    __tablename__ = "kb_prediction"

    id = Column(Integer, primary_key=True, index=True)
    region_id = Column(Integer, ForeignKey('kb_region.id'))  # 지역 ID (FK)
    region = relationship("Region", back_populates="predictions")  # 관계 설정 (지역과 연관)

    date = Column(Date, index=True)
    price_type = Column(String)  # "매매" 또는 "전세"
    time_span = Column(String)  # "주간" 또는 "월간"
    predicted_value = Column(Float)  # 예측된 가격 지수 또는 평균 가격
