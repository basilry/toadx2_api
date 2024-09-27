from sqlalchemy import Column, Integer, String, Float, Date

from src.config.database import Base


class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True, index=True)
    region_name = Column(String, unique=True, index=True)  # 지역명 (서울, 강남 등)


class PropertyPriceData(Base):
    __tablename__ = "property_price_data"

    id = Column(Integer, primary_key=True, index=True)
    region_id = Column(Integer)  # 지역 ID, FK로 설정 가능 (여기선 간단하게 설정)
    date = Column(Date, index=True)  # 주간 또는 월간 날짜
    price_type = Column(String, index=True)  # "매매" 또는 "전세"
    time_span = Column(String, index=True)  # "주간" 또는 "월간"
    index_value = Column(Float, nullable=True)  # 가격 지수
    avg_price = Column(Float, nullable=True)  # 평균 가격


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    region_id = Column(Integer)
    date = Column(Date, index=True)
    price_type = Column(String)  # "매매" 또는 "전세"
    time_span = Column(String)  # "주간" 또는 "월간"
    predicted_value = Column(Float)  # 예측된 가격 지수 또는 평균 가격
