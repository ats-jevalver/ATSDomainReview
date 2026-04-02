"""Authentication API routes for Microsoft 365 SSO."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import UserProfile, get_current_user, get_user_profile, validate_token
from config import azure_ad

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    access_token: str


class AuthConfigResponse(BaseModel):
    client_id: str
    tenant_id: str
    enabled: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/login", response_model=UserProfile)
async def login(body: LoginRequest):
    """Validate a frontend MSAL access token and return the user profile."""
    await validate_token(body.access_token)
    profile = await get_user_profile(body.access_token)
    return profile


@router.get("/me", response_model=UserProfile)
async def me(user: UserProfile = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    return user


@router.get("/config", response_model=AuthConfigResponse)
async def auth_config():
    """Return the Azure AD / MSAL configuration for the frontend (public)."""
    return AuthConfigResponse(
        client_id=azure_ad.client_id,
        tenant_id=azure_ad.tenant_id,
        enabled=bool(azure_ad.client_id),
    )
