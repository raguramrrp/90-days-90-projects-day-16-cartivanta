"""
CARTIVANTA - Authentication and Role-Based Access Control Service
Provides secure password hashing (PBKDF2-HMAC-SHA256 with salt),
token/session management, and role permission checks.
"""
import hashlib
import os
import hmac
import time
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from database.models import User

SECRET_KEY = os.getenv("CARTIVANTA_SECRET_KEY", "cartivanta-enterprise-retail-secure-salt-2026")

def hash_password(password: str) -> str:
    """Hash a plaintext password using PBKDF2-HMAC-SHA256 with a unique salt."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ":" + key.hex()

def verify_password(stored_password_hash: str, provided_password: str) -> bool:
    """Verify a plaintext password against the stored salt:hash string."""
    try:
        salt_hex, key_hex = stored_password_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(key, new_key)
    except Exception:
        return False

def generate_session_token(user: User) -> str:
    """Generate a tamper-proof signed session token containing user_id, role, and expiration."""
    expires_at = int(time.time()) + (86400 * 7)  # 7 days validity
    payload = f"{user.id}:{user.username}:{user.role}:{expires_at}"
    signature = hmac.new(SECRET_KEY.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"

def verify_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate token signature and expiration; return user session dict if valid."""
    if not token:
        return None
    try:
        parts = token.split(":")
        if len(parts) != 5:
            return None
        user_id_str, username, role, expires_at_str, signature = parts
        payload = f"{user_id_str}:{username}:{role}:{expires_at_str}"
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        if int(expires_at_str) < time.time():
            return None
        return {
            "user_id": int(user_id_str),
            "username": username,
            "role": role,
            "is_owner": (role == "owner")
        }
    except Exception:
        return None

def authenticate_user(session: Session, username: str, password: str) -> Optional[User]:
    """Look up user and check password."""
    user = session.query(User).filter(User.username == username.strip().lower(), User.is_active == True).first()
    if not user:
        return None
    if verify_password(user.password_hash, password):
        return user
    return None
