from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from src.api.routes import real_estate, healthcheck, assistant_api, openai_api
from src.database.database import Base, engine

# 로깅 레벨 설정
logging.basicConfig(level=logging.INFO)
# 외부 라이브러리 로깅 레벨 조정
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.DEBUG)
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:3000",
    "https://toadx2.com",  # 클라이언트 도메인 추가
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 허용할 출처
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메소드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)


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
app.include_router(openai_api.router, prefix="/model")
app.include_router(assistant_api.router, prefix="/assistant")
