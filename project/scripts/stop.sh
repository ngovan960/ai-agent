#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "Stopping Docker services..."
docker-compose down 2>/dev/null || docker compose down 2>/dev/null || true

echo "Stopping background processes..."
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "next-server" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true

# Robustly clear ports 3000 and 8000 if still occupied
for port in 3000 8000; do
  if command -v fuser &>/dev/null; then
    fuser -k -n tcp $port 2>/dev/null || true
  elif command -v lsof &>/dev/null; then
    pids=$(lsof -t -i :$port)
    if [ -n "$pids" ]; then
      kill -9 $pids 2>/dev/null || true
    fi
  fi
done

echo "✓ All services stopped"
