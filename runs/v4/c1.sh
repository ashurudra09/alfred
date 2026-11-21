#!/bin/bash
# Run C scoring: one model on one llama-server port, all four suites, current prompt 1.2 / contracts 1.3.
# Usage: bash runs/v4/c1.sh <system> <gguf> <port>   (never 8080: the user's UI). Stops only its own server.
cd "/c/work/interview prep/projects/alfred"
export ALFRED_EVAL_COMMIT=${ALFRED_EVAL_COMMIT:-$(git rev-parse --short HEAD)}
sys=$1 model=$2 port=$3
url=http://127.0.0.1:$port/v1
log=runs/v4/c1_${sys}
llama-server -m "$model" -c 8192 -t 4 --port $port > ${log}_server.log 2>&1 &
pid=$!
until curl -sf http://127.0.0.1:$port/health > /dev/null; do sleep 2; done
echo "$(date +%T) $sys up on $port (pid $pid)"
[ "${SKIP_INDOMAIN:-}" ] || ALFRED_LOCAL_URL=$url uv run python -m eval.run --system $sys --set indomain > ${log}_indomain.log 2>&1
echo "$(date +%T) indomain done"
uv run python -m eval.e2e --suite e2e --system $sys --url $url > ${log}_e2e.log 2>&1; echo "$(date +%T) e2e done"
uv run python -m eval.e2e --suite hard --system $sys --url $url > ${log}_hard.log 2>&1; echo "$(date +%T) hard done"
uv run python -m eval.security --system $sys --url $url > ${log}_security.log 2>&1; echo "$(date +%T) security done"
kill $pid
echo "$(date +%T) $sys all done"
