import hashlib
import secrets


def hash_api_key(key: str) -> str:
    """Hash an API key using SHA-256 for storage and lookup."""
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key.

    Returns:
        tuple of (raw_key, hashed_key).
        The raw key must be shown to the user only once.
        The hashed key is stored in the database.
    """
    raw_key = f"sdlc_{secrets.token_urlsafe(32)}"
    hashed = hash_api_key(raw_key)
    return raw_key, hashed


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    """Verify a raw API key against a stored hash."""
    return hash_api_key(raw_key) == stored_hash
