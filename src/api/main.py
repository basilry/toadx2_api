from fastapi import FastAPI

from src.api.routes import real_estate, healthcheck
from src.config.database import Base, engine
from src.api.models import kb_real_estate_data_hub

app = FastAPI()


@app.on_event("startup")
def on_startup():
    print("========Table Creating Start========")
    Base.metadata.create_all(bind=engine)  # 테이블 생성 명령
    print("========Table Creating Donee========")


@app.get("/")
async def root():
    return {"message": "Hello World"}


app.include_router(real_estate.router, prefix="/real-estate")
app.include_router(healthcheck.router, prefix="/health-check")
