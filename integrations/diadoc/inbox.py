from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config.settings import settings
from integrations.diadoc.client import DiadocClient
from integrations.diadoc.exceptions import DiadocApiError, DiadocConfigError, DiadocError
from integrations.diadoc.sync_state import load_sync_state, save_sync_state
from models.document import Document, DocumentFields, DocumentType

# Служебные вложения Diadoc — не первичные документы.
_SKIP_ATTACHMENT_TYPES = {
    "InvoiceConfirmation",
    "InvoiceReceipt",
    "Receipt",
    "Signature",
    "SignatureRequestRejection",
    "XmlSignatureReject",
    "RevocationRequest",
    "UniversalTransferDocumentBuyerTitle",
    "UniversalCorrectionDocumentBuyerTitle",
}

_TYPE_MAP: dict[str, DocumentType] = {
    "Invoice": DocumentType.INVOICE,
    "InvoiceRevision": DocumentType.INVOICE,
    "ProformaInvoice": DocumentType.INVOICE,
    "UniversalTransferDocument": DocumentType.UTD,
    "UniversalCorrectionDocument": DocumentType.UTD,
    "AcceptanceCertificate": DocumentType.ACT,
    "XmlAcceptanceCertificate": DocumentType.ACT,
    "Act": DocumentType.ACT,
    "Torg12": DocumentType.TURNOVER,
    "XmlTorg12": DocumentType.TURNOVER,
    "Waybill": DocumentType.TURNOVER,
}


@dataclass
class DiadocFetchResult:
    documents: list[Document]
    initialized_boxes: list[str]
    skipped_existing: int
    errors: list[str]


def is_diadoc_configured() -> bool:
    return bool(settings.diadoc_access_token)


def fetch_new_documents_from_diadoc(
    *,
    existing_keys: set[tuple[str, str, str]] | None = None,
) -> DiadocFetchResult:
    client = DiadocClient()
    known = existing_keys or set()
    box_ids = client.list_box_ids()
    if not box_ids:
        raise DiadocConfigError(
            "Не найдены ящики Diadoc. Задайте DIADOC_BOX_IDS в .env "
            "или проверьте доступ токена к GetMyOrganizations."
        )

    sync_state = load_sync_state()
    documents: list[Document] = []
    initialized_boxes: list[str] = []
    skipped_existing = 0
    errors: list[str] = []

    for box_id in box_ids:
        try:
            box_result = _sync_box(
                client,
                box_id,
                after_index_key=sync_state.get(box_id),
                known=known,
            )
        except DiadocApiError as exc:
            errors.append(f"Ящик {box_id}: {exc}")
            continue

        documents.extend(box_result.documents)
        skipped_existing += box_result.skipped_existing
        if box_result.initialized:
            initialized_boxes.append(box_id)
        if box_result.last_index_key:
            sync_state[box_id] = box_result.last_index_key

    save_sync_state(sync_state)
    return DiadocFetchResult(
        documents=documents,
        initialized_boxes=initialized_boxes,
        skipped_existing=skipped_existing,
        errors=errors,
    )


@dataclass
class _BoxSyncResult:
    documents: list[Document]
    last_index_key: str | None
    initialized: bool
    skipped_existing: int


def _sync_box(
    client: DiadocClient,
    box_id: str,
    *,
    after_index_key: str | None,
    known: set[tuple[str, str, str]],
) -> _BoxSyncResult:
    if not after_index_key:
        last_index_key = _bootstrap_cursor(client, box_id)
        return _BoxSyncResult(
            documents=[],
            last_index_key=last_index_key,
            initialized=True,
            skipped_existing=0,
        )

    documents: list[Document] = []
    skipped_existing = 0
    cursor = after_index_key
    last_index_key = after_index_key

    while True:
        events_data = client.get_new_events(box_id, after_index_key=cursor)
        events = events_data.get("Events", [])
        if not events:
            break

        for event in events:
            refs = _extract_inbound_documents(event)
            for ref in refs:
                key = (box_id, ref.message_id, ref.entity_id)
                if key in known:
                    skipped_existing += 1
                    continue
                try:
                    doc = _download_document(client, box_id, ref)
                except DiadocError as exc:
                    raise DiadocApiError(
                        f"документ {ref.message_id}/{ref.entity_id}: {exc}"
                    ) from exc
                documents.append(doc)
                known.add(key)

            index_key = event.get("IndexKey")
            if index_key:
                last_index_key = str(index_key)

        if len(events) < 100:
            break
        cursor = last_index_key

    return _BoxSyncResult(
        documents=documents,
        last_index_key=last_index_key,
        initialized=False,
        skipped_existing=skipped_existing,
    )


def _bootstrap_cursor(client: DiadocClient, box_id: str) -> str | None:
    """Пропускает историю ящика и сохраняет курсор для следующих вызовов."""
    cursor: str | None = None
    last_index_key: str | None = None
    max_pages = 50

    for _ in range(max_pages):
        events_data = client.get_new_events(box_id, after_index_key=cursor)
        events = events_data.get("Events", [])
        if not events:
            break
        for event in events:
            index_key = event.get("IndexKey")
            if index_key:
                last_index_key = str(index_key)
        if len(events) < 100:
            break
        cursor = last_index_key

    return last_index_key


