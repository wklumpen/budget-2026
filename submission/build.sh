#!/usr/bin/env bash
# Build docs/submission.pdf from submission/submission.html (WeasyPrint)
set -euo pipefail
cd "$(dirname "$0")"
${PY:-python3} -m weasyprint submission.html ../docs/submission.pdf
