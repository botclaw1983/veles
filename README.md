# Veles

Прототип системы автоматизации документооборота для управляющей компании ПИФ: получение документов из Diadoc, согласование, передача в Аванкор, Спецдепозитарий и банк-клиент.

Подробное описание проекта, процессов и плана разработки — в [PROJECT.md](1.%20Описание%20проекта.md).  
Интеграция с Diadoc — в [INTEGRATION_DIADOC.md](5.%20Интеграция%20с%20Diadoc.md).  
Интеграция с «Аванкор: Паевые фонды» — в [INTEGRATION_AVANKOR.md](6.%20Интеграция%20с%20Аванкор.md).  
Интеграция со Спецдепозитарием — в [INTEGRATION_SPEC_DEP.md](8.%20Интеграция%20со%20Спецдепозитарием.md).  
Интеграция с банк-клиентом — в [INTEGRATION_BANK_CLIENT.md](7.%20Интеграция%20с%20Банк-клиентом.md).  
Роли пользователей — в [Роли пользователей](9.%20Роли%20пользователей.md).  
Применение ИИ (распознавание PDF) — в [AI.md](10.%20Применение%20ИИ.md).

## Стек технологий

| Среда | Технологии |
|-------|------------|
| **Прототип** (текущий репозиторий) | Python + **Streamlit** |
| **Продакшен** (целевая реализация) | **FastAPI** (backend) + **React** (frontend) |

Подробнее о выборе стека и преимуществах FastAPI + React — в [PROJECT.md](1.%20Описание%20проекта.md) (раздел 7) и [TECHNICAL_REQUIREMENTS.md](4.%20Технические%20требования%20и%20инфраструктура.md) (раздел 4).

##Обзорная информация по прототипу

Ссылка на Holst https://app.holst.so/share/b/e5a91c3c-098a-4b0e-9a4e-7341402ae85d
![[Pasted image 20260621235034.png]]

![[Pasted image 20260621234947.png]]
![[Pasted image 20260621235123.png]]
![[Pasted image 20260621235145.png]]
![[Pasted image 20260621235218.png]]

![[Pasted image 20260621235250.png]]
![[Pasted image 20260621235447.png]]
![[Pasted image 20260621235502.png]]
![[Pasted image 20260621235511.png]]
![[Pasted image 20260621235542.png]]
![[Pasted image 20260621235613.png]]
![[Pasted image 20260621235630.png]]


## Запуск (прототип на Streamlit)

Инструкции ниже относятся к **прототипу** в каталоге `app/`. Продакшен-сервис планируется на FastAPI + React.

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
