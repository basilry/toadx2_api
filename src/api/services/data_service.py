from sqlalchemy.orm import Session

from src.api.models.kb_real_estate_data_hub import Region, PropertyPriceData


def insert_property_price_data(data: list, db: Session):
    """
    주간 또는 월간 데이터를 데이터베이스에 삽입합니다.
    """
    db.bulk_insert_mappings(PropertyPriceData, data)
    db.commit()


# kb 데이터베이스에서 모든 지역을 가져오는 함수
def get_all_kb_regions(db: Session):
    return db.query(Region).all()
