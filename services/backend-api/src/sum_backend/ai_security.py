"""Verify the short-lived UI assertion instead of trusting a browser identity header."""

import hashlib
import hmac
import json
import time

from sum_contracts.models import ServiceError


def verify_admin_assertion(value: str, method: str, path: str, body_digest: str, secret: str) -> str:
    return verify_identity_assertion(value, method, path, body_digest, secret, "admin")


def verify_identity_assertion(value: str, method: str, path: str, body_digest: str,
                              secret: str, role: str) -> str:
    invalid = ServiceError("AI_IDENTITY_INVALID", "La identidad no es válida.", 401)
    if not secret or len(secret) < 24 or len(value) > 4096:
        raise invalid
    try:
        payload_hex, signature = value.split(".", 1)
        payload = bytes.fromhex(payload_hex)
        if len(payload) > 2048 or len(signature) != 64:
            raise ValueError("Invalid assertion length")
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid assertion signature")
        claims = json.loads(payload)
        if set(claims) != {"sub", "role", "exp", "method", "path", "body_sha256"}:
            raise ValueError("Invalid assertion fields")
        if claims["role"] != role or not isinstance(claims["sub"], str) or not 1 <= len(claims["sub"]) <= 200:
            raise ValueError("Invalid admin identity")
        if type(claims["exp"]) is not int or not time.time() < claims["exp"] <= time.time() + 120:
            raise ValueError("Expired assertion")
        if (claims["method"], claims["path"], claims["body_sha256"]) != (method, path, body_digest):
            raise ValueError("Assertion scope mismatch")
        if role == "student":
            return "student:" + hashlib.sha256(claims["sub"].encode()).hexdigest()
        return claims["sub"]
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise invalid from exc
