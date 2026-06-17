from datetime import date
from pathlib import Path

import streamlit as st

from app.components.approval_status import render_approval_status
from app.components.pdf_viewer import render_pdf
from app.services.document_store import get_document, save_document
from app.services.reference_store import get_approvers, get_document_types, get_funds, resolve_document_type
from integrations.ollama_recognition import ExtractedFields, check_ollama_available, extract_fields_from_pdf
from models.document import Document, DocumentStatus


def _get_selected_document() -> Document | None:
    doc_id = st.session_state.get("selected_document_id")
    if not doc_id:
        return None
    return get_document(doc_id)


def _is_fully_approved(doc: Document) -> bool:
    if hasattr(doc, "is_fully_approved"):
        return doc.is_fully_approved()
    return bool(doc.approvers) and all(a.approved for a in doc.approvers)


def _approve_approver(doc: Document, idx: int) -> None:
    if doc.status == DocumentStatus.NEW:
        doc.status = DocumentStatus.ON_APPROVAL
    if hasattr(doc, "approve_approver"):
        doc.approve_approver(idx)
    else:
        doc.approvers[idx].approved = True
        if _is_fully_approved(doc):
            doc.status = DocumentStatus.APPROVED
    save_document(doc)


def _render_approvers(doc: Document) -> None:
    doc.ensure_approvers(get_approvers())
    st.subheader("Согласование")
    render_approval_status(doc)
    st.markdown("")

    locked = doc.status == DocumentStatus.SENT_TO_AVANKOR

    for idx, approver in enumerate(doc.approvers):
        icon_col, text_col = st.columns([0.5, 5.5], vertical_alignment="center")
        with icon_col:
            if approver.approved:
                st.button(
                    " ",
                    key=f"approve_done_{doc.id}_{idx}",
                    disabled=True,
                    type="tertiary",
                    help="Согласовано",
                )
            elif locked:
                st.button(
                    " ",
                    key=f"approve_idle_{doc.id}_{idx}",
                    disabled=True,
                    type="tertiary",
                )
            elif st.button(
                " ",
                key=f"approve_pending_{doc.id}_{idx}",
                help="Согласовать",
                type="tertiary",
            ):
                _approve_approver(doc, idx)
                st.rerun()
        with text_col:
            st.markdown(f"**{approver.name}** — _{approver.role}_")


def _apply_extracted_fields(doc: Document, extracted: ExtractedFields) -> None:
    if extracted.document_type:
        resolved = resolve_document_type(extracted.document_type)
        if resolved:
            doc.document_type = resolved

    if extracted.counterparty_name:
        doc.fields.counterparty_name = extracted.counterparty_name
    if extracted.counterparty_inn:
        doc.fields.counterparty_inn = extracted.counterparty_inn
    if extracted.fund_name:
        doc.fields.fund_name = extracted.fund_name
    if extracted.fund_inn:
        doc.fields.fund_inn = extracted.fund_inn
    if extracted.amount is not None:
        doc.fields.amount = extracted.amount
    if extracted.period_from:
        doc.fields.period_from = extracted.period_from
    if extracted.period_to:
        doc.fields.period_to = extracted.period_to
    if extracted.description:
        doc.fields.description = extracted.description
    doc.touch()


