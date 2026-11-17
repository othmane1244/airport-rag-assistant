"""Unit tests for document-admin authorisation (app/auth.py). No network:
Keycloak signature checks are mocked.

Usage: python tests/test_auth_roles.py
"""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import HTTPException  # noqa: E402
from fastapi.security import HTTPAuthorizationCredentials  # noqa: E402

from app import auth  # noqa: E402
from app.config import settings  # noqa: E402

ADMIN_CLAIMS = {"sub": "a", "realm_access": {"roles": ["document-admin", "offline_access"]}}
TRAVELLER_CLAIMS = {"sub": "v", "realm_access": {"roles": ["offline_access"]}}


def check(label, condition):
    print(("OK   " if condition else "FAIL ") + label)
    if not condition:
        raise SystemExit(1)


def status_of(fn, *args):
    try:
        fn(*args)
        return 200
    except HTTPException as exc:
        return exc.status_code


def current_user(token_claims, bypass):
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="x.y.z") if token_claims else None
    fake_client = SimpleNamespace(get_signing_key_from_jwt=lambda _t: SimpleNamespace(key="k"))
    with patch.object(settings, "environment", "development"), \
         patch.object(settings, "auth_disabled", bypass), \
         patch.object(auth, "_jwks_client", lambda: fake_client), \
         patch.object(auth.jwt, "decode", lambda *a, **k: token_claims):
        return auth.require_current_user(creds)


for bypass in (False, True):
    mode = "AUTH_DISABLED=true" if bypass else "normal auth"
    admin = current_user(ADMIN_CLAIMS, bypass)
    traveller = current_user(TRAVELLER_CLAIMS, bypass)
    check(f"{mode}: admin token keeps its roles", "document-admin" in admin["realm_access"]["roles"])
    check(f"{mode}: admin -> 200", status_of(auth.require_document_admin, admin) == 200)
    check(f"{mode}: traveller -> 403", status_of(auth.require_document_admin, traveller) == 403)

with patch.object(settings, "environment", "development"), patch.object(settings, "auth_disabled", True):
    anonymous = auth.require_current_user(None)
check("AUTH_DISABLED=true, no token: bypass identity", anonymous.get("auth_bypass") is True)
try:
    auth.require_document_admin(anonymous)
    check("bypass identity is refused admin access", False)
except HTTPException as exc:
    check("bypass identity -> 403 with an explicit message", exc.status_code == 403 and "AUTH_DISABLED" in exc.detail)

with patch.object(settings, "environment", "development"), patch.object(settings, "auth_disabled", False):
    check("normal auth, no token -> 401", status_of(auth.require_current_user, None) == 401)

print("\nTOUS LES TESTS PASSENT.")
