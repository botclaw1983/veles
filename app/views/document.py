from datetime import date

import streamlit as st

from models.document import Document, DocumentStatus, DocumentType


def _get_selected_document() -> Document | None:
    doc_id = st.session_state.get("selected_document_id")
    if not doc_id:
        return None
    for doc in st.session_state.get("documents", []):
        if doc.id == doc_id:
            return doc
    return None


def render() -> None:
    doc = _get_selected_document()

    if doc is None:
        st.title("Документ")
        st.warning("Выберите документ на странице «Входящие».")
        st.caption("Используйте боковое меню для перехода.")
        return

    st.title("Обработка документа")
    st.caption(f"ID: `{doc.id}` · Статус: **{doc.status.label}**")

    col_pdf, col_form = st.columns([1, 1])

    with col_pdf:
        st.subheader("Документ")
        if doc.pdf_filename:
            st.pdf(doc.pdf_filename)
        else:
            st.info("PDF будет загружен из Diadoc.")

    with col_form:
        st.subheader("Реквизиты")

        type_options = {t.label: t for t in DocumentType}
        type_values = list(type_options.values())
        default_index = (
            type_values.index(doc.document_type) if doc.document_type in type_values else 0
        )
        selected_type = st.selectbox(
            "Тип документа",
            options=list(type_options.keys()),
            index=default_index,
        )
        doc.document_type = type_options[selected_type]

        doc.fields.fund_name = st.text_input("Юр. лицо (фонд)", value=doc.fields.fund_name)
        doc.fields.fund_inn = st.text_input("ИНН фонда", value=doc.fields.fund_inn)
        doc.fields.counterparty_name = st.text_input(
            "Контрагент", value=doc.fields.counterparty_name
        )
        doc.fields.counterparty_inn = st.text_input(
            "ИНН контрагента", value=doc.fields.counterparty_inn
        )
        doc.fields.amount = st.number_input(
            "Сумма",
            min_value=0.0,
            value=float(doc.fields.amount or 0.0),
            step=0.01,
        )

        period_col1, period_col2 = st.columns(2)
        with period_col1:
            doc.fields.period_from = st.date_input(
                "Период с",
                value=doc.fields.period_from or date.today(),
            )
        with period_col2:
            doc.fields.period_to = st.date_input(
                "Период по",
                value=doc.fields.period_to or date.today(),
            )

        doc.fields.description = st.text_area("Назначение / комментарий", value=doc.fields.description)

        btn1, btn2, btn3 = st.columns(3)
        with btn1:
            if st.button("Сохранить черновик", use_container_width=True):
                doc.touch()
                st.success("Сохранено")
        with btn2:
            if st.button("Согласовать", type="primary", use_container_width=True):
                doc.status = DocumentStatus.ON_APPROVAL
                doc.touch()
                st.info("Согласование будет реализовано на этапе 4.")
        with btn3:
            if st.button("В Аванкор", use_container_width=True, disabled=doc.status != DocumentStatus.APPROVED):
                st.info("Интеграция с Аванкор — этап 5.")
