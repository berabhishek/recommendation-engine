#!/bin/sh

set -eu

keep_db=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --keep-db)
      keep_db=1
      ;;
    --delete-db)
      keep_db=0
      ;;
    -h|--help)
      cat <<'EOF'
Usage: docker_smoke_test.sh [--keep-db|--delete-db]

Runs the fixture-backed smoke test.
By default the recommendation-test database is deleted after the checks pass.
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
  shift
done

server_pid=""

cleanup() {
  if [ -n "$server_pid" ] && kill -0 "$server_pid" >/dev/null 2>&1; then
    kill "$server_pid" >/dev/null 2>&1 || true
    wait "$server_pid" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

python -c 'from scripts.docker_entrypoint import bootstrap_database; bootstrap_database()'

python -m uvicorn app.main:app --host 0.0.0.0 --port 3000 >/tmp/recommendation-test.log 2>&1 &
server_pid=$!
attempts=0

until curl -fsS http://127.0.0.1:3000/health >/dev/null 2>&1; do
  if [ "$attempts" -ge 60 ]; then
    cat /tmp/recommendation-test.log >&2 || true
    exit 1
  fi
  attempts=$((attempts + 1))
  sleep 1
done

check_curl() {
  label=$1
  shift
  response_file="/tmp/recommendation-test-${label}.json"
  if ! curl -fsS "$@" >"$response_file"; then
    echo "Request failed: $label" >&2
    cat "$response_file" >&2 || true
    cat /tmp/recommendation-test.log >&2 || true
    exit 1
  fi
}

check_curl movies "http://127.0.0.1:3000/movies?pageSize=2"
check_curl movie "http://127.0.0.1:3000/movies/tt0000001"
check_curl recommendations \
  -X POST "http://127.0.0.1:3000/recommendations" \
  -H "Content-Type: application/json" \
  -d '{"selectedMovieIds":["tt0000001"],"pageSize":1}' \
  >/tmp/recommendation-test-recommendations.json

cleanup
if [ "$keep_db" -eq 1 ]; then
  test -e /data/recommendation-test.db
else
  rm -f /data/recommendation-test.db
  test ! -e /data/recommendation-test.db
fi
