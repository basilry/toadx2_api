from pydantic import BaseModel


class RealEstateData(BaseModel):
    id: int
    region: str
    price: float
    date: str
