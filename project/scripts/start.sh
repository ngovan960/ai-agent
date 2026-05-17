#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${CYAN}[$(date +%H:%M:%S)]${NC} $1"; }
ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }

# ── Header ──
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║    AI SDLC Orchestrator — Quick Start    ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── Cleanup existing services ──
log "Checking and cleaning up any existing services..."
bash scripts/stop.sh >/dev/null 2>&1 || true
ok "Environment cleaned"

# Detect compose command
COMPOSE="docker compose"
if command -v docker-compose &>/dev/null; then
  COMPOSE="docker-compose"
fi

# ── Step 0: .env ──
if [ ! -f ".env" ]; then
  log "Creating .env from .env.example..."
  cp .env.example .env
  ok ".env created"
else
  ok ".env exists"
fi

# ── Step 1: Docker services ──
log "Starting PostgreSQL & Redis..."
$COMPOSE up -d postgres redis 2>&1 | grep -v "Network\|Volume" || true
ok "PostgreSQL & Redis started"

log "Waiting for PostgreSQL to be ready..."
for i in $(seq 1 30); do
  health=$(docker inspect project-postgres-1 --format '{{.State.Health.Status}}' 2>/dev/null)
  [ "$health" = "healthy" ] && break
  if docker inspect project-postgres-1 --format '{{.State.Status}}' 2>/dev/null | grep -q exited; then
    fail "PostgreSQL exited: $(docker logs project-postgres-1 2>&1 | tail -3)"
  fi
  sleep 2
done
ok "PostgreSQL ready"

# ── Step 2: Install deps ──
log "Installing Python dependencies..."
pip install -q -r requirements.txt 2>/dev/null || true
ok "Python deps ready"

log "Installing frontend dependencies..."
cd apps/dashboard
if [ ! -d "node_modules" ]; then
  npm install 2>&1 | tail -3
fi
cd "$ROOT_DIR"
ok "Frontend deps ready"

# ── Step 3: Start backend ──
log "Starting backend on :8000..."
PYTHONPATH="$ROOT_DIR" uvicorn services.orchestrator.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
ok "Backend started (PID $BACKEND_PID)"

sleep 2

# ── Step 4: Start frontend ──
log "Starting frontend on :3000..."
cd apps/dashboard
npx next dev -p 3000 &
FRONTEND_PID=$!
cd "$ROOT_DIR"
ok "Frontend started (PID $FRONTEND_PID)"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           All services running           ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC}  Dashboard  ${YELLOW}→${NC} http://localhost:3000    ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  API        ${YELLOW}→${NC} http://localhost:8000    ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  API Docs   ${YELLOW}→${NC} http://localhost:8000/docs${GREEN}║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
warn "Press Ctrl+C to stop all services"

# ── Cleanup on exit ──
cleanup() {
  echo ""
  log "Stopping services..."
  kill $BACKEND_PID 2>/dev/null || true
  kill $FRONTEND_PID 2>/dev/null || true
  ok "Services stopped"
  exit 0
}
trap cleanup SIGINT SIGTERM

wait
