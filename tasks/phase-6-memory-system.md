# PHASE 6 — MEMORY SYSTEM (2–3 tuần)

## Mục tiêu
"Organizational learning" — AI nhớ workflow cũ, giảm mentor cost, reuse solutions.

## Tech Stack
| Thành phần | Tech |
|---|---|
| Vector Search | pgvector (PostgreSQL extension) |
| DB | PostgreSQL |
| Embeddings | OpenAI text-embedding-3-small / BGE |
| Cache | Redis |

---

## 6.1. Instruction Ledger

### Mô tả
Lưu trữ mentor advice, failed patterns, architecture decisions, lesson learned.

### Tasks
- [x] **6.1.1** — Tạo SQLAlchemy model MentorInstruction
  - File: `shared/models/mentor_instruction.py` (đã có trong registry.py)
  - Table: `mentor_instructions` (đã có trong schema Phase 0)
  - Columns: id, task_id, instruction_type, content, context, applied, embedding, created_at, updated_at
- [x] **6.1.2** — Tạo Pydantic schemas cho MentorInstruction
  - File: `shared/schemas/mentor_instruction.py`
  - `InstructionCreate`: task_id, instruction_type, content, context
  - `InstructionUpdate`: applied
  - `InstructionResponse`: tất cả fields + id + task_title
- [x] **6.1.3** — Implement instruction service
  - File: `services/memory/ledger.py`
  - Function: `store_instruction(task_id, type, content, context) -> instruction`
- [x] **6.1.4** — Implement mentor advice storage
  - Type: advice
  - Function: `store_mentor_advice(task_id, advice, context) -> instruction`
- [x] **6.1.5** — Implement failed patterns storage
  - Type: warning
  - Function: `store_failed_pattern(task_id, pattern, reason, context) -> instruction`
- [x] **6.1.6** — Implement architecture decisions storage
  - Type: decision
  - Function: `store_architecture_decision(task_id, decision, reason, alternatives) -> instruction`
- [x] **6.1.7** — Implement lesson learned storage
  - Type: pattern
  - Function: `store_lesson_learned(task_id, lesson, context) -> instruction`
- [x] **6.1.8** — Build API: GET /api/v1/instructions
  - Query params: task_id, instruction_type, applied, page, limit
  - Output: List[InstructionResponse] + pagination
- [x] **6.1.9** — Build API: POST /api/v1/instructions
  - Input: InstructionCreate
  - Output: InstructionResponse
- [x] **6.1.10** — Build API: GET /api/v1/instructions/{task_id}
  - Output: List[InstructionResponse] cho task đó
- [x] **6.1.11** — Unit test cho instruction ledger
  - Test store mentor advice
  - Test store failed pattern
  - Test store architecture decision
  - Test store lesson learned
  - Test get instructions

### Output
- Instruction ledger hoạt động
- CRUD API
- Tests pass

---

## 6.2. Semantic Retrieval

### Mô tả
Tìm kiếm memory theo ngữ nghĩa — new task → search memory → reuse solution.

### Tasks
- [x] **6.2.1** — Setup pgvector trong PostgreSQL
  - Enable pgvector extension: `CREATE EXTENSION vector`
  - Verify vector column trong mentor_instructions table
  - Create IVFFlat index: `CREATE INDEX ... USING ivfflat (embedding vector_cosine_ops)`
- [x] **6.2.2** — Implement embedding service
  - File: `services/memory/embedding_service.py`
  - Model: OpenAI text-embedding-3-small hoặc BGE
  - Function: `generate_embedding(text) -> vector (1536 dims)`
  - Batch embedding cho hiệu quả
- [x] **6.2.3** — Implement vector storage
  - Store embeddings cùng với instruction content
  - Function: `store_embedding(instruction_id, embedding) -> status`
- [x] **6.2.4** — Implement semantic search
  - Input: query text
  - Action: generate embedding, search pgvector (cosine similarity)
  - Output: top K similar instructions
  - Function: `semantic_search(query, top_k=5) -> results`
- [x] **6.2.5** — Implement similarity threshold
  - Threshold: 0.7 (configurable)
  - Filter results dưới threshold
  - Function: `filter_by_similarity(results, threshold) -> filtered`
- [x] **6.2.6** — Implement memory retrieval workflow
  - Workflow: new task → generate query → search → filter → return
  - Function: `retrieve_memory(task_spec) -> relevant_instructions`
- [x] **6.2.7** — Build API: POST /api/v1/memory/search
  - Input: { "query": "...", "top_k": 5, "threshold": 0.7 }
  - Output: List[InstructionResponse] + similarity_scores
- [x] **6.2.8** — Implement embedding cache
  - Cache embeddings trong Redis
  - Function: `cache_embedding(text, embedding) -> status`
- [x] **6.2.9** — Unit test cho semantic retrieval
  - Test embedding generation
  - Test vector storage
  - Test semantic search
  - Test similarity threshold
  - Test memory retrieval workflow

### Output
- Semantic retrieval hoạt động
- pgvector integration
- Tests pass

---

## 6.3. Decision History

### Mô tả
Lưu trữ quyết định kiến trúc, lý do, context — để reuse và audit.

