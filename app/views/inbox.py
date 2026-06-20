from pathlib import Path
import calendar
from datetime import date

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
from config.reference_data import EXTRA_APPROVER_COUNT, MAIN_APPROVER_COUNT
from models.document import BankClientStatus, Document, DocumentStatus, SpecDepStatus

_SORTABLE_COLUMNS: list[tuple[str, str]] = [
    ("filename", "Файл"),
    ("received_at", "Получен"),
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


def _doc_zpif_name(doc: Document) -> str:
    return doc.fields.zpif_name or doc.fields.fund_name or ""


def _doc_zpif(doc: Document) -> str:
    return _doc_zpif_name(doc).lower()


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
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0.25rem 0.5rem;
            border-radius: 0.4rem;
            font-weight: 600;
            font-size: 0.75rem;
            line-height: 1.2;
            white-space: nowrap;
            min-height: 1.625rem;
            box-sizing: border-box;
        }
        .approval-progress {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            gap: 0.35rem;
            padding-right: 0.65rem;
            margin-right: 0.35rem;
            padding-bottom: 0.15rem;
        }
        .approval-dots {
            display: flex;
            gap: 0.28rem;
            align-items: center;
        }
        .approval-dot {
            width: 0.55rem;
            height: 0.55rem;
            border-radius: 50%;
            display: inline-block;
            flex-shrink: 0;
        }
        .approval-dot.pending {
            background: #d1d5db;
        }
        .approval-dot.approved {
            background: #16a34a;
        }
        .approval-dots-separator {
            color: #9ca3af;
            font-size: 0.7rem;
            line-height: 1;
            margin: 0 0.2rem;
            user-select: none;
        }
        div[class*="st-key-spec_dep_"],
        div[class*="st-key-avankor_"],
        div[class*="st-key-bank_client_"],
        div[class*="st-key-bank_pay_"],
        div[class*="st-key-process_"] {
            width: fit-content !important;
            max-width: 100% !important;
        }
        div[class*="st-key-bank_uploaded_"] {
            width: 100% !important;
            max-width: 100% !important;
        }
        div[class*="st-key-bank_uploaded_"] [data-testid="stElementContainer"],
        div[class*="st-key-bank_uploaded_"] [data-testid="stVerticalBlock"] {
            width: 100% !important;
            max-width: 100% !important;
        }
        div[class*="st-key-avankor_"] {
            margin-left: 0.45rem !important;
        }
        div[class*="st-key-spec_dep_"] [data-testid="stElementContainer"],
        div[class*="st-key-avankor_"] [data-testid="stElementContainer"],
        div[class*="st-key-bank_client_"] [data-testid="stElementContainer"],
        div[class*="st-key-bank_pay_"] [data-testid="stElementContainer"],
        div[class*="st-key-process_"] [data-testid="stElementContainer"],
        div[class*="st-key-spec_dep_"] [data-testid="stVerticalBlock"],
        div[class*="st-key-avankor_"] [data-testid="stVerticalBlock"],
        div[class*="st-key-bank_client_"] [data-testid="stVerticalBlock"],
        div[class*="st-key-bank_pay_"] [data-testid="stVerticalBlock"],
        div[class*="st-key-process_"] [data-testid="stVerticalBlock"] {
            width: fit-content !important;
            max-width: 100% !important;
        }
        div[class*="st-key-spec_dep_"] button,
        div[class*="st-key-avankor_"] button,
        div[class*="st-key-bank_client_"] button,
        div[class*="st-key-bank_pay_"] button,
        div[class*="st-key-process_"] button {
            font-size: 0.75rem !important;
            font-weight: 600 !important;
            padding: 0.25rem 0.5rem !important;
            min-height: 1.625rem !important;
            height: 1.625rem !important;
            line-height: 1.2 !important;
            white-space: nowrap !important;
            border-radius: 0.4rem !important;
            width: auto !important;
            box-sizing: border-box !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        div[class*="st-key-bank_pay_"] button {
            background: #fef3c7 !important;
            border: 1px solid #f59e0b !important;
            color: #92400e !important;
        }
        div[class*="st-key-bank_pay_"] button:hover {
            background: #fde68a !important;
            border-color: #d97706 !important;
            color: #78350f !important;
        }
        div[class*="st-key-bank_uploaded_"] [data-testid="stHorizontalBlock"] {
            gap: 0.35rem !important;
            justify-content: flex-start !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            width: 100% !important;
        }
        div[class*="st-key-bank_uploaded_"] [data-testid="column"] {
            width: auto !important;
            flex: 0 0 auto !important;
            min-width: 0 !important;
        }
        div[class*="st-key-bank_uploaded_"] [data-testid="column"]:first-child {
            min-width: 5.25rem !important;
        }
        div[class*="st-key-bank_uploaded_"] [data-testid="column"]:nth-child(2) {
            min-width: 4.75rem !important;
        }
        div[class*="st-key-bank_uploaded_"] div[class*="st-key-bank_pay_"] {
            width: auto !important;
            max-width: none !important;
        }
        div[class*="st-key-inbox_table"] [data-testid="stHorizontalBlock"] {
            align-items: flex-start !important;
        }
        div[class*="st-key-inbox_table"] [data-testid="column"] [data-testid="stVerticalBlock"] {
            justify-content: flex-start !important;
        }
        div[class*="st-key-inbox_table"] .doc-table-badge {
            margin-top: 0.05rem;
        }
        div[class*="st-key-spec_dep_"] button p,
        div[class*="st-key-avankor_"] button p,
        div[class*="st-key-bank_client_"] button p,
        div[class*="st-key-bank_pay_"] button p,
        div[class*="st-key-process_"] button p {
            font-size: 0.75rem !important;
            font-weight: 600 !important;
            white-space: nowrap !important;
            line-height: 1.2 !important;
            margin: 0 !important;
            padding: 0 !important;
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
        .inbox-action-header {
            white-space: nowrap;
            font-weight: 700;
            font-size: 0.8125rem;
        }
        div[class*="st-key-inbox_table"] {
            font-size: 0.8125rem;
        }
        div[class*="st-key-inbox_table"] [data-testid="stMarkdownContainer"],
        div[class*="st-key-inbox_table"] [data-testid="stMarkdownContainer"] p,
        div[class*="st-key-inbox_table"] [data-testid="stText"] {
            font-size: 0.8125rem !important;
            line-height: 1.35 !important;
        }
        div[class*="st-key-inbox_table"] div[class*="st-key-sort_"] button,
        div[class*="st-key-inbox_table"] div[class*="st-key-sort_"] button p {
            font-size: 0.8125rem !important;
        }
        div[class*="st-key-inbox_table"] div[class*="st-key-inbox_row_"] {
            padding-top: 0.4rem !important;
            padding-bottom: 0.4rem !important;
        }
        div[class*="st-key-inbox_table"] [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-child {
            margin-bottom: 0.35rem !important;
        }
        div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-inbox_filter_"]) {
            align-items: flex-end !important;
        }
        div[class*="st-key-inbox_filter_zpif"] [data-testid="stSelectbox"] > div {
            min-width: 0 !important;
        }
        div[class*="st-key-inbox_filter_zpif"] [data-baseweb="select"] > div {
            font-size: 0.82rem !important;
        }
        div[class*="st-key-inbox_filter_counterparty"] [data-baseweb="select"] > div {
            font-size: 0.82rem !important;
        }
        div[class*="st-key-inbox_filter_payment_popover"] button,
        div[class*="st-key-inbox_filter_received_popover"] button {
            font-size: 0.82rem !important;
            min-height: 2.4rem !important;
            padding: 0.35rem 0.65rem !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _doc_table_badge(label: str, background: str, border: str, color: str) -> str:
    return (
        f'<span class="doc-table-badge" style="background:{background};'
        f'border:1px solid {border};color:{color};">{label}</span>'
    )


_BADGE_GREEN = ("#dcfce7", "#16a34a", "#166534")
_BADGE_BLUE = ("#dbeafe", "#2563eb", "#1e40af")
_BADGE_GRAY = ("#f3f4f6", "#d1d5db", "#6b7280")
_BADGE_RED = ("#fee2e2", "#dc2626", "#991b1b")


def _approval_badge(status: DocumentStatus) -> str:
    if status in (DocumentStatus.APPROVED, DocumentStatus.SENT_TO_AVANKOR):
        label = "Согласован"
        background, border, color = _BADGE_GREEN
    elif status == DocumentStatus.ON_APPROVAL:
        label = "На согласовании"
        background, border, color = _BADGE_GRAY
    elif status == DocumentStatus.REJECTED:
        label = "Отклонён"
        background, border, color = _BADGE_RED
    else:
        label = "Не обработан"
        background, border, color = _BADGE_GRAY

    return _doc_table_badge(label, background, border, color)


def _approval_dot_html(approver) -> str:
    css_class = "approved" if approver and approver.approved else "pending"
    return f'<span class="approval-dot {css_class}"></span>'


def _approval_progress_dots(doc: Document) -> str:
    parts: list[str] = []
    for index in range(MAIN_APPROVER_COUNT):
        approver = doc.approvers[index] if index < len(doc.approvers) else None
        parts.append(_approval_dot_html(approver))

    if doc.real_estate_enabled:
        parts.append('<span class="approval-dots-separator">|</span>')
        for index in range(EXTRA_APPROVER_COUNT):
            approver = doc.extra_approvers[index] if index < len(doc.extra_approvers) else None
            parts.append(_approval_dot_html(approver))

    return f'<div class="approval-dots">{"".join(parts)}</div>'


def _render_approval_cell(col, doc: Document) -> None:
    badge = _approval_badge(doc.status)
    if doc.status == DocumentStatus.ON_APPROVAL:
        html = (
            f'<div class="approval-progress">{badge}{_approval_progress_dots(doc)}</div>'
        )
    else:
        html = badge
    col.markdown(html, unsafe_allow_html=True)


def _bank_client_badge(status: BankClientStatus) -> str:
    if status == BankClientStatus.UPLOADED:
        label = "Загружено"
        background, border, color = _BADGE_BLUE
    elif status == BankClientStatus.PAID:
        label = "Оплачено"
        background, border, color = _BADGE_GREEN
    else:
        return "—"

    return _doc_table_badge(label, background, border, color)


def _avankor_badge(status: DocumentStatus) -> str:
    if status == DocumentStatus.SENT_TO_AVANKOR:
        return _doc_table_badge("Отправлено", *_BADGE_GREEN)
    return "—"


def _spec_dep_sent_badge() -> str:
    return _doc_table_badge("Отправлено", *_BADGE_GREEN)


def _render_avankor_cell(col, doc: Document) -> None:
    if doc.status == DocumentStatus.SENT_TO_AVANKOR:
        col.markdown(_avankor_badge(doc.status), unsafe_allow_html=True)
    elif col.button("Отправить", key=f"avankor_{doc.id}"):
        doc.status = DocumentStatus.SENT_TO_AVANKOR
        save_document(doc)
        st.rerun()


def _render_bank_client_cell(col, doc: Document) -> None:
    if doc.bank_client_status == BankClientStatus.PAID:
        col.markdown(_bank_client_badge(doc.bank_client_status), unsafe_allow_html=True)
    elif doc.bank_client_status == BankClientStatus.UPLOADED:
        upload_box = col.container(key=f"bank_uploaded_{doc.id}")
        badge_col, pay_col = upload_box.columns([0.56, 0.44], gap="small")
        badge_col.markdown(_bank_client_badge(doc.bank_client_status), unsafe_allow_html=True)
        if pay_col.button("Оплатить", key=f"bank_pay_{doc.id}"):
            doc.bank_client_status = BankClientStatus.PAID
            save_document(doc)
            st.rerun()
    elif col.button("Отправить", key=f"bank_client_{doc.id}"):
        doc.bank_client_status = BankClientStatus.UPLOADED
        save_document(doc)
        st.rerun()


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


def _format_received_at(value) -> str:
    if value is None:
        return "—"
    return value.strftime("%d.%m.%Y")


def _normalize_date_selection(
    value: date | tuple[date, ...] | list[date] | None,
) -> tuple[date | None, date | None]:
    if value is None:
        return None, None
    if isinstance(value, tuple):
        if not value:
            return None, None
        if len(value) == 1:
            return value[0], value[0]
        start, end = value[0], value[-1]
        if start > end:
            start, end = end, start
        return start, end
    return value, value


def _end_of_month(day: date) -> date:
    last_day = calendar.monthrange(day.year, day.month)[1]
    return date(day.year, day.month, last_day)


def _doc_received_date(doc: Document) -> date | None:
    if doc.received_at is None:
        return None
    return doc.received_at.date()


def _date_in_range(
    value: date | None,
    *,
    range_start: date | None,
    range_end: date | None,
) -> bool:
    if value is None or range_start is None or range_end is None:
        return False
    return range_start <= value <= range_end


def _collect_filter_options(documents: list[Document]) -> tuple[list[str], list[str]]:
    zpif_names = sorted({_doc_zpif_name(doc) for doc in documents if _doc_zpif_name(doc)})
    counterparty_names = sorted(
        {doc.fields.counterparty_name for doc in documents if doc.fields.counterparty_name}
    )
    return zpif_names, counterparty_names


def _date_filter_button_label(
    mode: str,
    start: date | None,
    end: date | None,
) -> str:
    if mode == "Все" or start is None or end is None:
        return "Все"
    if start == end:
        return start.strftime("%d.%m.%Y")
    if start.year == end.year:
        return f"{start.strftime('%d.%m')}–{end.strftime('%d.%m.%Y')}"
    return f"{start.strftime('%d.%m.%Y')}–{end.strftime('%d.%m.%Y')}"


def _read_date_filter_state(
    key_prefix: str,
    *,
    today: date,
    month_start: date,
    month_end: date,
) -> tuple[str, date | None, date | None]:
    mode_key = f"{key_prefix}_mode"
    mode = st.session_state.get(mode_key, "Все")
    if mode == "Одна дата":
        selected = st.session_state.get(f"{key_prefix}_single", today)
        return mode, *_normalize_date_selection(selected)
    if mode == "Диапазон":
        selected = st.session_state.get(
            f"{key_prefix}_range",
            (month_start, month_end),
        )
        return mode, *_normalize_date_selection(selected)
    return "Все", None, None


def _reset_date_filter(key_prefix: str) -> None:
    for suffix in ("_mode", "_single", "_range"):
        st.session_state.pop(f"{key_prefix}{suffix}", None)


def _render_date_filter_popover(
    label: str,
    *,
    key_prefix: str,
    today: date,
    month_start: date,
    month_end: date,
) -> tuple[str, date | None, date | None]:
    mode_key = f"{key_prefix}_mode"
    mode_options = ["Все", "Одна дата", "Диапазон"]

    mode, start, end = _read_date_filter_state(
        key_prefix,
        today=today,
        month_start=month_start,
        month_end=month_end,
    )
    button_label = _date_filter_button_label(mode, start, end)

    with st.popover(button_label, use_container_width=True):
        st.markdown(f"**{label}**")
        current_mode = st.session_state.get(mode_key, "Все")
        st.radio(
            "Тип выбора",
            options=mode_options,
            index=mode_options.index(current_mode) if current_mode in mode_options else 0,
            horizontal=True,
            key=mode_key,
        )
        selected_mode = st.session_state[mode_key]
        if selected_mode == "Одна дата":
            st.date_input(
                "Дата",
                value=start or today,
                key=f"{key_prefix}_single",
            )
        elif selected_mode == "Диапазон":
            default_range = (start, end) if start and end else (month_start, month_end)
            st.date_input(
                "Период",
                value=default_range,
                key=f"{key_prefix}_range",
            )
        if selected_mode != "Все":
            st.button(
                "Сбросить",
                key=f"{key_prefix}_reset",
                use_container_width=True,
                on_click=_reset_date_filter,
                args=(key_prefix,),
            )

    return _read_date_filter_state(
        key_prefix,
        today=today,
        month_start=month_start,
        month_end=month_end,
    )


def _apply_document_filters(
    documents: list[Document],
    *,
    zpif_filter: str,
    counterparty_filter: str,
    payment_mode: str,
    payment_start: date | None,
    payment_end: date | None,
    received_mode: str,
    received_start: date | None,
    received_end: date | None,
) -> list[Document]:
    filtered = documents
    if zpif_filter != "Все":
        filtered = [doc for doc in filtered if _doc_zpif_name(doc) == zpif_filter]
    if counterparty_filter != "Все":
        filtered = [
            doc for doc in filtered if doc.fields.counterparty_name == counterparty_filter
        ]
    if payment_mode != "Все":
        filtered = [
            doc
            for doc in filtered
            if _date_in_range(
                doc.fields.payment_date,
                range_start=payment_start,
                range_end=payment_end,
            )
        ]
    if received_mode != "Все":
        filtered = [
            doc
            for doc in filtered
            if _date_in_range(
                _doc_received_date(doc),
                range_start=received_start,
                range_end=received_end,
            )
        ]
    return filtered


def _render_document_filters(documents: list[Document]) -> list[Document]:
    today = date.today()
    month_start = date(today.year, today.month, 1)
    month_end = _end_of_month(today)
    zpif_names, counterparty_names = _collect_filter_options(documents)

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(
        [0.85, 1.35, 1.1, 1.1],
        gap="small",
    )
    with filter_col1:
        zpif_filter = st.selectbox(
            "ЗПИФ",
            options=["Все", *zpif_names],
            index=0,
            key="inbox_filter_zpif",
        )
    with filter_col2:
        counterparty_filter = st.selectbox(
            "Контрагент",
            options=["Все", *counterparty_names],
            index=0,
            key="inbox_filter_counterparty",
        )
    with filter_col3:
        st.caption("Дата оплаты")
        with st.container(key="inbox_filter_payment_popover"):
            payment_mode, payment_start, payment_end = _render_date_filter_popover(
                "Дата оплаты",
                key_prefix="inbox_filter_payment",
                today=today,
                month_start=month_start,
                month_end=month_end,
            )
    with filter_col4:
        st.caption("Получен")
        with st.container(key="inbox_filter_received_popover"):
            received_mode, received_start, received_end = _render_date_filter_popover(
                "Получен",
                key_prefix="inbox_filter_received",
                today=today,
                month_start=month_start,
                month_end=month_end,
            )

    filtered = _apply_document_filters(
        documents,
        zpif_filter=zpif_filter,
        counterparty_filter=counterparty_filter,
        payment_mode=payment_mode,
        payment_start=payment_start,
        payment_end=payment_end,
        received_mode=received_mode,
        received_start=received_start,
        received_end=received_end,
    )
    st.caption(f"Показано документов: {len(filtered)} из {len(documents)}")
    return filtered


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
    filtered_documents = _render_document_filters(documents)
    if not filtered_documents:
        st.info("Нет документов по выбранным фильтрам.")
        return

    _init_inbox_sort()
    filtered_documents = _sort_documents(
        filtered_documents,
        sort_by=st.session_state.inbox_sort_by,
        ascending=st.session_state.inbox_sort_asc,
    )

    column_weights = [1.65, 0.75, 0.9, 0.95, 0.65, 0.75, 0.85, 1.15, 1.0, 0.85, 1.55, 0.95]
    with st.container(key="inbox_table"):
        header = st.columns(column_weights)
        for index, (field, label) in enumerate(_SORTABLE_COLUMNS):
            _render_sortable_header(header[index], field, label)
        header[11].markdown('<span class="inbox-action-header">Действие</span>', unsafe_allow_html=True)

        for doc in filtered_documents:
            row_box = st.container(key=f"inbox_row_{doc.id}")
            cols = row_box.columns(column_weights)
            filename = Path(doc.pdf_filename).name if doc.pdf_filename else "—"
            if doc.diadoc_message_id:
                filename = f"{filename} · Diadoc"
            cols[0].write(filename)
            cols[1].write(_format_received_at(doc.received_at))
            cols[2].write(doc.fields.zpif_name or doc.fields.fund_name or "—")
            cols[3].write(doc.fields.counterparty_name or "—")
            cols[4].write(doc.document_type.label if doc.document_type else "—")
            cols[5].write(f"{doc.fields.amount:,.2f}" if doc.fields.amount else "—")
            cols[6].write(_format_payment_date(doc.fields.payment_date))
            _render_approval_cell(cols[7], doc)
            _render_avankor_cell(cols[8], doc)
            _render_spec_dep_cell(cols[9], doc)
            _render_bank_client_cell(cols[10], doc)
            if cols[11].button("Обработать", key=f"process_{doc.id}"):
                _open_document(doc.id)