@dataclass
class _DocumentRef:
    message_id: str
    entity_id: str
    attachment_type: str
    file_name: str
    document_info: dict[str, Any]
    sender_title: str


def _extract_inbound_documents(event: dict[str, Any]) -> list[_DocumentRef]:
    refs: list[_DocumentRef] = []
    message = event.get("Message")
    if message:
        refs.extend(
            _attachments_from_entities(
                message.get("Entities", []),
                message_id=str(message.get("MessageId", "")),
                sender_title=str(message.get("FromTitle", "")),
            )
        )

    patch = event.get("Patch")
    if patch:
        refs.extend(
            _attachments_from_entities(
                patch.get("Entities", []),
                message_id=str(patch.get("MessageId", "")),
                sender_title="",
            )
        )
    return refs


def _attachments_from_entities(
    entities: list[dict[str, Any]],
    *,
    message_id: str,
    sender_title: str,
) -> list[_DocumentRef]:
    refs: list[_DocumentRef] = []
    for entity in entities:
        if entity.get("EntityType") != "Attachment":
            continue

        attachment_type = str(entity.get("AttachmentType") or "")
        if attachment_type in _SKIP_ATTACHMENT_TYPES:
            continue

        content_size = entity.get("Content", {}).get("Size", 0)
        if not content_size or content_size <= 0:
            continue

        document_info = entity.get("DocumentInfo") or {}
        direction = str(document_info.get("DocumentDirection") or "")
        if direction and direction != "Inbound":
            continue

        entity_id = str(entity.get("EntityId") or document_info.get("EntityId") or "")
        if not message_id or not entity_id:
            continue

        refs.append(
            _DocumentRef(
                message_id=message_id,
                entity_id=entity_id,
                attachment_type=attachment_type,
                file_name=str(entity.get("FileName") or document_info.get("FileName") or ""),
                document_info=document_info,
                sender_title=sender_title,
            )
        )
    return refs


def _download_document(client: DiadocClient, box_id: str, ref: _DocumentRef) -> Document:
    metadata = ref.document_info
    if not metadata:
        metadata = client.get_document(box_id, ref.message_id, ref.entity_id)

    pdf_path = _save_document_file(client, box_id, ref, metadata)
    fields = _build_fields(ref, metadata)

    return Document(
        document_type=_map_document_type(ref.attachment_type, metadata),
        fields=fields,
        diadoc_box_id=box_id,
        diadoc_message_id=ref.message_id,
        diadoc_entity_id=ref.entity_id,
        pdf_filename=str(pdf_path),
    )


def _save_document_file(
    client: DiadocClient,
    box_id: str,
    ref: _DocumentRef,
    metadata: dict[str, Any],
) -> Path:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{ref.message_id}_{ref.entity_id}.pdf"
    target = settings.data_dir / safe_name

    content = client.get_entity_content(box_id, ref.message_id, ref.entity_id)
    if _is_pdf(content):
        target.write_bytes(content)
        return target

    try:
        pdf_bytes = client.generate_print_form(box_id, ref.message_id, ref.entity_id)
        if _is_pdf(pdf_bytes):
            target.write_bytes(pdf_bytes)
            return target
    except DiadocApiError:
        pass

    extension = Path(ref.file_name).suffix.lower() or ".bin"
    fallback = settings.data_dir / f"{ref.message_id}_{ref.entity_id}{extension}"
    fallback.write_bytes(content)
    return fallback


def _is_pdf(content: bytes) -> bool:
    return content.startswith(b"%PDF")


def _build_fields(ref: _DocumentRef, metadata: dict[str, Any]) -> DocumentFields:
    counterparty_name = ref.sender_title or str(metadata.get("CounteragentBoxId") or "")
    amount = _extract_amount(metadata)
    description = str(metadata.get("Title") or ref.file_name or "Документ Diadoc")

    return DocumentFields(
        counterparty_name=counterparty_name,
        amount=amount,
        description=description,
    )


def _extract_amount(metadata: dict[str, Any]) -> float | None:
    utd_meta = metadata.get("UniversalTransferDocumentMetadata") or {}
    total = utd_meta.get("Total")
    if total is not None:
        try:
            return float(str(total).replace(",", ".").replace(" ", ""))
        except ValueError:
            pass

    for item in metadata.get("Metadata", []):
        if item.get("Key") == "TotalSum" and item.get("Value"):
            try:
                return float(str(item["Value"]).replace(",", ".").replace(" ", ""))
            except ValueError:
                return None
    return None


def _map_document_type(attachment_type: str, metadata: dict[str, Any]) -> DocumentType | None:
    type_named_id = str(metadata.get("TypeNamedId") or attachment_type)
    return _TYPE_MAP.get(type_named_id)
