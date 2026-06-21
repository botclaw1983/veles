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
from models.document import normalize_inn

EXTRACTION_PROMPT = """Извлеки реквизиты из российского документа (счёт, УПД, акт) и верни один JSON-объект.

Обязательные ключи (все должны присутствовать):
document_type, counterparty_name, counterparty_inn, fund_name, fund_inn, zpif_name, amount, period_from, period_to, description

Пример ответа:
{"document_type":"utd","counterparty_name":"ООО «Пример»","counterparty_inn":"7701234567","fund_name":"ООО «Покупатель»","fund_inn":"7707654321","zpif_name":"","amount":3660.00,"period_from":null,"period_to":null,"description":"Оплата по счёту"}

Правила:
- document_type: invoice, act, utd или turnover
- counterparty_name: поставщик / продавец
- fund_name: покупатель / получатель
- counterparty_inn и fund_inn: только 10 или 12 цифр, иначе ""
- amount: число или null
- period_from, period_to: YYYY-MM-DD или null
- без markdown, без комментариев, без текста до или после JSON
- в текстовых значениях не используй символ двойной кавычки — замени на «»"""

SYSTEM_PROMPT = (
    "Ты OCR-система для бухгалтерских документов РФ. "
    "Отвечай только валидным JSON-объектом с указанными ключами."
)

CONTRACT_ANALYSIS_SYSTEM_PROMPT = (
    "Ты помощник бухгалтера управляющей компании ЗПИФ. "
    "Анализируешь счета и договоры с контрагентами. Отвечай на русском языке."
)

DEFAULT_CONTRACT_ANALYSIS_PROMPT = """Сравни счёт контрагента и договор. Ответь структурированным текстом на русском языке:

1. Контрагент прислал счёт на какую сумму и от какой даты (если видно на счёте).
2. Сумма счёта соответствует или не соответствует условиям договора — объясни почему.
3. По условиям договора, в какой срок нужно оплатить этот счёт (укажи количество дней и от какой даты отсчитывается срок).
4. Рекомендуемая дата оплаты — как можно позже, но в пределах срока по договору (формат ДД.ММ.ГГГГ).
5. Другие важные условия договора, влияющие на оплату (аванс, лимит, штрафы, НДС и т.п.).

Важно: для управляющей компании ЗПИФ приоритет — оплатить счёт как можно позже, но не позже срока по договору.
Если данных недостаточно — явно укажи, чего не хватает.
Не используй markdown-заголовки — только нумерованный список или короткие абзацы."""

_MAX_RECOGNITION_ATTEMPTS = 3

@dataclass(frozen=True)
class _RecognitionProfile:
    max_pages: int
    dpi_scale: float
    max_dimension: int
    num_ctx: int | None = None


# Прогрессивное уменьшение картинок и рост контекста: vision-токены быстро
# заполняют num_ctx, из-за чего модель успевает вернуть только «{».
_RECOGNITION_PROFILES: tuple[_RecognitionProfile, ...] = (
    _RecognitionProfile(max_pages=1, dpi_scale=1.5, max_dimension=1280),
    _RecognitionProfile(max_pages=1, dpi_scale=1.2, max_dimension=1024, num_ctx=4096),
    _RecognitionProfile(max_pages=1, dpi_scale=1.0, max_dimension=896, num_ctx=8192),
)

_STRING_FIELD_ORDER = [
    "document_type",
    "counterparty_name",
    "counterparty_inn",
    "fund_name",
    "fund_inn",
    "zpif_name",
    "description",
]

_LAST_RESPONSE_PATH = settings.data_dir / "ollama_last_response.txt"
_LAST_CONTRACT_ANALYSIS_PATH = settings.data_dir / "ollama_last_contract_analysis.txt"


@dataclass
class ExtractedFields:
    document_type: str | None = None
    counterparty_name: str = ""
    counterparty_inn: str = ""
    fund_name: str = ""
    fund_inn: str = ""
    zpif_name: str = ""
    amount: float | None = None
    period_from: date | None = None
    period_to: date | None = None
    description: str = ""


class RecognitionParseError(ValueError):
    def __init__(self, message: str, *, raw_response: str, log_path: Path) -> None:
        super().__init__(message)
        self.raw_response = raw_response
        self.log_path = log_path


