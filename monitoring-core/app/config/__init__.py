# monitoring-core/app/config/__init__.py
"""Configuration package"""

from .settings import settings
from .secrets import secret_manager

__all__ = ["settings", "secret_manager"]