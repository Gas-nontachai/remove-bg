#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import base64
png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAFUlEQVR4nGP8//8/AzbAhFV00EoAAFbUAw037MyjAAAAAElFTkSuQmCC"
with open("/tmp/rmbg_ci_smoke.png", "wb") as f:
    f.write(base64.b64decode(png_b64))
PY

resp=$(curl -sS -X POST -F "file=@/tmp/rmbg_ci_smoke.png" -F "feather_radius=0" -F "alpha_boost=1" http://127.0.0.1:8000/api/jobs/remove-bg)
if [[ -z "${resp}" || "${resp:0:1}" != "{" ]]; then
  echo "unexpected submit response: ${resp}" >&2
  exit 4
fi
job_id=$(python3 - <<'PY' "$resp"
import json,sys
print(json.loads(sys.argv[1])["job_id"])
PY
)

for i in $(seq 1 60); do
  status=$(curl -sS "http://127.0.0.1:8000/api/jobs/${job_id}")
  state=$(python3 - <<'PY' "$status"
import json,sys
print(json.loads(sys.argv[1])["status"])
PY
)
  if [[ "$state" == "finished" ]]; then
    curl -sS "http://127.0.0.1:8000/api/jobs/${job_id}/download" -o /tmp/rmbg_ci_out.png
    file /tmp/rmbg_ci_out.png | grep -q "PNG image data"
    exit 0
  fi
  if [[ "$state" == "failed" ]]; then
    echo "job failed: $status" >&2
    exit 2
  fi
  sleep 1
done

echo "timeout waiting for job ${job_id}" >&2
exit 3
