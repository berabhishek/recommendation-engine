#!/bin/sh

set -eu

server_pid=""

cleanup() {
  if [ -n "$server_pid" ] && kill -0 "$server_pid" >/dev/null 2>&1; then
    kill "$server_pid" >/dev/null 2>&1 || true
    wait "$server_pid" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

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

curl -fsS "http://127.0.0.1:3000/movies?pageSize=2" >/tmp/recommendation-test-movies.json
curl -fsS "http://127.0.0.1:3000/movies/tt0000001" >/tmp/recommendation-test-movie.json
curl -fsS \
  -X POST "http://127.0.0.1:3000/recommendations" \
  -H "Content-Type: application/json" \
  -d '{"selectedMovieIds":["tt0000001"],"pageSize":1}' \
  >/tmp/recommendation-test-recommendations.json

cleanup
if [ "${KEEP_TEST_DB:-0}" = "1" ]; then
  test -e /data/recommendation-test.db
else
  rm -f /data/recommendation-test.db
  test ! -e /data/recommendation-test.db
fi
