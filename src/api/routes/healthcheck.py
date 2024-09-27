from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.config.database import SessionLocal

router = APIRouter()


@router.get("/", status_code=200)
def health_check():
    return {"status": "toadx2 api server ok"}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection(db: Session):
    try:
        db.execute(text('SELECT 1'))
        return True
    except Exception as e:
        print(f"Database connection error: {e}")
        return False


@router.get("/database")
def db_health_check(db: Session = Depends(get_db)):
    if check_db_connection(db):
        return {"status": "Database is connected"}
    else:
        return {"status": "Database connection failed"}, 500
