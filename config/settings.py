from pathlib import Path

from dotenv import load_dotenv
import os

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings:
    app_title: str = "Veles"
    data_dir: Path = ROOT_DIR / "data" / "documents"
    pdf_docs_dir: Path = ROOT_DIR / "pdf_docs"

    diadoc_api_url: str = os.getenv("DIADOC_API_URL", "https://diadoc-api.kontur.ru")
    diadoc_client_id: str | None = os.getenv("DIADOC_CLIENT_ID")
    diadoc_access_token: str | None = os.getenv("DIADOC_ACCESS_TOKEN")

    avankor_base_url: str | None = os.getenv("AVANKOR_BASE_URL")

    # Заглушка авторизации для прототипа
    auth_username: str = os.getenv("VELES_AUTH_USER", "admin")
    auth_password: str = os.getenv("VELES_AUTH_PASSWORD", "admin")

    default_approvers: list[tuple[str, str]] = [
        ("Иванов А.А.", "Бухгалтер"),
        ("Петров В.В.", "Руководитель отдела"),
        ("Сидорова Е.Е.", "Финансовый контролёр"),
    ]


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.pdf_docs_dir.mkdir(parents=True, exist_ok=True)
