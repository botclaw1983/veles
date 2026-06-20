from pathlib import Path

from dotenv import load_dotenv
import os

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings:
    app_title: str = "Veles"
    data_dir: Path = ROOT_DIR / "data" / "documents"
    pdf_docs_dir: Path = ROOT_DIR / "pdf_docs"
    contracts_dir: Path = ROOT_DIR / "contracts"

    diadoc_api_url: str = os.getenv("DIADOC_API_URL", "https://diadoc-api.kontur.ru")
    diadoc_client_id: str | None = os.getenv("DIADOC_CLIENT_ID")
    diadoc_access_token: str | None = os.getenv("DIADOC_ACCESS_TOKEN")
    diadoc_box_ids: list[str] = [
        box_id.strip()
        for box_id in os.getenv("DIADOC_BOX_IDS", "").split(",")
        if box_id.strip()
    ]

    avankor_base_url: str | None = os.getenv("AVANKOR_BASE_URL")

    ollama_host: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "veles-vl")
    ollama_num_ctx: int = int(os.getenv("OLLAMA_NUM_CTX", "4096"))

    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://veles:veles_secret@localhost:5432/veles",
    )

    # Заглушка авторизации для прототипа
    auth_username: str = os.getenv("VELES_AUTH_USER", "admin")
    auth_password: str = os.getenv("VELES_AUTH_PASSWORD", "admin")

    default_approvers: list[tuple[str, str]] = [
        ("Иванов А.А.", "Главный бухгалтер"),
        ("Петров В.В.", "Финансовый директор"),
        ("Сидорова Е.Е.", "Руководитель бэк-офиса"),
        ("Козлов М.И.", "Юрист"),
        ("Новикова Т.С.", "Руководитель отдела закупок"),
        ("Фёдоров Н.П.", "Заместитель генерального директора"),
        ("Смирнов О.А.", "Финансовый контролёр"),
        ("Кузнецов А.И.", "Экономист"),
        ("Попов А.П.", "Начальник отдела казначейства"),
    ]


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.pdf_docs_dir.mkdir(parents=True, exist_ok=True)
settings.contracts_dir.mkdir(parents=True, exist_ok=True)
