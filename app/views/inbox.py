from pathlib import Path

import streamlit as st

from config.settings import settings
from integrations.diadoc import (
    DiadocConfigError,
    DiadocError,
    fetch_new_documents_from_diadoc,
    is_diadoc_configured,
)
from integrations.local_pdf import fetch_documents_from_pdf_docs
from app.services.document_store import add_documents, list_documents, save_document
from models.document import BankClientStatus, Document, DocumentStatus, SpecDepStatus

_SORTABLE_COLUMNS: list[tuple[str, str]] = [
    ("filename", "Файл"),
    ("zpif", "ЗПИФ"),
    ("counterparty", "Контрагент"),
    ("document_type", "Тип"),
    ("amount", "Сумма"),
    ("payment_date", "Дата оплаты"),
    ("approval", "Согласование"),
    ("avankor", "Аванкор"),
    ("spec_dep", "Спец.Деп"),
    ("bank_client", "Банк-клиент"),
]

_APPROVAL_SORT_ORDER = {
    DocumentStatus.NEW: 0,
    DocumentStatus.ON_APPROVAL: 1,
    DocumentStatus.REJECTED: 2,
    DocumentStatus.APPROVED: 3,
    DocumentStatus.SENT_TO_AVANKOR: 4,
}

_BANK_CLIENT_SORT_ORDER = {
    BankClientStatus.NOT_UPLOADED: 0,
    BankClientStatus.UPLOADED: 1,
    BankClientStatus.PAID: 2,
}


def _doc_filename(doc: Document) -> str:
    if not doc.pdf_filename:
        return ""
    return Path(doc.pdf_filename).name.lower()


def _doc_zpif(doc: Document) -> str:
    return (doc.fields.zpif_name or doc.fields.fund_name or "").lower()


def _sort_key(doc: Document, field: str):
    if field == "received_at":
        return doc.received_at
    if field == "filename":
        return _doc_filename(doc)
    if field == "zpif":
        return _doc_zpif(doc)
    if field == "counterparty":
        return (doc.fields.counterparty_name or "").lower()
    if field == "document_type":
        return doc.document_type.label if doc.document_type else ""
    if field == "amount":
        amount = doc.fields.amount
        return (amount is None, amount if amount is not None else 0.0)
    if field == "payment_date":
        payment_date = doc.fields.payment_date
        return (payment_date is None, payment_date)
    if field == "approval":
        return _APPROVAL_SORT_ORDER.get(doc.status, 99)
    if field == "avankor":
        return 1 if doc.status == DocumentStatus.SENT_TO_AVANKOR else 0
    if field == "spec_dep":
        return 1 if doc.spec_dep_status == SpecDepStatus.SENT else 0
    if field == "bank_client":
        return _BANK_CLIENT_SORT_ORDER.get(doc.bank_client_status, 0)
    return ""


def _sort_documents(
    documents: list[Document],
    *,
    sort_by: str,
    ascending: bool,
) -> list[Document]:
    return sorted(documents, key=lambda doc: _sort_key(doc, sort_by), reverse=not ascending)


def _init_inbox_sort() -> None:
    if "inbox_sort_by" not in st.session_state:
        st.session_state.inbox_sort_by = "received_at"
    if "inbox_sort_asc" not in st.session_state:
        st.session_state.inbox_sort_asc = False


def _handle_sort_click(field: str) -> None:
    if st.session_state.inbox_sort_by == field:
        st.session_state.inbox_sort_asc = not st.session_state.inbox_sort_asc
    else:
        st.session_state.inbox_sort_by = field
        st.session_state.inbox_sort_asc = True
    st.rerun()


def _sort_header_label(field: str, label: str) -> str:
    if st.session_state.inbox_sort_by != field:
        return label
    return f"{label} {'↑' if st.session_state.inbox_sort_asc else '↓'}"


def _render_sortable_header(col, field: str, label: str) -> None:
    if col.button(
        _sort_header_label(field, label),
        key=f"sort_{field}",
        type="tertiary",
        use_container_width=True,
    ):
        _handle_sort_click(field)


def _existing_pdf_paths(documents: list[Document]) -> set[str]:
    return {doc.pdf_filename for doc in documents if doc.pdf_filename}


def _existing_diadoc_keys(documents: list[Document]) -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    for doc in documents:
        if doc.diadoc_box_id and doc.diadoc_message_id and doc.diadoc_entity_id:
            keys.add((doc.diadoc_box_id, doc.diadoc_message_id, doc.diadoc_entity_id))
    return keys


def _open_document(doc_id: str) -> None:
    st.session_state.selected_document_id = doc_id
    st.switch_page(st.session_state["nav_document_page"])


