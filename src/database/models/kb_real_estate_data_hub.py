from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from src.database.database import Base


# 지역 테이블
class Region(Base):
    __tablename__ = "kb_region"

    id = Column(Integer, primary_key=True, index=True)
    region_name = Column(String, unique=True, index=True)  # 지역명 (서울, 강남 등)

    # 연관된 부동산 데이터
    property_prices = relationship("PropertyPriceData", back_populates="region")
    predictions = relationship("Prediction", back_populates="region")


# 부동산 가격 데이터 테이블
class PropertyPriceData(Base):
    __tablename__ = "kb_property_price_data"

    id = Column(Integer, primary_key=True, index=True)
    region_id = Column(Integer, ForeignKey('kb_region.id'))
    region = relationship("Region", back_populates="property_prices")

    date = Column(Date, index=True)  # 주간 또는 월간 날짜
    price_type = Column(String, index=True)  # "매매" 또는 "전세"
    index_value = Column(Float, nullable=True)  # 가격 지수
    avg_price = Column(Float, nullable=True)  # 평균 가격
    is_interpolated = Column(Boolean, default=False)  # 보간 여부 (True/False)

    __table_args__ = (
        Index('ix_region_date_type_timespan', 'region_id', 'date', 'price_type'),
    )


# 예측 데이터 테이블
class Prediction(Base):
    __tablename__ = "kb_prediction"

    id = Column(Integer, primary_key=True, index=True)
    region_id = Column(Integer, ForeignKey('kb_region.id'))
    region = relationship("Region", back_populates="predictions")

    date = Column(Date, index=True)
    price_type = Column(String)  # "매매" 또는 "전세"
    predicted_value = Column(Float)  # 예측된 가격 지수 또는 평균 가격
    prediction_accuracy = Column(Float, nullable=True)  # 예측 정확도 (선택 사항)
