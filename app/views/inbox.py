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
from app.services.document_store import add_documents, list_documents
from models.document import BankClientStatus, Document, DocumentStatus


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
    else:
        label = "Не согласован"
        background, border, color = "#fee2e2", "#dc2626", "#991b1b"

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


def render() -> None:
    _inject_table_styles()
    st.title("Документы")

    source_parts = [f"локальная папка `{settings.pdf_docs_dir}`"]
    if is_diadoc_configured():
        source_parts.append(f"Diadoc `{settings.diadoc_api_url}`")
    st.caption("Источники: " + ", ".join(source_parts))

    col1, col2, col3 = st.columns([1.2, 1.4, 2.4])
    with col1:
        if st.button("Получить документы", type="primary", use_container_width=True):
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
                        st.info("Новых документов нет — все PDF из папки уже загружены.")

    with col2:
        diadoc_disabled = not is_diadoc_configured()
        if st.button(
            "Получить новые документы из Diadoc",
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
                "Для загрузки из Diadoc задайте `DIADOC_ACCESS_TOKEN` в `.env`. "
                "Инструкция: `INTEGRATION_DIADOC.md`."
            )

    documents = list_documents()

    if not documents:
        st.markdown("---")
        st.markdown(
            f"Положите PDF-файлы в папку **`pdf_docs`** или настройте Diadoc и нажмите "
            f"«Получить новые документы из Diadoc».\n\n"
            f"Путь pdf_docs: `{settings.pdf_docs_dir}`"
        )
        return

    st.markdown("---")
    header = st.columns([2.0, 1.3, 1.4, 1.3, 1.0, 1.0, 1.0])
    header[0].markdown("**Файл**")
    header[1].markdown("**Согласование**")
    header[2].markdown("**Отправлено в Аванкор**")
    header[3].markdown("**Банк-клиент**")
    header[4].markdown("**Тип**")
    header[5].markdown("**Сумма**")
    header[6].markdown("**Действие**")

    for doc in documents:
        cols = st.columns([2.0, 1.3, 1.4, 1.3, 1.0, 1.0, 1.0])
        filename = Path(doc.pdf_filename).name if doc.pdf_filename else "—"
        if doc.diadoc_message_id:
            filename = f"{filename} · Diadoc"
        cols[0].write(filename)
        cols[1].markdown(_approval_badge(doc.status), unsafe_allow_html=True)
        cols[2].markdown(_avankor_badge(doc.status), unsafe_allow_html=True)
        cols[3].markdown(_bank_client_badge(doc.bank_client_status), unsafe_allow_html=True)
        cols[4].write(doc.document_type.label if doc.document_type else "—")
        cols[5].write(f"{doc.fields.amount:,.2f}" if doc.fields.amount else "—")
        if cols[6].button("Обработать", key=f"process_{doc.id}", use_container_width=True):
            _open_document(doc.id)