def _client() -> Client:
    return Client(host=settings.ollama_host)


def pdf_pages_to_base64(
    pdf_path: Path,
    *,
    max_pages: int = 1,
    dpi_scale: float = 1.5,
    max_dimension: int = 1280,
) -> list[str]:
    """Рендерит первые страницы PDF в PNG (base64) для vision-модели."""
    doc = fitz.open(pdf_path)
    images: list[str] = []
    try:
        for page_num in range(min(doc.page_count, max_pages)):
            page = doc.load_page(page_num)
            scale = dpi_scale
            longest_side = max(page.rect.width, page.rect.height) * scale
            if longest_side > max_dimension:
                scale *= max_dimension / longest_side
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
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


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json_object(text: str) -> str | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def _is_string_closing_quote(text: str, quote_index: int) -> bool:
    index = quote_index + 1
    while index < len(text) and text[index] in " \t\n\r":
        index += 1
    return index >= len(text) or text[index] in ",}:]"


def _repair_unescaped_quotes(text: str) -> str:
    result: list[str] = []
    index = 0
    in_string = False
    length = len(text)

    while index < length:
        char = text[index]
        if char == '"' and not in_string:
            in_string = True
            result.append(char)
            index += 1
            continue
        if char == '"' and in_string:
            if _is_string_closing_quote(text, index):
                in_string = False
                result.append(char)
            else:
                result.append('\\"')
            index += 1
            continue
        if char == "\\" and in_string and index + 1 < length:
            result.append(char)
            result.append(text[index + 1])
            index += 2
            continue
        result.append(char)
        index += 1

    return "".join(result)


def _extract_string_field(body: str, field: str, next_fields: list[str]) -> str | None:
    match = re.search(rf'"{re.escape(field)}"\s*:\s*"', body)
    if not match:
        return None

    start = match.end()
    end = len(body)
    for next_field in next_fields:
        next_match = re.search(rf'"\s*,\s*"{re.escape(next_field)}"\s*:', body[start:])
        if next_match:
            end = min(end, start + next_match.start())

    amount_match = re.search(r'"\s*,\s*"amount"\s*:', body[start:])
    if amount_match:
        end = min(end, start + amount_match.start())

    period_match = re.search(r'"\s*,\s*"period_from"\s*:', body[start:])
    if period_match:
        end = min(end, start + period_match.start())

    closing_match = re.search(r'"\s*[\n\r]+\s*}', body[start:])
    if closing_match:
        end = min(end, start + closing_match.start())

    value = body[start:end].replace('\\"', '"').replace("\\n", "\n").strip()
    return value


def _extract_scalar_field(body: str, field: str) -> object | None:
    match = re.search(
        rf'"{re.escape(field)}"\s*:\s*(null|"[^"]*"|[\d.]+)',
        body,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    raw = match.group(1)
    if raw == "null":
        return None
    if raw.startswith('"'):
        return raw[1:-1]
    return raw


def _extract_fields_loosely(text: str) -> dict:
    body = _extract_json_object(_strip_markdown_fence(text)) or text.strip()
    result: dict = {}

    for index, field in enumerate(_STRING_FIELD_ORDER):
        value = _extract_string_field(body, field, _STRING_FIELD_ORDER[index + 1 :])
        if value is not None:
            result[field] = value

    amount_raw = _extract_scalar_field(body, "amount")
    if amount_raw is not None:
        try:
            result["amount"] = float(amount_raw)
        except (TypeError, ValueError):
            result["amount"] = None

    for field in ("period_from", "period_to"):
        value = _extract_scalar_field(body, field)
        if value is not None:
            result[field] = value

    if result:
        return result
    raise ValueError("Не удалось извлечь поля из ответа модели")


def _save_raw_response(content: str) -> Path:
    _LAST_RESPONSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _LAST_RESPONSE_PATH.write_text(content, encoding="utf-8")
    return _LAST_RESPONSE_PATH


def _response_looks_valid(text: str) -> bool:
    cleaned = _strip_markdown_fence(text).strip()
    if len(cleaned) < 20:
        return False
    if cleaned.startswith("{") and not cleaned.endswith("}"):
        return False
    return any(field in cleaned for field in (*_STRING_FIELD_ORDER, "amount"))


def _has_useful_data(data: dict) -> bool:
    if data.get("document_type") in {"invoice", "act", "utd", "turnover"}:
        return True
    if str(data.get("counterparty_name") or "").strip():
        return True
    if str(data.get("fund_name") or "").strip():
        return True
    if data.get("amount") not in (None, "", 0):
        return True
    return False


def _request_model(
    images: list[str],
    *,
    attempt: int,
    num_ctx: int | None = None,
) -> str:
    user_prompt = EXTRACTION_PROMPT
    if attempt > 0:
        user_prompt += (
            "\n\nПредыдущий ответ был неверным или обрезан. "
            "Верни полный JSON со всеми ключами из примера."
        )

    response = _client().chat(
        model=settings.ollama_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": user_prompt,
                "images": images,
            },
        ],
        format="json",
        think=False,
        options={
            "num_ctx": num_ctx or settings.ollama_num_ctx,
            "num_predict": 512,
            "temperature": 0.0 if attempt == 0 else 0.1,
        },
    )
    content = (response.message.content or "").strip()
    thinking = (response.message.thinking or "").strip()
    if _response_looks_valid(content):
        return content
    if _response_looks_valid(thinking):
        return thinking
    return content or thinking


