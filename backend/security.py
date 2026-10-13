import hashlib
import secrets
from datetime import UTC, datetime, timedelta
import jwt

from backend.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET_KEY

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not configured in the .env file")


# Hash the password with SHA-256 before storing it in the database.
def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# Verify the submitted password against the stored SHA-256 hash.
def _verify_password(password: str, stored_hash: str) -> bool:
    calculated_hash = _hash_password(password)
    return secrets.compare_digest(calculated_hash, stored_hash)


# Create a JWT access token containing the user ID.
def create_access_token(user_id: str) -> str:
    expire_at = datetime.now(UTC) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "exp": expire_at},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> str:
    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise jwt.InvalidTokenError("Missing user ID")
    return user_id