#!/usr/bin/env bash
# Установка Docker на Ubuntu (нужен sudo).
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Запустите с sudo:"
  echo "  sudo bash scripts/install_docker.sh"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y ca-certificates curl gnupg

# Официальный репозиторий Docker (для Ubuntu используем codename из os-release)
. /etc/os-release
ARCH="$(dpkg --print-architecture)"
CODENAME="${VERSION_CODENAME:-noble}"

install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
fi

echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update

if ! apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin; then
  echo ""
  echo "Репозиторий Docker для ${CODENAME} недоступен — ставим пакеты Ubuntu..."
  apt-get install -y docker.io docker-compose-v2
fi

systemctl enable --now docker

TARGET_USER="${SUDO_USER:-$USER}"
if [ "$TARGET_USER" != "root" ]; then
  usermod -aG docker "$TARGET_USER"
  echo ""
  echo "Пользователь ${TARGET_USER} добавлен в группу docker."
  echo "Выйдите из сессии и войдите снова (или выполните: newgrp docker)"
fi

docker --version
docker compose version 2>/dev/null || docker-compose --version

echo ""
echo "Docker установлен."
