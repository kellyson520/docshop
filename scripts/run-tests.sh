#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="${FRONTEND_DIR:-${ROOT_DIR}/frontend}"
BACKEND_DIR="${BACKEND_DIR:-${ROOT_DIR}/backend}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { printf "${BLUE}[INFO]${NC} %s\n" "$*"; }
success() { printf "${GREEN}[SUCCESS]${NC} %s\n" "$*"; }
warn() { printf "${YELLOW}[WARN]${NC} %s\n" "$*"; }
fail() { printf "${RED}[ERROR]${NC} %s\n" "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
DocShop test runner

Usage:
  scripts/run-tests.sh [options] <frontend|backend|e2e|integration|performance|security|all>

Options:
  -h, --help       Show help.
  -v, --verbose    Verbose/headed E2E output.
  -c, --coverage   Generate coverage reports where supported.
  -w, --watch      Run frontend tests in watch mode.

Environment overrides:
  FRONTEND_DIR=/path/to/frontend
  BACKEND_DIR=/path/to/backend
EOF
}

require_dir() {
  [[ -d "$1" ]] || fail "Directory not found: $1"
}

run_frontend_tests() {
  require_dir "${FRONTEND_DIR}"
  log "Running frontend unit tests"
  cd "${FRONTEND_DIR}"
  if [[ "${COVERAGE}" == true ]]; then
    npm run test:coverage
  elif [[ "${WATCH}" == true ]]; then
    npm run test
  else
    npm run test -- --run
  fi
  success "Frontend tests passed"
}

run_backend_tests() {
  require_dir "${BACKEND_DIR}"
  log "Running backend unit tests"
  cd "${BACKEND_DIR}"
  if [[ "${COVERAGE}" == true ]]; then
    python -m pytest tests/unit -v --cov=app --cov-report=html:../artifacts/coverage/backend-htmlcov --cov-report=term
  else
    python -m pytest tests/unit -v --no-cov
  fi
  success "Backend unit tests passed"
}

run_integration_tests() {
  require_dir "${BACKEND_DIR}"
  log "Running backend integration tests"
  cd "${BACKEND_DIR}"
  python -m pytest tests/integration -v --no-cov
  success "Integration tests passed"
}

run_e2e_tests() {
  require_dir "${FRONTEND_DIR}"
  log "Running Playwright E2E tests"
  cd "${FRONTEND_DIR}"
  npx playwright install chromium
  if [[ "${VERBOSE}" == true ]]; then
    npx playwright test --headed
  else
    npx playwright test
  fi
  success "E2E tests passed"
}

run_performance_tests() {
  require_dir "${BACKEND_DIR}"
  log "Running backend performance tests"
  cd "${BACKEND_DIR}"
  python -m pytest tests/performance -v --no-cov
  success "Performance tests passed"
}

run_security_tests() {
  require_dir "${BACKEND_DIR}"
  log "Running backend security tests"
  cd "${BACKEND_DIR}"
  python -m pytest tests/security -v --no-cov
  success "Security tests passed"
}

run_all_tests() {
  run_frontend_tests
  run_backend_tests
  run_integration_tests
  run_e2e_tests
  run_security_tests
  success "All requested tests passed"
}

VERBOSE=false
COVERAGE=false
WATCH=false
TEST_TYPE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    -v|--verbose) VERBOSE=true; shift ;;
    -c|--coverage) COVERAGE=true; shift ;;
    -w|--watch) WATCH=true; shift ;;
    frontend|backend|e2e|integration|performance|security|all) TEST_TYPE="$1"; shift ;;
    *) fail "Unknown option or test type: $1" ;;
  esac
done

if [[ -z "${TEST_TYPE}" ]]; then
  usage
  exit 0
fi

case "${TEST_TYPE}" in
  frontend) run_frontend_tests ;;
  backend) run_backend_tests ;;
  e2e) run_e2e_tests ;;
  integration) run_integration_tests ;;
  performance) run_performance_tests ;;
  security) run_security_tests ;;
  all) run_all_tests ;;
  *) fail "Unknown test type: ${TEST_TYPE}" ;;
esac
