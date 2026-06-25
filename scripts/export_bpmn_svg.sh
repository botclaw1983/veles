#!/usr/bin/env bash
# Экспорт BPMN 2.0 XML в SVG через Docker (Node.js + bpmn-to-image + Chromium).
# Использование:
#   ./scripts/export_bpmn_svg.sh diagrams/2.1-invoice-payment.bpmn
#   ./scripts/export_bpmn_svg.sh diagrams/2.1-invoice-payment.bpmn diagrams/2.1-invoice-payment.svg

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT="${1:-}"
OUTPUT="${2:-}"

if [[ -z "$INPUT" ]]; then
  echo "Usage: $0 <input.bpmn> [output.svg]" >&2
  exit 1
fi

if [[ "$INPUT" != /* ]]; then
  INPUT="$ROOT/$INPUT"
fi

if [[ ! -f "$INPUT" ]]; then
  echo "File not found: $INPUT" >&2
  exit 1
fi

if [[ -z "$OUTPUT" ]]; then
  OUTPUT="${INPUT%.bpmn}.svg"
elif [[ "$OUTPUT" != /* ]]; then
  OUTPUT="$ROOT/$OUTPUT"
fi

INPUT_REL="${INPUT#$ROOT/}"
OUTPUT_REL="${OUTPUT#$ROOT/}"

docker run --rm \
  --shm-size=1gb \
  -v "$ROOT:/work" \
  -w /work \
  node:22-bookworm-slim \
  bash -lc "
    set -euo pipefail
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq chromium fonts-liberation >/dev/null
    export PUPPETEER_SKIP_DOWNLOAD=1
    export PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
    npm install --no-save bpmn-to-image@0.10.0
    node -e \"
      const fs = require('fs');
      const file = '/work/node_modules/bpmn-to-image/index.js';
      let source = fs.readFileSync(file, 'utf8');
      if (!source.includes('--no-sandbox')) {
        source = source.replace(
          'browser = await puppeteer.launch({',
          'browser = await puppeteer.launch({ args: [\\\"--no-sandbox\\\", \\\"--disable-setuid-sandbox\\\", \\\"--disable-dev-shm-usage\\\"],'
        );
        fs.writeFileSync(file, source);
      }
    \"
    npx bpmn-to-image \"/work/$INPUT_REL:/work/$OUTPUT_REL\"
  "

echo "Exported: $OUTPUT_REL"
