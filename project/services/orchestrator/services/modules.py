from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.models.module import Module, ModuleDependency
from shared.schemas.module import ModuleCreate, ModuleUpdate


async def get_modules(
    db: AsyncSession,
    project_id: UUID | None = None,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
) -> tuple[list[Module], int]:
    query = select(Module)
    count_query = select(func.count()).select_from(Module)

    if project_id:
        query = query.where(Module.project_id == project_id)
        count_query = count_query.where(Module.project_id == project_id)
    if status:
        query = query.where(Module.status == status)
        count_query = count_query.where(Module.status == status)

    total = (await db.execute(count_query)).scalar()
    result = await db.execute(
        query.offset((page - 1) * page_size).limit(page_size).order_by(Module.created_at.desc())
    )
    return result.scalars().all(), total


async def get_module(db: AsyncSession, module_id: UUID) -> Module | None:
    result = await db.execute(
        select(Module).where(Module.id == module_id).options(selectinload(Module.dependencies))
    )
    return result.scalar_one_or_none()


async def create_module(db: AsyncSession, data: ModuleCreate) -> Module:
    module = Module(**data.model_dump())
    db.add(module)
    await db.flush()
    await db.refresh(module)
    return module


async def update_module(db: AsyncSession, module_id: UUID, data: ModuleUpdate) -> Module | None:
    module = await get_module(db, module_id)
    if not module:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(module, key, value)

    await db.flush()
    await db.refresh(module)
    return module


async def delete_module(db: AsyncSession, module_id: UUID) -> bool:
    module = await get_module(db, module_id)
    if not module:
        return False
    await db.delete(module)
    await db.flush()
    return True


async def add_module_dependency(
    db: AsyncSession, module_id: UUID, depends_on_module_id: UUID
) -> ModuleDependency | None:
    if module_id == depends_on_module_id:
        return None

    existing = await db.execute(
        select(ModuleDependency).where(
            ModuleDependency.module_id == module_id,
            ModuleDependency.depends_on_module_id == depends_on_module_id,
        )
    )
    if existing.scalar_one_or_none():
        return None

    dep = ModuleDependency(module_id=module_id, depends_on_module_id=depends_on_module_id)
    db.add(dep)
    await db.flush()
    await db.refresh(dep)
    return dep


async def remove_module_dependency(db: AsyncSession, dep_id: UUID) -> bool:
    result = await db.execute(select(ModuleDependency).where(ModuleDependency.id == dep_id))
    dep = result.scalar_one_or_none()
    if not dep:
        return False
    await db.delete(dep)
    await db.flush()
    return True
