# monitoring-core/app/config/secrets.py
import os
from typing import Dict
import secrets
import hashlib


class SecretManager:
    """Centralized secret management"""

    def __init__(self):
        self.service_secrets = self._load_service_secrets()
        self.master_secret = os.getenv("SECRET_KEY", "")

    def _load_service_secrets(self) -> Dict[str, str]:
        """Load service secrets from environment variables"""
        return {
            "note-service": os.getenv("NOTE_SERVICE_SECRET", ""),
            "user-service": os.getenv("USER_SERVICE_SECRET", ""),
            "order-service": os.getenv("ORDER_SERVICE_SECRET", ""),
            "payment-service": os.getenv("PAYMENT_SERVICE_SECRET", ""),
            "inventory-service": os.getenv("INVENTORY_SERVICE_SECRET", "")
        }

    def validate_service_secret(self, service_name: str, provided_secret: str) -> bool:
        """Validate a service secret"""
        expected_secret = self.service_secrets.get(service_name)
        if not expected_secret:
            return False

        return secrets.compare_digest(expected_secret, provided_secret)

    def generate_service_secret(self, service_name: str) -> str:
        """Generate a new secret for a service"""
        new_secret = f"{service_name}_{secrets.token_urlsafe(32)}"
        self.service_secrets[service_name] = new_secret
        return new_secret

    def hash_secret(self, secret: str) -> str:
        """Hash a secret for storage"""
        return hashlib.sha256(secret.encode()).hexdigest()

    def get_service_secrets(self) -> Dict[str, str]:
        """Get all service secrets (for admin use)"""
        return self.service_secrets.copy()

    def rotate_service_secret(self, service_name: str) -> str:
        """Rotate a service secret"""
        if service_name in self.service_secrets:
            return self.generate_service_secret(service_name)
        else:
            raise ValueError(f"Service {service_name} not found")


# Global secret manager instance
secret_manager = SecretManager()

# monitoring-core/app/__init__.py
"""Monitoring core application package"""



