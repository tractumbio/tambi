from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
    environment: str
    database_mode: str
    ai_provider: str
