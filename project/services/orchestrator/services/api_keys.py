from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.user import ApiKey
from shared.security import generate_api_key


async def create_api_key(
    db: AsyncSession,
    user_id: UUID,
    name: str,
    permissions: list[str] | None = None,
    expires_in_days: int | None = None,
) -> tuple[ApiKey, str]:
    """Create a new API key and return the raw key (shown only once)."""
    raw_key, hashed_key = generate_api_key()

    expires_at = None
    if expires_in_days:
        expires_at = datetime.now(timezone.utc).replace(
            hour=23, minute=59, second=59, microsecond=0
        )
        from datetime import timedelta
        expires_at = expires_at + timedelta(days=expires_in_days)

    key = ApiKey(
        user_id=user_id,
        name=name,
        key_hash=hashed_key,
        key_prefix=raw_key[:12],
        permissions=permissions or ["read"],
        expires_at=expires_at,
    )
    db.add(key)
    await db.flush()
    await db.refresh(key)

    return key, raw_key


async def get_api_keys(db: AsyncSession, user_id: UUID) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user_id)
    )
    return list(result.scalars().all())


async def revoke_api_key(db: AsyncSession, key_id: UUID) -> bool:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        return False
    key.is_active = False
    await db.flush()
    return True


async def delete_api_key(db: AsyncSession, key_id: UUID) -> bool:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        return False
    await db.delete(key)
    await db.flush()
    return True
