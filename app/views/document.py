import calendar
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

from app.components.approval_status import render_approval_status, send_document_to_approval
from app.components.pdf_viewer import render_pdf
from app.services.document_store import get_document, save_document
from app.services.reference_store import (
    get_counterparties,
    get_counterparty,
    get_counterparty_names,
    get_document_types,
    get_extra_approvers,
    get_funds,
    get_primary_approvers,
    get_zpif,
    get_zpif_names,
    resolve_document_type,
)
from config.reference_data import EXTRA_APPROVER_COUNT, MAIN_APPROVER_COUNT
from integrations.ollama_recognition import ExtractedFields, check_ollama_available, extract_fields_from_pdf
from models.document import Document, DocumentStatus, SpecDepStatus


def _get_selected_document() -> Document | None:
    doc_id = st.session_state.get("selected_document_id")
    if not doc_id:
        return None
    return get_document(doc_id)


def _is_fully_approved(doc: Document) -> bool:
    if hasattr(doc, "is_fully_approved"):
        return doc.is_fully_approved()
    return bool(doc.approvers) and all(a.approved for a in doc.approvers)


def _ensure_document_approvers(doc: Document) -> None:
    doc.ensure_approvers(
        get_primary_approvers(),
        extra_defaults=get_extra_approvers(),
    )


def _toggle_approver(doc: Document, idx: int, *, is_extra: bool = False) -> None:
    approvers = doc.extra_approvers if is_extra else doc.approvers
    if idx < 0 or idx >= len(approvers):
        return

    if approvers[idx].approved:
        approvers[idx].approved = False
        if doc.status == DocumentStatus.APPROVED:
            doc.status = DocumentStatus.ON_APPROVAL
    else:
        if doc.status == DocumentStatus.NEW:
            doc.status = DocumentStatus.ON_APPROVAL
        approvers[idx].approved = True
        if _is_fully_approved(doc):
            doc.status = DocumentStatus.APPROVED

    save_document(doc)


def _render_approver_row(
    doc: Document,
    *,
    approver,
    idx: int,
    key_prefix: str,
    locked: bool,
    is_extra: bool = False,
) -> None:
    icon_col, text_col = st.columns([0.5, 5.5], vertical_alignment="center")
    with icon_col:
        if locked:
            key_suffix = "done" if approver.approved else "idle"
            st.button(
                " ",
                key=f"{key_prefix}_{key_suffix}_{doc.id}_{idx}",
                disabled=True,
                type="tertiary",
            )
        elif approver.approved:
            if st.button(
                " ",
                key=f"{key_prefix}_done_{doc.id}_{idx}",
                type="tertiary",
            ):
                _toggle_approver(doc, idx, is_extra=is_extra)
                st.rerun()
        elif st.button(
            " ",
            key=f"{key_prefix}_pending_{doc.id}_{idx}",
            type="tertiary",
        ):
            _toggle_approver(doc, idx, is_extra=is_extra)
            st.rerun()
    with text_col:
        st.markdown(f"**{approver.name}** — _{approver.role}_")


def _render_approvers(doc: Document) -> None:
    _ensure_document_approvers(doc)

    real_estate = st.toggle(
        "Недвижимость",
        value=doc.real_estate_enabled,
        key=f"real_estate_{doc.id}",
        help="Включите для счетов по объектам недвижимости — потребуется доп. согласование сотрудниками ТЦ",
    )
    if real_estate != doc.real_estate_enabled:
        doc.real_estate_enabled = real_estate
        save_document(doc)
        st.rerun()

    st.subheader("Согласование")
    render_approval_status(doc, show_send_button=False)
    st.markdown("")

    locked = doc.status == DocumentStatus.SENT_TO_AVANKOR
    main_approvers = doc.approvers[:MAIN_APPROVER_COUNT]
    extra_approvers = doc.extra_approvers[:EXTRA_APPROVER_COUNT]

    for idx, approver in enumerate(main_approvers):
        _render_approver_row(
            doc,
            approver=approver,
            idx=idx,
            key_prefix="approve",
            locked=locked,
        )

    if extra_approvers:
        st.markdown("")
        st.markdown("**Доп. согласование**")
        for idx, approver in enumerate(extra_approvers):
            _render_approver_row(
                doc,
                approver=approver,
                idx=idx,
                key_prefix="extra_approve",
                locked=locked,
                is_extra=True,
            )


