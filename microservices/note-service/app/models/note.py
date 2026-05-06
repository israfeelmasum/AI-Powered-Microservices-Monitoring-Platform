# microservices/note-service/app/models/note.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class NoteBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Note title")
    content: str = Field(..., min_length=1, description="Note content")
    tags: Optional[List[str]] = Field(default=[], description="Note tags")


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    tags: Optional[List[str]] = None


class Note(NoteBase):
    id: int = Field(..., description="Unique note identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "Sample Note",
                "content": "This is a sample note content",
                "tags": ["sample", "demo"],
                "created_at": "2024-01-01T12:00:00",
                "updated_at": "2024-01-01T12:00:00"
            }
        }