def _parse_json_response(text: str) -> dict:
    cleaned = _strip_markdown_fence(text)
    candidates: list[str] = []
    for item in (cleaned, _extract_json_object(cleaned)):
        if item and item not in candidates:
            candidates.append(item)
            repaired = _repair_unescaped_quotes(item)
            if repaired not in candidates:
                candidates.append(repaired)

    last_error: json.JSONDecodeError | None = None
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError as exc:
            last_error = exc

    try:
        return _extract_fields_loosely(text)
    except ValueError as loose_error:
        message = "Не удалось извлечь поля из ответа модели"
        if last_error is not None:
            message += f" (строка {last_error.lineno}, символ {last_error.colno})"
        raise ValueError(message) from loose_error


def _parse_model_response(text: str) -> dict:
    try:
        data = _parse_json_response(text)
    except ValueError as exc:
        log_path = _save_raw_response(text)
        details = f"{exc} Полный ответ сохранён в: {log_path}"
        raise RecognitionParseError(details, raw_response=text, log_path=log_path) from exc
    if not _has_useful_data(data):
        log_path = _save_raw_response(text)
        details = (
            "Модель вернула JSON без полезных данных. "
            f"Полный ответ сохранён в: {log_path}"
        )
        raise RecognitionParseError(details, raw_response=text, log_path=log_path)
    return data


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
        counterparty_inn=normalize_inn(str(data.get("counterparty_inn") or "")),
        fund_name=str(data.get("fund_name") or "").strip(),
        fund_inn=normalize_inn(str(data.get("fund_inn") or "")),
        zpif_name=str(data.get("zpif_name") or "").strip(),
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

    profiles = _RECOGNITION_PROFILES[:_MAX_RECOGNITION_ATTEMPTS]
    last_error: RecognitionParseError | None = None
    last_content = ""

    for attempt, profile in enumerate(profiles):
        images = pdf_pages_to_base64(
            path,
            max_pages=profile.max_pages,
            dpi_scale=profile.dpi_scale,
            max_dimension=profile.max_dimension,
        )
        if not images:
            raise ValueError("PDF не содержит страниц")

        content = _request_model(images, attempt=attempt, num_ctx=profile.num_ctx)
        last_content = content
        if not content:
            continue
        if not _response_looks_valid(content):
            continue
        try:
            data = _parse_model_response(content)
            return _to_extracted(data)
        except RecognitionParseError as exc:
            last_error = exc
            continue

    if last_error is not None:
        raise last_error

    log_path = _save_raw_response(last_content or "(пустой ответ)")
    truncated_hint = ""
    if last_content.strip() in ("{", "{\n", "{\r\n"):
        truncated_hint = (
            " Модель вернула только «{» — скорее всего, не хватило контекста "
            f"(OLLAMA_NUM_CTX={settings.ollama_num_ctx}). "
            "Попробуйте увеличить OLLAMA_NUM_CTX до 4096 или 8192."
        )
    raise RecognitionParseError(
        "Модель не смогла распознать документ после "
        f"{len(profiles)} попыток."
        f"{truncated_hint} Заполните реквизиты вручную. "
        f"Последний ответ сохранён в: {log_path}",
        raw_response=last_content,
        log_path=log_path,
    )


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


