"""Microsoft 365 SSO authentication helpers."""

from __future__ import annotations

import time
from typing import Optional

import httpx
import jwt
from fastapi import HTTPException, Request
from pydantic import BaseModel

from config import azure_ad

# ---------------------------------------------------------------------------
# User profile model
# ---------------------------------------------------------------------------


class UserProfile(BaseModel):
    oid: str  # Azure AD object ID
    name: str
    email: str
    title: Optional[str] = None
    phone: Optional[str] = None


# ---------------------------------------------------------------------------
# OIDC signing-key cache
# ---------------------------------------------------------------------------

_jwks_cache: dict | None = None
_jwks_cache_time: float = 0
_JWKS_CACHE_TTL = 3600  # 1 hour


async def _get_signing_keys() -> dict:
    """Fetch and cache Microsoft OIDC signing keys."""
    global _jwks_cache, _jwks_cache_time

    now = time.time()
    if _jwks_cache is not None and (now - _jwks_cache_time) < _JWKS_CACHE_TTL:
        return _jwks_cache

    url = f"https://login.microsoftonline.com/{azure_ad.tenant_id}/discovery/v2.0/keys"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_cache_time = now
        return _jwks_cache


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------


async def validate_token(token: str) -> dict:
    """Decode and validate a Microsoft identity-platform access token.

    If ``AZURE_CLIENT_ID`` is empty (dev mode), returns a mock claims dict.
    """
    if not azure_ad.client_id:
        return {
            "oid": "00000000-0000-0000-0000-000000000000",
            "name": "Dev User",
            "preferred_username": "dev@localhost",
        }

    jwks = await _get_signing_keys()

    # Decode the token header to find the correct signing key
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Token missing kid header")

    rsa_key: dict | None = None
    for key in jwks.get("keys", []):
        if key["kid"] == kid:
            rsa_key = key
            break

    if rsa_key is None:
        # Keys may have rotated -- bust cache and retry once
        global _jwks_cache_time
        _jwks_cache_time = 0
        jwks = await _get_signing_keys()
        for key in jwks.get("keys", []):
            if key["kid"] == kid:
                rsa_key = key
                break

    if rsa_key is None:
        raise HTTPException(status_code=401, detail="Unable to find matching signing key")

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key)

    issuer = f"https://login.microsoftonline.com/{azure_ad.tenant_id}/v2.0"

    try:
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=azure_ad.client_id,
            issuer=issuer,
            options={"require": ["exp", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

    return claims


# ---------------------------------------------------------------------------
# Microsoft Graph - user profile
# ---------------------------------------------------------------------------


async def get_user_profile(access_token: str) -> UserProfile:
    """Fetch the current user's profile from Microsoft Graph."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Graph API error: {exc.response.text}",
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Graph API request failed: {exc}")

    phone = data.get("mobilePhone") or ""
    if not phone:
        phones = data.get("businessPhones") or []
        phone = phones[0] if phones else ""

    return UserProfile(
        oid=data.get("id", ""),
        name=data.get("displayName", ""),
        email=data.get("mail") or data.get("userPrincipalName", ""),
        title=data.get("jobTitle"),
        phone=phone or None,
    )


# ---------------------------------------------------------------------------
# Profile cache (in-memory, keyed by oid)
# ---------------------------------------------------------------------------

_profile_cache: dict[str, tuple[float, UserProfile]] = {}
_PROFILE_CACHE_TTL = 1800  # 30 minutes


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_current_user(request: Request) -> UserProfile:
    """FastAPI dependency that extracts and validates the current user.

    In dev mode (``AZURE_CLIENT_ID`` is empty) returns a mock profile.
    """
    if not azure_ad.client_id:
        return UserProfile(
            oid="00000000-0000-0000-0000-000000000000",
            name="Dev User",
            email="dev@localhost",
            title="Developer",
            phone="",
        )

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[len("Bearer "):]

    claims = await validate_token(token)
    oid = claims.get("oid", "")

    # Check cache
    now = time.time()
    if oid in _profile_cache:
        cached_time, cached_profile = _profile_cache[oid]
        if (now - cached_time) < _PROFILE_CACHE_TTL:
            return cached_profile

    profile = await get_user_profile(token)
    if profile.oid:
        _profile_cache[profile.oid] = (now, profile)

    return profile