def _render_recognition(doc: Document) -> None:
    if not doc.pdf_filename or not Path(doc.pdf_filename).is_file():
        return

    ok, error = check_ollama_available()
    if not ok:
        st.caption(f"Распознавание недоступно: {error}")
        return

    if st.button("Распознать PDF", use_container_width=True, key=f"recognize_{doc.id}"):
        with st.spinner("Распознавание документа..."):
            try:
                extracted = extract_fields_from_pdf(doc.pdf_filename)
                _apply_extracted_fields(doc, extracted)
                save_document(doc)
                st.success("Реквизиты заполнены. Проверьте и сохраните.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001 — показываем ошибку в UI
                st.error(f"Ошибка распознавания: {exc}")


def _render_requisites(doc: Document) -> None:
    st.subheader("Реквизиты")

    doc_types = get_document_types()
    if not doc_types:
        st.warning("Справочник типов документов пуст. Добавьте типы на странице «Справочники».")
        return

    type_labels = [item["label"] for item in doc_types]
    type_by_label = {item["label"]: item["code"] for item in doc_types}

    current_label = doc.document_type.label if doc.document_type else type_labels[0]
    if current_label not in type_labels and type_labels:
        current_label = type_labels[0]

    selected_type = st.selectbox(
        "Тип документа",
        options=type_labels,
        index=type_labels.index(current_label) if current_label in type_labels else 0,
    )
    doc.document_type = resolve_document_type(type_by_label[selected_type])

    funds = get_funds()
    fund_names = [fund["name"] for fund in funds]
    if fund_names:
        current_fund = doc.fields.fund_name if doc.fields.fund_name in fund_names else fund_names[0]
        doc.fields.fund_name = st.selectbox(
            "Юр. лицо",
            options=fund_names,
            index=fund_names.index(current_fund),
        )
    else:
        doc.fields.fund_name = st.text_input("Юр. лицо", value=doc.fields.fund_name)

    doc.fields.amount = st.number_input(
        "Сумма",
        min_value=0.0,
        value=float(doc.fields.amount or 0.0),
        step=0.01,
    )

    doc.fields.counterparty_name = st.text_input(
        "Контрагент",
        value=doc.fields.counterparty_name,
    )
    doc.fields.counterparty_inn = st.text_input(
        "ИНН контрагента",
        value=doc.fields.counterparty_inn,
    )
    doc.fields.description = st.text_area(
        "Назначение / описание",
        value=doc.fields.description,
        height=68,
    )

    st.markdown("**Период**")
    period_col1, period_col2 = st.columns(2)
    with period_col1:
        doc.fields.period_from = st.date_input(
            "С",
            value=doc.fields.period_from or date.today(),
            label_visibility="collapsed",
        )
    with period_col2:
        doc.fields.period_to = st.date_input(
            "По",
            value=doc.fields.period_to or date.today(),
            label_visibility="collapsed",
        )

    if st.button("Сохранить", use_container_width=True):
        save_document(doc)
        st.success("Сохранено")


def _inject_page_styles() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stMainBlockContainer"] {
            padding-top: 2.75rem;
        }
        div[class*="st-key-approve_done_"],
        div[class*="st-key-approve_pending_"],
        div[class*="st-key-approve_idle_"] {
            width: 100% !important;
            height: 32px !important;
            min-height: 32px !important;
            max-height: 32px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        div[class*="st-key-approve_done_"] [data-testid="stElementContainer"],
        div[class*="st-key-approve_pending_"] [data-testid="stElementContainer"],
        div[class*="st-key-approve_idle_"] [data-testid="stElementContainer"],
        div[class*="st-key-approve_done_"] [data-testid="stVerticalBlock"],
        div[class*="st-key-approve_pending_"] [data-testid="stVerticalBlock"],
        div[class*="st-key-approve_idle_"] [data-testid="stVerticalBlock"] {
            padding: 0 !important;
            margin: 0 !important;
            gap: 0 !important;
            width: 100% !important;
            height: 32px !important;
            min-height: 32px !important;
            justify-content: center !important;
            align-items: center !important;
        }
        div[class*="st-key-approve_done_"] button,
        div[class*="st-key-approve_pending_"] button,
        div[class*="st-key-approve_idle_"] button {
            width: 20px !important;
            height: 20px !important;
            min-width: 20px !important;
            min-height: 20px !important;
            max-width: 20px !important;
            max-height: 20px !important;
            border-radius: 50% !important;
            padding: 0 !important;
            margin: 0 !important;
            border: none !important;
            color: transparent !important;
            font-size: 0 !important;
            line-height: 0 !important;
            box-shadow: none !important;
            box-sizing: border-box !important;
            opacity: 1 !important;
        }
        div[class*="st-key-approve_done_"] button {
            background: #16a34a !important;
            cursor: default !important;
        }
        div[class*="st-key-approve_pending_"] button {
            background: #9ca3af !important;
        }
        div[class*="st-key-approve_pending_"] button:hover {
            background: #6b7280 !important;
        }
        div[class*="st-key-approve_idle_"] button {
            background: #9ca3af !important;
            cursor: default !important;
        }
        div[class*="st-key-approve_done_"] button p,
        div[class*="st-key-approve_pending_"] button p,
        div[class*="st-key-approve_idle_"] button p {
            display: none !important;
        }
        div[class*="st-key-send_approval_"] button {
            font-size: 0.78rem !important;
            min-height: 1.85rem !important;
            padding: 0.2rem 0.5rem !important;
        }
        div[class*="st-key-send_approval_"] button p {
            font-size: 0.78rem !important;
        }
        .approval-status-badge {
            padding: 0.35rem 0.5rem;
            border-radius: 0.4rem;
            text-align: center;
            font-weight: 600;
            font-size: 0.78rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_page_header(doc: Document) -> None:
    filename = Path(doc.pdf_filename).name if doc.pdf_filename else "—"
    st.subheader("Обработка")
    st.caption(filename)


def render() -> None:
    doc = _get_selected_document()
    _inject_page_styles()

    if doc is None:
        st.subheader("Обработка")
        st.warning("Выберите документ на странице «Документы» и нажмите «Обработать».")
        return

    doc.ensure_approvers(get_approvers())

    _render_page_header(doc)

    col_doc, col_side = st.columns([5, 2])

    with col_doc:
        if doc.pdf_filename and Path(doc.pdf_filename).is_file():
            render_pdf(doc.pdf_filename, height=920)
        else:
            st.info("PDF-файл не найден.")

    with col_side:
        _render_recognition(doc)
        _render_requisites(doc)

        st.markdown("---")
        _render_approvers(doc)

        all_approved = _is_fully_approved(doc)
        avankor_sent = doc.status == DocumentStatus.SENT_TO_AVANKOR
        if st.button(
            "Отправить в Аванкор",
            type="primary" if all_approved and not avankor_sent else "secondary",
            disabled=not all_approved or avankor_sent,
            use_container_width=True,
        ):
            doc.status = DocumentStatus.SENT_TO_AVANKOR
            save_document(doc)
            st.success("Документ отправлен в Аванкор (демо).")
            st.rerun()

        if avankor_sent:
            st.caption("Документ уже отправлен в Аванкор.")
