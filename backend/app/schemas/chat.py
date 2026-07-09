from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    created_at: datetime


class ChatMessageCreate(BaseModel):
    content: str
