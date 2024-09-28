from sqlalchemy.orm import Session

from src.api.models.kb_real_estate_data_hub import Region


# kb 데이터베이스에서 모든 지역을 가져오는 함수
def get_all_kb_regions(db: Session):
    return db.query(Region).all()
