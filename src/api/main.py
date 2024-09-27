from fastapi import FastAPI

from src.api.routes import real_estate, healthcheck
from src.config.database import Base, engine
from src.api.models import real_estate_model

app = FastAPI()


@app.on_event("startup")
def on_startup():
    print("========테이블 생성 시작========")
    Base.metadata.create_all(bind=engine)  # 테이블 생성 명령
    print("========테이블 생성 완료========")


@app.get("/")
async def root():
    return {"message": "Hello World"}


app.include_router(real_estate.router, prefix="/real-estate")
app.include_router(healthcheck.router, prefix="/health-check")
