from pydantic import BaseModel

class Deal(BaseModel):
    id: int
    title: str
    address: str | None = None
    contact: str | None = None
    type: str | None = None
    model: str | None = None
    delivery_date: str | None = None