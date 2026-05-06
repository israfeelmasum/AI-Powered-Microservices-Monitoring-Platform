# microservices/note-service/app/middleware/__init__.py
"""Middleware for note service"""

from .monitoring import NoteServiceMonitoring

__all__ = ["NoteServiceMonitoring"]