def _selectbox_with_value(
    label: str,
    *,
    options: list[str],
    current: str,
    key: str,
) -> str:
    if not options:
        return st.text_input(label, value=current, key=key)
    if current and current not in options:
        options = [current, *options]
    index = options.index(current) if current in options else 0
    return st.selectbox(label, options=options, index=index, key=key)


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
    if extracted.zpif_name:
        doc.fields.zpif_name = extracted.zpif_name
    elif extracted.fund_name:
        for zpif in get_zpif():
            if zpif["name"] in extracted.fund_name or extracted.fund_name in zpif["name"]:
                doc.fields.zpif_name = zpif["name"]
                break

    for item in get_counterparties():
        if doc.fields.counterparty_name and item["name"] == doc.fields.counterparty_name:
            doc.fields.counterparty_inn = item["inn"]
            break

    for item in get_funds():
        if doc.fields.fund_name and item["name"] == doc.fields.fund_name:
            doc.fields.fund_inn = item["inn"]
            break

    for item in get_zpif():
        if doc.fields.zpif_name and item["name"] == doc.fields.zpif_name:
            if not doc.fields.fund_inn:
                doc.fields.fund_inn = item["inn"]
            break
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

    counterparty_names = get_counterparty_names()
    doc.fields.counterparty_name = _selectbox_with_value(
        "Контрагент",
        options=counterparty_names,
        current=doc.fields.counterparty_name,
        key=f"counterparty_{doc.id}",
    )
    for item in get_counterparties():
        if item["name"] == doc.fields.counterparty_name:
            doc.fields.counterparty_inn = item["inn"]
            break

    fund_names = [fund["name"] for fund in get_funds()]
    doc.fields.fund_name = _selectbox_with_value(
        "Юр. лицо",
        options=fund_names,
        current=doc.fields.fund_name,
        key=f"fund_{doc.id}",
    )
    for item in get_funds():
        if item["name"] == doc.fields.fund_name:
            doc.fields.fund_inn = item["inn"]
            break

    doc.fields.zpif_name = _selectbox_with_value(
        "ЗПИФ",
        options=get_zpif_names(),
        current=doc.fields.zpif_name,
        key=f"zpif_{doc.id}",
    )

    doc.fields.amount = st.number_input(
        "Сумма",
        min_value=0.0,
        value=float(doc.fields.amount or 0.0),
        step=0.01,
    )

    if doc.fields.counterparty_inn:
        st.caption(f"ИНН контрагента: {doc.fields.counterparty_inn}")

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

    st.markdown("**Дата оплаты**")
    st.caption("Планируемая дата оплаты счёта")
    payment_date_key = f"payment_date_{doc.id}"
    payment_col1, payment_col2, payment_col3 = st.columns(3)
    with payment_col1:
        if st.button("Конец месяца", use_container_width=True, key=f"pay_eom_{doc.id}"):
            last_day = calendar.monthrange(date.today().year, date.today().month)[1]
            doc.fields.payment_date = date(date.today().year, date.today().month, last_day)
            st.session_state[payment_date_key] = doc.fields.payment_date
            save_document(doc)
            st.rerun()
    with payment_col2:
        if st.button("+7 дней", use_container_width=True, key=f"pay_7d_{doc.id}"):
            doc.fields.payment_date = date.today() + timedelta(days=7)
            st.session_state[payment_date_key] = doc.fields.payment_date
            save_document(doc)
            st.rerun()
    with payment_col3:
        if st.button("Сегодня", use_container_width=True, key=f"pay_today_{doc.id}"):
            doc.fields.payment_date = date.today()
            st.session_state[payment_date_key] = doc.fields.payment_date
            save_document(doc)
            st.rerun()

    doc.fields.payment_date = st.date_input(
        "Дата оплаты",
        value=doc.fields.payment_date,
        label_visibility="collapsed",
        key=payment_date_key,
    )

    if st.button("Сохранить", use_container_width=True):
        if doc.status in (DocumentStatus.NEW, DocumentStatus.REJECTED):
            doc.status = DocumentStatus.ON_APPROVAL
        doc.touch()
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
        div[class*="st-key-approve_idle_"],
        div[class*="st-key-extra_approve_done_"],
        div[class*="st-key-extra_approve_pending_"],
        div[class*="st-key-extra_approve_idle_"] {
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
        div[class*="st-key-extra_approve_done_"] [data-testid="stElementContainer"],
        div[class*="st-key-extra_approve_pending_"] [data-testid="stElementContainer"],
        div[class*="st-key-extra_approve_idle_"] [data-testid="stElementContainer"],
        div[class*="st-key-approve_done_"] [data-testid="stVerticalBlock"],
        div[class*="st-key-approve_pending_"] [data-testid="stVerticalBlock"],
        div[class*="st-key-approve_idle_"] [data-testid="stVerticalBlock"],
        div[class*="st-key-extra_approve_done_"] [data-testid="stVerticalBlock"],
        div[class*="st-key-extra_approve_pending_"] [data-testid="stVerticalBlock"],
        div[class*="st-key-extra_approve_idle_"] [data-testid="stVerticalBlock"] {
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
        div[class*="st-key-approve_idle_"] button,
        div[class*="st-key-extra_approve_done_"] button,
        div[class*="st-key-extra_approve_pending_"] button,
        div[class*="st-key-extra_approve_idle_"] button {
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
            cursor: pointer !important;
        }
        div[class*="st-key-extra_approve_done_"] button {
            background: #16a34a !important;
            cursor: pointer !important;
        }
        div[class*="st-key-approve_done_"] button:hover,
        div[class*="st-key-extra_approve_done_"] button:hover {
            background: #15803d !important;
        }
        div[class*="st-key-approve_pending_"] button {
            background: #9ca3af !important;
        }
        div[class*="st-key-extra_approve_pending_"] button {
            background: #9ca3af !important;
        }
        div[class*="st-key-approve_pending_"] button:hover {
            background: #6b7280 !important;
        }
        div[class*="st-key-extra_approve_pending_"] button:hover {
            background: #6b7280 !important;
        }
        div[class*="st-key-approve_idle_"] button {
            background: #9ca3af !important;
            cursor: default !important;
        }
        div[class*="st-key-extra_approve_idle_"] button {
            background: #9ca3af !important;
            cursor: default !important;
        }
        div[class*="st-key-approve_done_"] button p,
        div[class*="st-key-approve_pending_"] button p,
        div[class*="st-key-approve_idle_"] button p,
        div[class*="st-key-extra_approve_done_"] button p,
        div[class*="st-key-extra_approve_pending_"] button p,
        div[class*="st-key-extra_approve_idle_"] button p {
            display: none !important;
        }
        div[class*="st-key-send_approval_"] button,
        div[class*="st-key-header_approve_"] button {
            font-size: 0.78rem !important;
            min-height: 1.85rem !important;
            padding: 0.2rem 0.5rem !important;
        }
        div[class*="st-key-send_approval_"] button p,
        div[class*="st-key-header_approve_"] button p {
            font-size: 0.78rem !important;
        }
        div[class*="st-key-header_approve_"] {
            display: flex !important;
            justify-content: flex-start !important;
            align-items: center !important;
        }
        div[class*="st-key-header_approve_"] [data-testid="stElementContainer"] {
            width: auto !important;
            margin-left: 0 !important;
        }
        div[class*="st-key-header_approve_"] button {
            width: auto !important;
            white-space: nowrap !important;
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


def _current_counterparty_name(doc: Document) -> str:
    return st.session_state.get(f"counterparty_{doc.id}", doc.fields.counterparty_name) or ""


def _render_counterparty_comments(doc: Document) -> None:
    counterparty_name = _current_counterparty_name(doc)
    counterparty = get_counterparty(counterparty_name)
    comment = counterparty.get("comment", "") if counterparty else ""
    lawyer_comment = counterparty.get("lawyer_comment", "") if counterparty else ""
    st.text_area(
        "Комментарий",
        value=comment,
        height=68,
        disabled=True,
        key=f"cp_comment_{doc.id}_{counterparty_name}",
    )
    st.text_area(
        "Комментарий юриста",
        value=lawyer_comment,
        height=68,
        disabled=True,
        key=f"cp_lawyer_comment_{doc.id}_{counterparty_name}",
    )


def _render_page_header(doc: Document) -> None:
    filename = Path(doc.pdf_filename).name if doc.pdf_filename else "—"
    title_col, comments_col = st.columns([4, 3], vertical_alignment="top")
    with title_col:
        st.subheader("Обработка")
        st.caption(filename)
        can_send = doc.status in (DocumentStatus.NEW, DocumentStatus.REJECTED)
        if st.button(
            "Согласовать",
            key=f"header_approve_{doc.id}",
            type="primary",
            disabled=not can_send,
        ):
            send_document_to_approval(doc)
            st.rerun()
    with comments_col:
        _render_counterparty_comments(doc)


def render() -> None:
    doc = _get_selected_document()
    _inject_page_styles()

    if doc is None:
        st.subheader("Обработка")
        st.warning("Выберите документ на странице «Документы» и нажмите «Обработать».")
        return

    _ensure_document_approvers(doc)

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

        spec_dep_sent = doc.spec_dep_status == SpecDepStatus.SENT
        if st.button(
            "Отправить в Спец.Деп",
            type="primary" if all_approved and not spec_dep_sent else "secondary",
            disabled=not all_approved or spec_dep_sent,
            use_container_width=True,
        ):
            doc.spec_dep_status = SpecDepStatus.SENT
            save_document(doc)
            st.success("Документ отправлен в Спец.Деп (демо).")
            st.rerun()

        if spec_dep_sent:
            st.caption("Документ уже отправлен в Спец.Деп.")
