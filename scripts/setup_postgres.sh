#!/usr/bin/env bash
# Полная настройка: Docker + PostgreSQL для Veles.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker не найден. Сначала выполните:"
  echo "  sudo bash scripts/install_docker.sh"
  echo "  newgrp docker   # или перелогиньтесь"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Нет доступа к Docker. Выполните: newgrp docker"
  echo "или перелогиньтесь после install_docker.sh"
  exit 1
fi

docker compose up -d

echo "Ожидание PostgreSQL..."
for _ in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U veles -d veles >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if [ -d .venv ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

pip install -q -r requirements.txt
python -c "from db import init_db; init_db(); print('Таблицы PostgreSQL созданы.')"

echo ""
echo "Готово. Запуск приложения:"
echo "  streamlit run app/main.py"
