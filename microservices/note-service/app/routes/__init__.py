# microservices/note-service/app/routes/__init__.py
"""Routes package for note service"""

from .notes import router as notes_router

__all__ = ["notes_router"]
