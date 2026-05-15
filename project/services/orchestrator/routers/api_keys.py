from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db
from services.orchestrator.services import api_keys as api_key_service

router = APIRouter()


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    permissions: list[str] = Field(default_factory=lambda: ["read"])
    expires_in_days: int | None = Field(None, ge=1, le=365)


class ApiKeyResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    permissions: list
    is_active: bool
    expires_at: str | None = None
    last_used_at: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(BaseModel):
    id: UUID
    api_key: str
    name: str
    key_prefix: str
    message: str = "Store this key securely. It will not be shown again."


@router.post("/", response_model=ApiKeyCreatedResponse, status_code=201)
async def create_api_key(data: ApiKeyCreateRequest, db: AsyncSession = Depends(get_db)):
    from fastapi import Request
    try:
        key, raw_key = await api_key_service.create_api_key(
            db,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            name=data.name,
            permissions=data.permissions,
            expires_in_days=data.expires_in_days,
        )
        return ApiKeyCreatedResponse(
            id=key.id,
            api_key=raw_key,
            name=key.name,
            key_prefix=key.key_prefix,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=list[ApiKeyResponse])
async def list_api_keys(db: AsyncSession = Depends(get_db)):
    keys = await api_key_service.get_api_keys(
        db, UUID("00000000-0000-0000-0000-000000000000")
    )
    return [ApiKeyResponse(
        id=k.id,
        name=k.name,
        key_prefix=k.key_prefix,
        permissions=k.permissions,
        is_active=k.is_active,
        expires_at=k.expires_at.isoformat() if k.expires_at else None,
        last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
        created_at=k.created_at.isoformat() if k.created_at else "",
    ) for k in keys]


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(key_id: UUID, db: AsyncSession = Depends(get_db)):
    ok = await api_key_service.revoke_api_key(db, key_id)
    if not ok:
        raise HTTPException(status_code=404, detail="API key not found")
