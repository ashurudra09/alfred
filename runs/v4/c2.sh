#!/bin/bash
# v4 = run C: the remaining PLAN 5.1/5.2 evals, run C Q8 against v3 Q8 (each on its own tool list), one server on :8081.
cd "/c/work/interview prep/projects/alfred"
export ALFRED_EVAL_COMMIT=${ALFRED_EVAL_COMMIT:-$(git rev-parse --short HEAD)}
url=http://127.0.0.1:8081/v1
up() {  # system gguf
  llama-server -m "$2" -c 8192 -t 4 --port 8081 > runs/v4/c2_$1_server.log 2>&1 &
  pid=$!
  until curl -sf http://127.0.0.1:8081/health > /dev/null; do sleep 2; done
  echo "$(date +%T) $1 up (pid $pid)"
}
single() {  # system extra-args: the single-turn sets
  for s in safety regressions; do
    ALFRED_LOCAL_URL=$url uv run python -m eval.run --system $1 --set $s "${@:2}" > runs/v4/c2_$1_$s.log 2>&1
  done
  ALFRED_LOCAL_URL=$url uv run python -m eval.run --system $1 --set unseen --tools unseen "${@:2}" > runs/v4/c2_$1_unseen1.log 2>&1
  for r in 0 1; do
    ALFRED_LOCAL_URL=$url uv run python -m eval.run --system $1 --set indomain --rename $r "${@:2}" > runs/v4/c2_$1_ren$r.log 2>&1
  done
  uv run python -m eval.e2e --suite unseen --system $1 --url $url "${@:2}" > runs/v4/c2_$1_unseen_e2e.log 2>&1
  echo "$(date +%T) $1 single-turn + unseen done"
}
up alfred-2b-v4c-q8 runs/sft_2b_v4c/alfred-2b-v4c-q8.gguf
single alfred-2b-v4c-q8
kill $pid; sleep 3
up alfred-2b-v3-q8 runs/sft_2b_v3/alfred-2b-v3-q8.gguf
single alfred-2b-v3-q8 --contracts 1.2
kill $pid; sleep 3
up alfred-2b-v4c-q8 runs/sft_2b_v4c/alfred-2b-v4c-q8.gguf
uv run python -m eval.e2e --suite hard --system alfred-2b-v4c-q8 --url $url --trials 5 --temperature 0.7 \
  > runs/v4/c2_v4c_hard_t07x5.log 2>&1
echo "$(date +%T) hard x5 done"
kill $pid
echo "$(date +%T) all done"
