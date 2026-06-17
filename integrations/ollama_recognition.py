"""Распознавание реквизитов из PDF через Ollama (Qwen VL)."""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import fitz
from ollama import Client

from config.settings import settings

EXTRACTION_PROMPT = """Ты извлекаешь реквизиты из российского бухгалтерского документа (счёт, УПД, акт).
Верни ТОЛЬКО JSON без markdown и пояснений со следующими полями:
{
  "document_type": "invoice|act|utd|turnover",
  "counterparty_name": "название контрагента",
  "counterparty_inn": "ИНН контрагента или пустая строка",
  "fund_name": "получатель / юр. лицо фонда или пустая строка",
  "fund_inn": "ИНН получателя или пустая строка",
  "amount": 12345.67,
  "period_from": "YYYY-MM-DD или null",
  "period_to": "YYYY-MM-DD или null",
  "description": "краткое назначение платежа"
}
Если поле не найдено — пустая строка, для amount — null, для дат — null."""


@dataclass
class ExtractedFields:
    document_type: str | None = None
    counterparty_name: str = ""
    counterparty_inn: str = ""
    fund_name: str = ""
    fund_inn: str = ""
    amount: float | None = None
    period_from: date | None = None
    period_to: date | None = None
    description: str = ""


def _client() -> Client:
    return Client(host=settings.ollama_host)


def pdf_pages_to_base64(pdf_path: Path, *, max_pages: int = 2, dpi_scale: float = 1.5) -> list[str]:
    """Рендерит первые страницы PDF в PNG (base64) для vision-модели."""
    doc = fitz.open(pdf_path)
    images: list[str] = []
    try:
        matrix = fitz.Matrix(dpi_scale, dpi_scale)
        for page_num in range(min(doc.page_count, max_pages)):
            pix = doc.load_page(page_num).get_pixmap(matrix=matrix, alpha=False)
            images.append(base64.b64encode(pix.tobytes("png")).decode())
    finally:
        doc.close()
    return images


def _parse_date(value: object) -> date | None:
    if not value or value == "null":
        return None
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _to_extracted(data: dict) -> ExtractedFields:
    amount = data.get("amount")
    if amount is not None:
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            amount = None

    doc_type = data.get("document_type")
    if doc_type:
        doc_type = str(doc_type).strip().lower() or None

    return ExtractedFields(
        document_type=doc_type,
        counterparty_name=str(data.get("counterparty_name") or "").strip(),
        counterparty_inn=str(data.get("counterparty_inn") or "").strip(),
        fund_name=str(data.get("fund_name") or "").strip(),
        fund_inn=str(data.get("fund_inn") or "").strip(),
        amount=amount,
        period_from=_parse_date(data.get("period_from")),
        period_to=_parse_date(data.get("period_to")),
        description=str(data.get("description") or "").strip(),
    )


def extract_fields_from_pdf(pdf_path: Path | str) -> ExtractedFields:
    """Извлекает реквизиты из PDF через Ollama vision-модель."""
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF не найден: {path}")

    images = pdf_pages_to_base64(path)
    if not images:
        raise ValueError("PDF не содержит страниц")

    response = _client().chat(
        model=settings.ollama_model,
        messages=[
            {
                "role": "user",
                "content": EXTRACTION_PROMPT,
                "images": images,
            }
        ],
        think=False,
        options={
            "num_ctx": settings.ollama_num_ctx,
            "num_predict": 1024,
            "temperature": 0.1,
        },
    )

    content = response.message.content or response.message.thinking or ""
    data = _parse_json_response(content)
    return _to_extracted(data)


def check_ollama_available() -> tuple[bool, str]:
    """Проверяет доступность Ollama и модели."""
    try:
        models = _client().list().models
        names = {m.model for m in models}
        target = settings.ollama_model
        installed = target in names or f"{target}:latest" in names or any(
            name.split(":")[0] == target for name in names
        )
        if not installed:
            return False, f"Модель {target} не установлена. Выполните: bash scripts/setup-ollama-gpu.sh"
        return True, ""
    except Exception as exc:  # noqa: BLE001 — показываем пользователю причину
        return False, f"Ollama недоступна ({settings.ollama_host}): {exc}"
