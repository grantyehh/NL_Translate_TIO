#!/usr/bin/env bash
# Render kag_config.template.yaml → kag_config.yaml with env var substitution.
# 必跑於 `knext project restore` / `knext schema commit` / `python builder/indexer.py` 之前。
#
# Required env:
#   GRAPHRAG_API_KEY
#   GRAPHRAG_LLM_MODEL
#   GRAPHRAG_EMBEDDING_MODEL

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Allow caller to source .env first; or load from default location.
if [ -z "${GRAPHRAG_API_KEY:-}" ] && [ -f /Users/grantyeh/Grant/Project/CHT/.env ]; then
  set -a
  # shellcheck disable=SC1091
  source /Users/grantyeh/Grant/Project/CHT/.env
  set +a
fi

if [ -z "${GRAPHRAG_API_KEY:-}" ] || [ -z "${GRAPHRAG_LLM_MODEL:-}" ] || [ -z "${GRAPHRAG_EMBEDDING_MODEL:-}" ]; then
  echo "ERR: GRAPHRAG_API_KEY / GRAPHRAG_LLM_MODEL / GRAPHRAG_EMBEDDING_MODEL not all set" >&2
  exit 1
fi

VENV_PY="/Users/grantyeh/Grant/Project/CHT/TIO_Experiment/KAG/.venv/bin/python"
"$VENV_PY" - <<'PY'
import os
from jinja2 import Template
with open('kag_config.template.yaml') as f:
    rendered = Template(f.read()).render(**dict(os.environ))
with open('kag_config.yaml', 'w') as f:
    f.write(rendered)
PY

echo "kag_config.yaml regenerated."
