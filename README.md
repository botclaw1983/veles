# Veles

Прототип системы автоматизации документооборота для управляющей компании ПИФ: получение документов из Diadoc, согласование и передача в Аванкор.

Подробное описание проекта, процессов и плана разработки — в [PROJECT.md](./PROJECT.md).  
Интеграция с «Аванкор: Паевые фонды» — в [INTEGRATION_AVANKOR.md](./INTEGRATION_AVANKOR.md).  
Интеграция с Diadoc — в [INTEGRATION_DIADOC.md](./INTEGRATION_DIADOC.md).

## Запуск

### 1. Docker и PostgreSQL

```bash
sudo bash scripts/install_docker.sh
newgrp docker                    # или перелогиньтесь
bash scripts/setup_postgres.sh   # поднимет Postgres и создаст таблицы
```

Либо вручную:

```bash
docker compose up -d
```

База: `veles`, пользователь/пароль: `veles` / `veles_secret`, порт `5432`.  
Строка подключения — в `.env` (`DATABASE_URL`).

### Подключение через DBeaver

Контейнер Postgres должен быть запущен (`docker compose up -d`).

1. Откройте **DBeaver** → **База данных** → **Новое подключение** → **PostgreSQL**.
2. На вкладке **Main** укажите:

| Поле | Значение |
|------|----------|
| Host | `localhost` |
| Port | `5432` |
| Database | `veles` |
| Username | `veles` |
| Password | `veles_secret` |

3. Нажмите **Test Connection**. При первом подключении DBeaver предложит скачать драйвер PostgreSQL — согласитесь.
4. **Finish** — в дереве слева появится база `veles`.

**Строка JDBC** (если нужна вручную):

```text
jdbc:postgresql://localhost:5432/veles
```

**Основные таблицы Veles:**

| Таблица | Содержимое |
|---------|------------|
| `documents` | Документы и реквизиты |
| `document_approvers` | Согласующие по каждому документу |
| `diadoc_sync_state` | Курсор синхронизации Diadoc |

**Если подключение не удаётся:**

- Проверьте контейнер: `docker compose ps` — статус `veles-postgres` должен быть `running`.
- Убедитесь, что порт 5432 не занят другим Postgres на машине.
- На Linux при ошибке «connection refused» перезапустите: `docker compose restart postgres`.

### 2. Приложение

```bash
cd veles
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # при необходимости измените логин/пароль
streamlit run app/main.py
```

Сайт откроется по адресу: **http://localhost:8501**

По умолчанию вход: `admin` / `admin` (переменные `VELES_AUTH_USER`, `VELES_AUTH_PASSWORD`).

**Запуск без активации venv** (если `streamlit: command not found`):

```bash
cd veles
.venv/bin/streamlit run app/main.py
```

Команда `streamlit` доступна только внутри виртуального окружения — после `python3 -m venv .venv` нужно либо выполнить `source .venv/bin/activate`, либо вызывать `.venv/bin/streamlit` напрямую. Зависимости устанавливаются один раз: `pip install -r requirements.txt` (или `.venv/bin/pip install -r requirements.txt`).

Без запущенного PostgreSQL (см. раздел 1) часть функций приложения может не работать.
