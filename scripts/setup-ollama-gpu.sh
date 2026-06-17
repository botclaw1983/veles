#!/usr/bin/env bash
# Настройка Ollama для GPU на RTX 4060 8GB (Veles)
set -euo pipefail

MODEL="${OLLAMA_MODEL:-qwen3-vl:4b-instruct}"
CUSTOM_MODEL="veles-vl"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Скачивание модели ${MODEL}..."
ollama pull "${MODEL}"

echo "==> Создание оптимизированной модели ${CUSTOM_MODEL}..."
ollama create "${CUSTOM_MODEL}" -f "${ROOT_DIR}/ollama/Modelfile.qwen3-vl-4b-gpu"

echo "==> Настройка systemd (требуется sudo)..."
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/veles-gpu.conf >/dev/null <<'EOF'
[Service]
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q4_0"
Environment="OLLAMA_CONTEXT_LENGTH=2048"
EOF

sudo systemctl daemon-reload
sudo systemctl restart ollama

echo "==> Проверка GPU..."
sleep 3
curl -s http://127.0.0.1:11434/api/generate \
  -d "{\"model\":\"${CUSTOM_MODEL}\",\"prompt\":\"ок\",\"stream\":false}" >/dev/null
ollama ps

echo ""
echo "Готово. В .env укажите: OLLAMA_MODEL=${CUSTOM_MODEL}"
