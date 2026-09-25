from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


EventType = Literal[
    "payment_initiated",
    "payment_processed",
    "payment_failed",
    "settled",
]


class EventCreate(BaseModel):
    event_id: str = Field(min_length=1, max_length=100)
    event_type: EventType
    transaction_id: str = Field(min_length=1, max_length=100)
    merchant_id: str = Field(min_length=1, max_length=100)
    merchant_name: str = Field(min_length=1, max_length=255)
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=10)
    timestamp: datetime