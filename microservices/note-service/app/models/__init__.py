# microservices/note-service/app/models/__init__.py
"""Models for note service"""

from .note import Note, NoteCreate, NoteUpdate

__all__ = ["Note", "NoteCreate", "NoteUpdate"]