def _inject_table_styles() -> None:
    st.markdown(
        """
        <style>
        .doc-table-badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 0.4rem;
            font-weight: 600;
            font-size: 0.75rem;
            white-space: nowrap;
        }
        div[class*="st-key-spec_dep_"],
        div[class*="st-key-process_"] {
            width: fit-content !important;
            max-width: 100% !important;
        }
        div[class*="st-key-spec_dep_"] [data-testid="stElementContainer"],
        div[class*="st-key-process_"] [data-testid="stElementContainer"],
        div[class*="st-key-spec_dep_"] [data-testid="stVerticalBlock"],
        div[class*="st-key-process_"] [data-testid="stVerticalBlock"] {
            width: fit-content !important;
            max-width: 100% !important;
        }
        div[class*="st-key-spec_dep_"] button,
        div[class*="st-key-process_"] button {
            font-size: 0.75rem !important;
            font-weight: 600 !important;
            padding: 0.25rem 0.5rem !important;
            min-height: 0 !important;
            height: auto !important;
            line-height: 1.2 !important;
            white-space: nowrap !important;
            border-radius: 0.4rem !important;
            width: auto !important;
        }
        div[class*="st-key-spec_dep_"] button p,
        div[class*="st-key-process_"] button p {
            font-size: 0.75rem !important;
            font-weight: 600 !important;
            white-space: nowrap !important;
            line-height: 1.2 !important;
        }
        div[class*="st-key-sort_"] {
            width: 100% !important;
        }
        div[class*="st-key-sort_"] [data-testid="stElementContainer"],
        div[class*="st-key-sort_"] [data-testid="stVerticalBlock"] {
            width: 100% !important;
        }
        div[class*="st-key-sort_"] button {
            font-size: 0.875rem !important;
            font-weight: 700 !important;
            padding: 0 !important;
            min-height: 0 !important;
            height: auto !important;
            line-height: 1.2 !important;
            white-space: nowrap !important;
            border: none !important;
            box-shadow: none !important;
            background: transparent !important;
            color: inherit !important;
            justify-content: flex-start !important;
            text-align: left !important;
        }
        div[class*="st-key-sort_"] button:hover {
            color: #2563eb !important;
            background: transparent !important;
        }
        div[class*="st-key-sort_"] button p {
            font-size: 0.875rem !important;
            font-weight: 700 !important;
            white-space: nowrap !important;
            line-height: 1.2 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _approval_badge(status: DocumentStatus) -> str:
    if status in (DocumentStatus.APPROVED, DocumentStatus.SENT_TO_AVANKOR):
        label = "Согласован"
        background, border, color = "#dcfce7", "#16a34a", "#166534"
    elif status == DocumentStatus.ON_APPROVAL:
        label = "На согласовании"
        background, border, color = "#f3f4f6", "#d1d5db", "#6b7280"
    elif status == DocumentStatus.REJECTED:
        label = "Отклонён"
        background, border, color = "#fee2e2", "#dc2626", "#991b1b"
    else:
        label = "Не обработан"
        background, border, color = "#f3f4f6", "#d1d5db", "#6b7280"

    return (
        f'<span class="doc-table-badge" style="background:{background};'
        f'border:1px solid {border};color:{color};">{label}</span>'
    )


def _bank_client_badge(status: BankClientStatus) -> str:
    if status == BankClientStatus.UPLOADED:
        label = "Загружено"
        background, border, color = "#ecfdf5", "#6ee7b7", "#047857"
    elif status == BankClientStatus.PAID:
        label = "Оплачено"
        background, border, color = "#dcfce7", "#16a34a", "#166534"
    else:
        return "—"

    return (
        f'<span class="doc-table-badge" style="background:{background};'
        f'border:1px solid {border};color:{color};">{label}</span>'
    )


def _avankor_badge(status: DocumentStatus) -> str:
    if status == DocumentStatus.SENT_TO_AVANKOR:
        label = "Отправлено"
        background, border, color = "#dbeafe", "#1e40af", "#1e40af"
    else:
        return "—"

    return (
        f'<span class="doc-table-badge" style="background:{background};'
        f'border:1px solid {border};color:{color};">{label}</span>'
    )


def _spec_dep_sent_badge() -> str:
    return (
        '<span class="doc-table-badge" style="background:#dbeafe;'
        'border:1px solid #1e40af;color:#1e40af;">Отправлено</span>'
    )


def _render_spec_dep_cell(col, doc: Document) -> None:
    if doc.spec_dep_status == SpecDepStatus.SENT:
        col.markdown(_spec_dep_sent_badge(), unsafe_allow_html=True)
    elif col.button("Отправить", key=f"spec_dep_{doc.id}"):
        doc.spec_dep_status = SpecDepStatus.SENT
        save_document(doc)
        st.rerun()


def _format_payment_date(value) -> str:
    if value is None:
        return "—"
    return value.strftime("%d.%m.%Y")


def render() -> None:
    _inject_table_styles()
    st.title("Документы")

    col1, col2, col3 = st.columns([1.2, 1.4, 2.4])
    with col1:
        if st.button("Загрузить из папки", type="primary", use_container_width=True):
            with st.spinner("Сканирование pdf_docs…"):
                documents = list_documents()
                new_docs = fetch_documents_from_pdf_docs(
                    existing_paths=_existing_pdf_paths(documents),
                )
                if new_docs:
                    add_documents(new_docs)
                    st.success(f"Получено документов: {len(new_docs)}")
                else:
                    pdf_count = len(list(settings.pdf_docs_dir.glob("*.pdf")))
                    if pdf_count == 0:
                        st.warning(
                            f"В папке pdf_docs нет PDF-файлов. "
                            f"Положите документы в: {settings.pdf_docs_dir}"
                        )
                    else:
                        st.info("Новых документов в папке нет")

    with col2:
        diadoc_disabled = not is_diadoc_configured()
        if st.button(
            "Загрузить из Diadoc",
            type="secondary",
            use_container_width=True,
            disabled=diadoc_disabled,
            help="Требуется DIADOC_ACCESS_TOKEN в .env",
        ):
            with st.spinner("Запрос новых документов из Diadoc…"):
                documents = list_documents()
                try:
                    result = fetch_new_documents_from_diadoc(
                        existing_keys=_existing_diadoc_keys(documents),
                    )
                except DiadocConfigError as exc:
                    st.error(str(exc))
                except DiadocError as exc:
                    st.error(f"Ошибка Diadoc: {exc}")
                else:
                    if result.initialized_boxes:
                        st.info(
                            "Первичная синхронизация с Diadoc выполнена для ящиков: "
                            + ", ".join(result.initialized_boxes)
                            + ". Нажмите кнопку ещё раз, чтобы загружать только новые документы."
                        )
                    if result.documents:
                        add_documents(result.documents)
                        st.success(f"Получено из Diadoc: {len(result.documents)}")
                    elif not result.initialized_boxes:
                        st.info("Новых документов в Diadoc нет.")
                    if result.skipped_existing:
                        st.caption(f"Пропущено уже загруженных: {result.skipped_existing}")
                    for error in result.errors:
                        st.warning(error)

    if diadoc_disabled:
        with col3:
            st.caption(
                "Для загрузки из Diadoc задайте `DIADOC_ACCESS_TOKEN` в `.env`."
            )

    documents = list_documents()

    if not documents:
        st.markdown("---")
        st.markdown(
            f"Положите PDF-файлы в папку **`pdf_docs`** или настройте Diadoc и нажмите "
            f"«Загрузить из Diadoc».\n\n"
            f"Путь pdf_docs: `{settings.pdf_docs_dir}`"
        )
        return

    st.markdown("---")
    _init_inbox_sort()
    documents = _sort_documents(
        documents,
        sort_by=st.session_state.inbox_sort_by,
        ascending=st.session_state.inbox_sort_asc,
    )

    column_weights = [1.6, 1.1, 1.2, 0.7, 0.8, 0.9, 1.0, 0.9, 0.9, 0.9, 0.8]
    header = st.columns(column_weights)
    for index, (field, label) in enumerate(_SORTABLE_COLUMNS):
        _render_sortable_header(header[index], field, label)
    header[10].markdown("**Действие**")

    for doc in documents:
        cols = st.columns(column_weights)
        filename = Path(doc.pdf_filename).name if doc.pdf_filename else "—"
        if doc.diadoc_message_id:
            filename = f"{filename} · Diadoc"
        cols[0].write(filename)
        cols[1].write(doc.fields.zpif_name or doc.fields.fund_name or "—")
        cols[2].write(doc.fields.counterparty_name or "—")
        cols[3].write(doc.document_type.label if doc.document_type else "—")
        cols[4].write(f"{doc.fields.amount:,.2f}" if doc.fields.amount else "—")
        cols[5].write(_format_payment_date(doc.fields.payment_date))
        cols[6].markdown(_approval_badge(doc.status), unsafe_allow_html=True)
        cols[7].markdown(_avankor_badge(doc.status), unsafe_allow_html=True)
        _render_spec_dep_cell(cols[8], doc)
        cols[9].markdown(_bank_client_badge(doc.bank_client_status), unsafe_allow_html=True)
        if cols[10].button("Обработать", key=f"process_{doc.id}"):
            _open_document(doc.id)
