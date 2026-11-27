from datetime import datetime
from pydantic import BaseModel, Field


class ChatMessageCreate(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Isi pesan teks (1 - 2000 karakter)",
    )


class ChatMessageResponse(BaseModel):
    id: int
    order_id: int
    sender_id: int
    message: str
    created_at: datetime

    class Config:
        from_attributes = True