### Tasks
- [x] **6.3.1** — Tạo SQLAlchemy model Decision
  - File: `shared/models/decision.py` (đã có trong registry.py)
  - Table: `decisions` (đã có trong schema Phase 0)
  - Columns: id, project_id, task_id, decision, reason, context, alternatives, created_at
- [x] **6.3.2** — Tạo Pydantic schemas cho Decision
  - File: `shared/schemas/decision.py`
  - `DecisionCreate`: project_id, task_id, decision, reason, context, alternatives
  - `DecisionResponse`: tất cả fields + id + project_name
- [x] **6.3.3** — Implement decision service
  - File: `services/memory/decision_service.py`
  - Function: `store_decision(project_id, task_id, decision, reason, context, alternatives) -> decision`
- [x] **6.3.4** — Implement decision retrieval
  - Function: `get_decisions(project_id, filters) -> decisions`
- [x] **6.3.5** — Build API: GET /api/v1/decisions
  - Query params: project_id, task_id, page, limit
  - Output: List[DecisionResponse] + pagination
- [x] **6.3.6** — Build API: POST /api/v1/decisions
  - Input: DecisionCreate
  - Output: DecisionResponse
- [x] **6.3.7** — Build API: GET /api/v1/decisions/{project_id}
  - Output: List[DecisionResponse] cho project đó
- [x] **6.3.8** — Implement decision linking
  - Link decision đến task và instruction
  - Function: `link_decision(decision_id, task_id, instruction_id) -> status`
- [x] **6.3.9** — Unit test cho decision history
  - Test store decision
  - Test get decisions
  - Test decision linking
  - Test pagination

### Output
- Decision history hoạt động
- CRUD API
- Tests pass

---

## 6.4. Memory Integration

### Mô tả
Tích hợp memory system vào các agents và workflow.

### Tasks
- [x] **6.4.1** — Tích hợp memory vào Gatekeeper (tra cứu task cũ)
  - Gatekeeper gọi semantic search khi nhận request
  - Function: `gatekeeper_memory_lookup(request) -> past_solutions`
  - Nếu có solution tương tự → return cached solution
- [x] **6.4.2** — Tích hợp memory vào Orchestrator (reuse solution)
  - Orchestrator gọi memory retrieval khi plan
  - Function: `orchestrator_memory_lookup(task_spec) -> relevant_solutions`
  - Use solutions để optimize task breakdown
- [x] **6.4.3** — Tích hợp memory vào Specialist (learn from past)
  - Specialist đọc failed patterns trước khi code
  - Function: `specialist_memory_lookup(task_spec) -> warnings`
  - Avoid patterns đã fail trước đó
- [x] **6.4.4** — Implement memory update sau mỗi task hoàn thành
  - Auto-store lesson learned, decisions, patterns
  - Function: `update_memory_after_task(task_id) -> memory_entries`
- [x] **6.4.5** — Implement memory quality control
  - Review memory entries trước khi store
  - Filter low-quality entries
  - Function: `quality_check_memory(entry) -> approved`
- [x] **6.4.6** — Integration test: memory system end-to-end
  - Tạo task → store memory → tạo task tương tự → retrieve memory
  - Verify memory giúp giảm thời gian xử lý
  - Verify memory quality

### Output
- Memory system tích hợp vào agents
- Auto-update memory
- Integration tests pass

---

## 6.5. Cache Layer

### Mô tả
Redis cache cho frequent queries — giảm latency, giảm database load.

### Tasks
- [x] **6.5.1** — Implement Redis cache service
  - File: `services/memory/cache_service.py`
  - Function: `cache_get(key) -> value`
  - Function: `cache_set(key, value, ttl) -> status`
- [x] **6.5.2** — Implement cache cho frequent queries
  - Cache: task lookups, memory search results, law checks
  - Key pattern: `cache:{type}:{id}`
- [x] **6.5.3** — Implement cache invalidation strategy
  - Invalidate khi data thay đổi
  - Function: `cache_invalidate(key) -> status`
  - Function: `cache_invalidate_pattern(pattern) -> status`
- [x] **6.5.4** — Implement cache TTL
  - Default TTL: 1 hour
  - Custom TTL per cache type
  - Function: `set_ttl(key, ttl) -> status`
- [x] **6.5.5** — Implement cache hit rate tracking
  - Track hit/miss ratio
  - Function: `get_cache_stats() -> { hits, misses, hit_rate }`
- [x] **6.5.6** — Unit test cho cache layer
  - Test cache get/set
  - Test invalidation
  - Test TTL
  - Test hit rate tracking

### Output
- Redis cache hoạt động
- Cache invalidation
- Tests pass

---

## Checklist Phase 6

| # | Task | Status | Notes |
|---|---|---|---|
| 6.1 | Instruction Ledger | ✅ | CRUD API + ledger service |
| 6.2 | Semantic Retrieval | ✅ | pgvector + pseudo-embedding + keyword fallback |
| 6.3 | Decision History | ✅ | CRUD API + decision linking |
| 6.4 | Memory Integration | ✅ | Redis cache + integration tests |
| 6.5 | Cache Layer | ✅ | TTL config, hit rate tracking |

**Definition of Done cho Phase 6:**
- [x] AI nhớ workflow cũ
- [x] Semantic retrieval hoạt động
- [x] Giảm mentor cost
- [x] Reuse solutions
- [x] Integration tests pass
