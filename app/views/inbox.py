import streamlit as st

from models.document import Document, DocumentStatus


def _fetch_from_diadoc_stub() -> list[Document]:
    """Заглушка: позже заменить на integrations/diadoc."""
    return []


def render() -> None:
    st.title("Входящие документы")

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Получить документы", type="primary", use_container_width=True):
            with st.spinner("Запрос к Diadoc…"):
                new_docs = _fetch_from_diadoc_stub()
                if new_docs:
                    st.session_state.documents.extend(new_docs)
                    st.success(f"Получено документов: {len(new_docs)}")
                else:
                    st.info(
                        "Новых документов нет. Интеграция с Diadoc будет подключена на следующем этапе."
                    )

    documents: list[Document] = st.session_state.get("documents", [])

    if not documents:
        st.markdown("---")
        st.markdown(
            "Документы из Diadoc появятся здесь после настройки API "
            "(см. [INTEGRATION_DIADOC.md](../INTEGRATION_DIADOC.md))."
        )
        return

    rows = [
        {
            "ID": doc.id[:8],
            "Статус": doc.status.label,
            "Тип": doc.document_type.label if doc.document_type else "—",
            "Контрагент": doc.fields.counterparty_name or "—",
            "Сумма": doc.fields.amount,
            "Получен": doc.received_at.strftime("%d.%m.%Y %H:%M"),
        }
        for doc in documents
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.subheader("Открыть документ")
    options = {
        f"{d.id[:8]} — {d.fields.counterparty_name or 'без названия'}": d.id
        for d in documents
    }
    choice = st.selectbox("Документ", options=list(options.keys()))
    if st.button("Открыть"):
        st.session_state.selected_document_id = options[choice]
        st.success("Документ выбран. Откройте раздел «Документ» в меню слева.")
