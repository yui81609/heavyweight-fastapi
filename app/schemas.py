# app/schemas.py
from pydantic import BaseModel
from typing import List, Optional


class AutoReplyRequest(BaseModel):
    user_message: str


class AutoReplyResponse(BaseModel):
    reply: str


class SaveIdentityRequest(BaseModel):
    key_terms: List[str]
    snippet: str
    note: Optional[str] = None

