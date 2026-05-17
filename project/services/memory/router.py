"""Memory API routers — Phase 6: Instructions, Decisions, Memory Search."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory import ledger
from services.memory.cache_service import get_cache_stats
from services.memory.decision_service import decision_to_response, get_decisions
from services.memory.decision_service import store_decision as store_decision_svc
from services.memory.embedding_service import semantic_search
from shared.database import get_db
from shared.schemas.decision import DecisionCreate, DecisionListResponse, DecisionResponse
from shared.schemas.mentor_instruction import (
    InstructionCreate,
    InstructionListResponse,
    InstructionResponse,
    InstructionUpdate,
    MemorySearchRequest,
)

router = APIRouter()


@router.get("/instructions", response_model=InstructionListResponse)
async def list_instructions(
    db: AsyncSession = Depends(get_db),
    task_id: UUID | None = None,
    instruction_type: str | None = None,
    applied: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await ledger.get_instructions(db, task_id, instruction_type, applied, page, page_size)
    return InstructionListResponse(
        items=[ledger.instruction_to_response(i) for i in items],
        total=total, page=page, page_size=page_size,
    )


@router.post("/instructions", response_model=InstructionResponse, status_code=201)
async def create_instruction(data: InstructionCreate, db: AsyncSession = Depends(get_db)):
    inst = await ledger.store_instruction(db, data.task_id, data.instruction_type, data.content, data.context)
    return ledger.instruction_to_response(inst)


@router.patch("/instructions/{instruction_id}", response_model=InstructionResponse)
async def update_instruction(
    instruction_id: UUID, data: InstructionUpdate, db: AsyncSession = Depends(get_db),
):
    inst = await ledger.update_instruction(db, instruction_id, data)
    if not inst:
        raise HTTPException(status_code=404, detail="Instruction not found")
    return ledger.instruction_to_response(inst)


@router.get("/instructions/{task_id}", response_model=InstructionListResponse)
async def get_task_instructions(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await ledger.get_instructions(db, task_id=task_id, page=page, page_size=page_size)
    return InstructionListResponse(
        items=[ledger.instruction_to_response(i) for i in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/decisions", response_model=DecisionListResponse)
async def list_decisions(
    db: AsyncSession = Depends(get_db),
    project_id: UUID | None = None,
    task_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await get_decisions(db, project_id, task_id, page, page_size)
    return DecisionListResponse(
        items=[decision_to_response(i) for i in items],
        total=total, page=page, page_size=page_size,
    )


@router.post("/decisions", response_model=DecisionResponse, status_code=201)
async def create_decision(data: DecisionCreate, db: AsyncSession = Depends(get_db)):
    dec = await store_decision_svc(
        db, data.project_id, data.decision, data.reason,
        task_id=data.task_id, context=data.context,
        alternatives=data.alternatives,
    )
    return decision_to_response(dec)


@router.get("/decisions/{project_id}", response_model=DecisionListResponse)
async def get_project_decisions(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = await get_decisions(db, project_id=project_id, page=page, page_size=page_size)
    return DecisionListResponse(
        items=[decision_to_response(i) for i in items],
        total=total, page=page, page_size=page_size,
    )


@router.post("/memory/search")
async def search_memory(body: MemorySearchRequest, db: AsyncSession = Depends(get_db)):
    results = await semantic_search(db, body.query, top_k=body.top_k, threshold=body.threshold)
    return {"results": results, "total": len(results), "query": body.query}


@router.get("/memory/stats")
async def memory_cache_stats():
    return get_cache_stats()
