from pathlib import Path

import streamlit as st

from config.settings import settings
from integrations.local_pdf import fetch_documents_from_pdf_docs
from models.document import Document


def _existing_pdf_paths(documents: list[Document]) -> set[str]:
    return {doc.pdf_filename for doc in documents if doc.pdf_filename}


def _open_document(doc_id: str) -> None:
    st.session_state.selected_document_id = doc_id
    st.switch_page(st.session_state["nav_document_page"])


def render() -> None:
    st.title("Входящие документы")
    st.caption(f"Источник: `{settings.pdf_docs_dir}`")

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Получить документы", type="primary", use_container_width=True):
            with st.spinner("Сканирование pdf_docs…"):
                documents: list[Document] = st.session_state.get("documents", [])
                new_docs = fetch_documents_from_pdf_docs(
                    existing_paths=_existing_pdf_paths(documents),
                )
                if new_docs:
                    st.session_state.documents.extend(new_docs)
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

    documents = st.session_state.get("documents", [])

    if not documents:
        st.markdown("---")
        st.markdown(
            f"Положите PDF-файлы в папку **`pdf_docs`** и нажмите «Получить документы».\n\n"
            f"Путь: `{settings.pdf_docs_dir}`"
        )
        return

    st.markdown("---")
    header = st.columns([3, 2, 2, 2, 1.2])
    header[0].markdown("**Файл**")
    header[1].markdown("**Согласование**")
    header[2].markdown("**Тип**")
    header[3].markdown("**Сумма**")
    header[4].markdown("**Действие**")

    for doc in documents:
        cols = st.columns([3, 2, 2, 2, 1.2])
        filename = Path(doc.pdf_filename).name if doc.pdf_filename else "—"
        cols[0].write(filename)
        cols[1].write(doc.status.approval_label)
        cols[2].write(doc.document_type.label if doc.document_type else "—")
        cols[3].write(f"{doc.fields.amount:,.2f}" if doc.fields.amount else "—")
        if cols[4].button("Обработать", key=f"process_{doc.id}", use_container_width=True):
            _open_document(doc.id)
