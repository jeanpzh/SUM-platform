import hashlib
import hmac
import json
import time

import pytest
from sum_backend.ai_security import verify_admin_assertion
from sum_contracts.models import ServiceError

SECRET = "test-signing-secret-with-adequate-length"


def signed(body: dict) -> str:
    payload = json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
    return payload.hex() + "." + hmac.new(SECRET.encode(), payload, hashlib.sha256).hexdigest()


def test_valid_assertion_binds_method_path_and_body():
    digest = hashlib.sha256(b'{"question":"hola"}').hexdigest()
    token = signed({"sub": "admin-1", "role": "admin", "exp": int(time.time()) + 60,
                    "method": "POST", "path": "/v1/admin/ai/runs", "body_sha256": digest})
    assert verify_admin_assertion(token, "POST", "/v1/admin/ai/runs", digest, SECRET) == "admin-1"
    for method, path, body in [("GET", "/v1/admin/ai/runs", digest),
                               ("POST", "/v1/admin/ai/metrics", digest),
                               ("POST", "/v1/admin/ai/runs", "0" * 64)]:
        with pytest.raises(ServiceError) as error:
            verify_admin_assertion(token, method, path, body, SECRET)
        assert error.value.status == 401


def test_expired_or_changed_signature_is_rejected():
    fields = {"sub": "admin", "role": "admin", "exp": int(time.time()) - 1,
              "method": "GET", "path": "/v1/admin/ai/models", "body_sha256": hashlib.sha256(b"").hexdigest()}
    with pytest.raises(ServiceError):
        verify_admin_assertion(signed(fields), "GET", fields["path"], fields["body_sha256"], SECRET)
    fields["exp"] += 60
    token = signed(fields)
    replacement = "1" if token[-1] == "0" else "0"
    with pytest.raises(ServiceError):
        verify_admin_assertion(token[:-1] + replacement, "GET", fields["path"], fields["body_sha256"], SECRET)
