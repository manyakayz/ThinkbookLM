from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UserSession(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: int
    csrf_token: str
    created_at: datetime
    expires_at: datetime
