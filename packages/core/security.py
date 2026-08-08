import hashlib
import hmac


def verify_api_key(provided: str, expected: str) -> bool:
    """Constant-time API-key comparison for an eventual authenticated boundary."""
    if not provided or not expected:
        return False
    return hmac.compare_digest(hashlib.sha256(provided.encode()).digest(), hashlib.sha256(expected.encode()).digest())
