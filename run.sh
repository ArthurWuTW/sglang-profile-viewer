#!/usr/bin/env bash
#
# run.sh - Build the frontend and start the backend for the SGLang Profiler Viewer.
#
# Usage:
#   ./run.sh                 # build frontend (if needed) + start backend
#   ./run.sh --no-build      # skip the frontend build, just start the backend
#   ./run.sh --rebuild       # force a clean frontend rebuild
#
# Configuration is via environment variables (see README.md for the full list):
#   PROFILE_ROOT   directory scanned for *.json.gz traces (default /root/.cache/profile_log)
#   HOST           bind host (default 0.0.0.0)
#   PORT           bind port (default 6006)
#   LOG_LEVEL      backend log level (default INFO)
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve repo root (the directory containing this script)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}"
FRONTEND_DIR="${REPO_ROOT}/frontend"
BACKEND_DIR="${REPO_ROOT}/backend"
DIST_DIR="${FRONTEND_DIR}/dist"

# ---------------------------------------------------------------------------
# Parse flags
# ---------------------------------------------------------------------------
DO_BUILD=1
FORCE_REBUILD=0
for arg in "$@"; do
  case "${arg}" in
    --no-build)  DO_BUILD=0 ;;
    --rebuild)   FORCE_REBUILD=1 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown option: ${arg}" >&2
      echo "Usage: $0 [--no-build] [--rebuild]" >&2
      exit 1
      ;;
  esac
done

log()  { echo "[run] $*"; }
warn() { echo "[run] WARNING: $*" >&2; }
die()  { echo "[run] ERROR: $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Pick a Python interpreter (prefer 3.12, fall back to python3)
# ---------------------------------------------------------------------------
if command -v python3.12 >/dev/null 2>&1; then
  PYTHON=python3.12
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  die "No python3 interpreter found on PATH."
fi

# ---------------------------------------------------------------------------
# Frontend build
# ---------------------------------------------------------------------------
build_frontend() {
  if [[ ! -d "${FRONTEND_DIR}" ]]; then
    warn "Frontend directory not found at ${FRONTEND_DIR}; skipping build."
    return 0
  fi

  if ! command -v npm >/dev/null 2>&1; then
    warn "npm not found on PATH; skipping frontend build."
    warn "The backend will serve the existing ${DIST_DIR} if present."
    return 0
  fi

  # Install dependencies if node_modules is missing.
  if [[ ! -d "${FRONTEND_DIR}/node_modules" ]]; then
    log "Installing frontend dependencies (npm install)..."
    (cd "${FRONTEND_DIR}" && npm install)
  fi

  # Decide whether a build is required.
  local need_build=0
  if [[ "${FORCE_REBUILD}" -eq 1 ]]; then
    need_build=1
    log "Forcing frontend rebuild."
  elif [[ ! -f "${DIST_DIR}/index.html" ]]; then
    need_build=1
    log "No built frontend found; building."
  else
    # Rebuild if any source file is newer than the last build output.
    local newest_src
    newest_src="$(find "${FRONTEND_DIR}/src" "${FRONTEND_DIR}/index.html" \
      "${FRONTEND_DIR}/package.json" -type f -newer "${DIST_DIR}/index.html" \
      -print -quit 2>/dev/null || true)"
    if [[ -n "${newest_src}" ]]; then
      need_build=1
      log "Frontend sources changed since last build; rebuilding."
    fi
  fi

  if [[ "${need_build}" -eq 1 ]]; then
    log "Building frontend (npm run build)..."
    (cd "${FRONTEND_DIR}" && npm run build)
    log "Frontend build complete -> ${DIST_DIR}"
  else
    log "Frontend already up to date; skipping build."
  fi
}

# ---------------------------------------------------------------------------
# Backend dependency check
# ---------------------------------------------------------------------------
check_backend_deps() {
  if ! "${PYTHON}" -c "import fastapi, uvicorn, watchdog, yaml, pydantic" >/dev/null 2>&1; then
    warn "Backend dependencies missing; attempting 'pip install -e ${BACKEND_DIR}'..."
    "${PYTHON}" -m pip install -e "${BACKEND_DIR}"
  fi
}

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if [[ "${DO_BUILD}" -eq 1 ]]; then
  build_frontend
fi

check_backend_deps

# Default the profile root if the caller did not set one.
export PROFILE_ROOT="${PROFILE_ROOT:-/root/.cache/profile_log}"
export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-6006}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
# Point the backend at the built frontend and the mappings directory.
export FRONTEND_DIST="${FRONTEND_DIST:-${DIST_DIR}}"
export MAPPINGS_DIR="${MAPPINGS_DIR:-${REPO_ROOT}/mappings}"

log "Starting backend on http://${HOST}:${PORT} (profile_root=${PROFILE_ROOT})"
log "  FRONTEND_DIST=${FRONTEND_DIST}"
log "  MAPPINGS_DIR=${MAPPINGS_DIR}"

# Run uvicorn from the backend directory so the 'app' package is importable.
cd "${BACKEND_DIR}"
exec "${PYTHON}" -m uvicorn app.main:app --host "${HOST}" --port "${PORT}"