def _save_contract_analysis_response(content: str) -> Path:
    _LAST_CONTRACT_ANALYSIS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _LAST_CONTRACT_ANALYSIS_PATH.write_text(content, encoding="utf-8")
    return _LAST_CONTRACT_ANALYSIS_PATH


def _build_contract_analysis_context(
    *,
    counterparty_name: str = "",
    counterparty_inn: str = "",
    amount: float | None = None,
    contract_number: str = "",
    contract_date: str = "",
    contract_title: str = "",
) -> str:
    lines = ["Контекст из формы Veles (может дополнять документы):"]
    if counterparty_name:
        lines.append(f"- Контрагент: {counterparty_name}")
    if counterparty_inn:
        lines.append(f"- ИНН контрагента: {counterparty_inn}")
    if amount is not None:
        lines.append(f"- Сумма в форме: {amount:,.2f} ₽".replace(",", " "))
    if contract_title or contract_number:
        contract_line = "- Договор: "
        if contract_title:
            contract_line += contract_title
        if contract_number:
            contract_line += f" № {contract_number}"
        if contract_date:
            contract_line += f" от {contract_date}"
        lines.append(contract_line)
    return "\n".join(lines)


def analyze_contract_against_invoice(
    invoice_pdf_path: Path | str,
    contract_pdf_path: Path | str,
    *,
    prompt: str | None = None,
    counterparty_name: str = "",
    counterparty_inn: str = "",
    amount: float | None = None,
    contract_number: str = "",
    contract_date: str = "",
    contract_title: str = "",
) -> str:
    """Сравнивает счёт и договор через Ollama vision-модель, возвращает текстовый анализ."""
    invoice_path = Path(invoice_pdf_path)
    contract_path = Path(contract_pdf_path)
    if not invoice_path.is_file():
        raise FileNotFoundError(f"PDF счёта не найден: {invoice_path}")
    if not contract_path.is_file():
        raise FileNotFoundError(f"PDF договора не найден: {contract_path}")

    invoice_images = pdf_pages_to_base64(
        invoice_path,
        max_pages=2,
        dpi_scale=1.2,
        max_dimension=1280,
    )
    contract_images = pdf_pages_to_base64(
        contract_path,
        max_pages=3,
        dpi_scale=1.2,
        max_dimension=1280,
    )
    if not invoice_images:
        raise ValueError("PDF счёта не содержит страниц")
    if not contract_images:
        raise ValueError("PDF договора не содержит страниц")

    context = _build_contract_analysis_context(
        counterparty_name=counterparty_name,
        counterparty_inn=counterparty_inn,
        amount=amount,
        contract_number=contract_number,
        contract_date=contract_date,
        contract_title=contract_title,
    )
    user_prompt = (prompt or DEFAULT_CONTRACT_ANALYSIS_PROMPT).strip()
    user_prompt = (
        f"{user_prompt}\n\n{context}\n\n"
        "На изображениях: сначала страницы счёта, затем страницы договора."
    )

    response = _client().chat(
        model=settings.ollama_model,
        messages=[
            {"role": "system", "content": CONTRACT_ANALYSIS_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": user_prompt,
                "images": [*invoice_images, *contract_images],
            },
        ],
        think=False,
        options={
            "num_ctx": max(settings.ollama_num_ctx, 8192),
            "num_predict": 1024,
            "temperature": 0.1,
        },
    )
    content = (response.message.content or "").strip()
    thinking = (response.message.thinking or "").strip()
    result = content or thinking
    if not result:
        log_path = _save_contract_analysis_response("(пустой ответ)")
        raise ValueError(f"Модель не вернула анализ. Ответ сохранён в: {log_path}")
    _save_contract_analysis_response(result)
    return result
