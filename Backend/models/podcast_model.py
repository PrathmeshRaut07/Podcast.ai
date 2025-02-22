from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PodcastCreate(BaseModel):
    title: str
    description: str
    topic: str

class Podcast(BaseModel):
    id: str
    user_email: str
    title: str
    description: str
    topic: str
    audio_base64: str
    created_at: datetime
    duration_seconds: Optional[float]