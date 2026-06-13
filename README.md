# Veles

Прототип системы автоматизации документооборота для управляющей компании ПИФ: получение документов из Diadoc, согласование и передача в Аванкор.

Подробное описание проекта, процессов и плана разработки — в [PROJECT.md](./PROJECT.md).  
Интеграция с «Аванкор: Паевые фонды» — в [INTEGRATION_AVANKOR.md](./INTEGRATION_AVANKOR.md).  
Интеграция с Diadoc — в [INTEGRATION_DIADOC.md](./INTEGRATION_DIADOC.md).

## Запуск

```bash
cd veles
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # при необходимости измените логин/пароль
streamlit run app/main.py
```

По умолчанию вход: `admin` / `admin` (переменные `VELES_AUTH_USER`, `VELES_AUTH_PASSWORD`).
