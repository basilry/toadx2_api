from fastapi import FastAPI
from src.api.routes import real_estate, healthcheck

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


app.include_router(real_estate.router, prefix="/real-estate")
# app.include_router(healthcheck.router, prefix="/healthcheck")