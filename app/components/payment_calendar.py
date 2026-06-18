from __future__ import annotations

import calendar
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

from app.services.document_store import list_documents
from models.document import BankClientStatus, Document


def _format_rub(value: float | None) -> str:
    if value is None:
        return "—"
    formatted = f"{value:,.2f}".replace(",", " ").replace(".", ",")
    return f"{formatted} ₽"


def _format_date(value: date | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%d.%m.%Y")


def _end_of_month(day: date) -> date:
    last_day = calendar.monthrange(day.year, day.month)[1]
    return date(day.year, day.month, last_day)


def _is_payable(doc: Document) -> bool:
    return doc.bank_client_status != BankClientStatus.PAID


def _pending_documents(documents: list[Document]) -> list[Document]:
    return [doc for doc in documents if _is_payable(doc) and doc.fields.amount]


def _urgency_class(payment_date: date | None, today: date) -> str:
    if payment_date is None:
        return "unscheduled"
    if payment_date < today:
        return "overdue"
    if payment_date <= today + timedelta(days=7):
        return "soon"
    return "planned"


def _inject_calendar_styles() -> None:
    st.markdown(
        """
        <style>
        .pay-cal-metric {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 0.65rem;
            padding: 0.85rem 1rem;
        }
        .pay-cal-metric-label {
            color: #64748b;
            font-size: 0.78rem;
            margin-bottom: 0.25rem;
        }
        .pay-cal-metric-value {
            font-size: 1.35rem;
            font-weight: 700;
            color: #0f172a;
            line-height: 1.2;
        }
        .pay-cal-metric-sub {
            color: #64748b;
            font-size: 0.75rem;
            margin-top: 0.2rem;
        }
        .pay-cal-date-header {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            margin: 1rem 0 0.45rem;
        }
        .pay-cal-date-badge {
            display: inline-block;
            padding: 0.2rem 0.55rem;
            border-radius: 0.4rem;
            font-weight: 700;
            font-size: 0.78rem;
            white-space: nowrap;
        }
        .pay-cal-date-badge.overdue {
            background: #fee2e2;
            border: 1px solid #dc2626;
            color: #991b1b;
        }
        .pay-cal-date-badge.soon {
            background: #fef3c7;
            border: 1px solid #d97706;
            color: #92400e;
        }
        .pay-cal-date-badge.planned {
            background: #dcfce7;
            border: 1px solid #16a34a;
            color: #166534;
        }
        .pay-cal-date-badge.unscheduled {
            background: #f3f4f6;
            border: 1px solid #d1d5db;
            color: #6b7280;
        }
        .pay-cal-date-sum {
            color: #475569;
            font-size: 0.82rem;
        }
        div[class*="st-key-pay_cal_open_"] button {
            font-size: 0.75rem !important;
            padding: 0.2rem 0.45rem !important;
            min-height: 0 !important;
            height: auto !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _open_document(doc_id: str) -> None:
    st.session_state.selected_document_id = doc_id
    st.switch_page(st.session_state["nav_document_page"])


def _render_metric(label: str, amount: float, count: int, sub: str = "") -> None:
    st.markdown(
        f"""
        <div class="pay-cal-metric">
            <div class="pay-cal-metric-label">{label}</div>
            <div class="pay-cal-metric-value">{_format_rub(amount)}</div>
            <div class="pay-cal-metric-sub">{count} платеж(ей){f" · {sub}" if sub else ""}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _date_header_label(payment_date: date | None, today: date) -> tuple[str, str]:
    if payment_date is None:
        return "Без даты оплаты", "unscheduled"
    urgency = _urgency_class(payment_date, today)
    weekday = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][payment_date.weekday()]
    label = f"{payment_date.strftime('%d.%m.%Y')} ({weekday})"
    if urgency == "overdue":
        days = (today - payment_date).days
        label += f" · просрочено {days} дн."
    elif urgency == "soon":
        days = (payment_date - today).days
        label += f" · через {days} дн."
    return label, urgency


def render_payment_calendar() -> None:
    _inject_calendar_styles()
    today = date.today()
    month_start = date(today.year, today.month, 1)
    month_end = _end_of_month(today)
    week_end = today + timedelta(days=7)

    all_docs = list_documents()
    pending = _pending_documents(all_docs)

    zpif_names = sorted(
        {doc.fields.zpif_name or doc.fields.fund_name for doc in pending if doc.fields.zpif_name or doc.fields.fund_name}
    )

    filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 3])
    with filter_col1:
        view_filter = st.selectbox(
            "Период",
            options=["Все", "Просрочено", "На этой неделе", "В этом месяце", "Без даты"],
            index=0,
        )
    with filter_col2:
        zpif_filter = st.selectbox(
            "ЗПИФ",
            options=["Все"] + zpif_names,
            index=0,
        )
    with filter_col3:
        st.caption(
            "УК ЗПИФ может переносить оплату счетов — укажите дату на странице «Обработка» "
            "или в списке «Документы»."
        )

    def _matches_filters(doc: Document) -> bool:
        payment_date = doc.fields.payment_date
        zpif = doc.fields.zpif_name or doc.fields.fund_name
        if zpif_filter != "Все" and zpif != zpif_filter:
            return False
        if view_filter == "Просрочено":
            return payment_date is not None and payment_date < today
        if view_filter == "На этой неделе":
            return payment_date is not None and today <= payment_date <= week_end
        if view_filter == "В этом месяце":
            return payment_date is not None and month_start <= payment_date <= month_end
        if view_filter == "Без даты":
            return payment_date is None
        return True

    filtered = [doc for doc in pending if _matches_filters(doc)]

    overdue = [doc for doc in pending if doc.fields.payment_date and doc.fields.payment_date < today]
    this_week = [
        doc for doc in pending
        if doc.fields.payment_date and today <= doc.fields.payment_date <= week_end
    ]
    this_month = [
        doc for doc in pending
        if doc.fields.payment_date and month_start <= doc.fields.payment_date <= month_end
    ]
    unscheduled = [doc for doc in pending if doc.fields.payment_date is None]

    metric_cols = st.columns(4)
    with metric_cols[0]:
        _render_metric("Просрочено", sum(d.fields.amount or 0 for d in overdue), len(overdue))
    with metric_cols[1]:
        _render_metric("На этой неделе", sum(d.fields.amount or 0 for d in this_week), len(this_week))
    with metric_cols[2]:
        _render_metric("В этом месяце", sum(d.fields.amount or 0 for d in this_month), len(this_month))
    with metric_cols[3]:
        _render_metric(
            "Без даты",
            sum(d.fields.amount or 0 for d in unscheduled),
            len(unscheduled),
            sub="нужно запланировать",
        )

    st.markdown("---")

    if not filtered:
        st.info("Нет платежей по выбранным фильтрам.")
        return

    def _sort_key(doc: Document) -> tuple:
        payment_date = doc.fields.payment_date
        if payment_date is None:
            return (1, date.max, doc.fields.counterparty_name or "")
        return (0, payment_date, doc.fields.counterparty_name or "")

    filtered.sort(key=_sort_key)

    grouped: dict[date | None, list[Document]] = {}
    for doc in filtered:
        grouped.setdefault(doc.fields.payment_date, []).append(doc)

    group_dates = sorted(
        (d for d in grouped if d is not None),
        key=lambda d: d,
    )
    if None in grouped:
        group_dates.append(None)

    for payment_date in group_dates:
        docs = grouped[payment_date]
        group_total = sum(doc.fields.amount or 0 for doc in docs)
        label, urgency = _date_header_label(payment_date, today)
        st.markdown(
            f"""
            <div class="pay-cal-date-header">
                <span class="pay-cal-date-badge {urgency}">{label}</span>
                <span class="pay-cal-date-sum">{_format_rub(group_total)} · {len(docs)} шт.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_weights = [1.4, 1.2, 1.0, 0.9, 1.4, 0.7]
        header = st.columns(col_weights)
        header[0].markdown("**Контрагент**")
        header[1].markdown("**ЗПИФ**")
        header[2].markdown("**Тип**")
        header[3].markdown("**Сумма**")
        header[4].markdown("**Назначение**")
        header[5].markdown("**Действие**")

        for doc in docs:
            cols = st.columns(col_weights)
            cols[0].write(doc.fields.counterparty_name or "—")
            cols[1].write(doc.fields.zpif_name or doc.fields.fund_name or "—")
            cols[2].write(doc.document_type.label if doc.document_type else "—")
            cols[3].write(_format_rub(doc.fields.amount))
            purpose = doc.fields.description or "—"
            if len(purpose) > 60:
                purpose = purpose[:57] + "…"
            filename = Path(doc.pdf_filename).name if doc.pdf_filename else ""
            if filename:
                purpose = f"{purpose}\n_{filename}_" if purpose != "—" else f"_{filename}_"
            cols[4].write(purpose)
            if cols[5].button("Открыть", key=f"pay_cal_open_{doc.id}"):
                _open_document(doc.id)

        st.markdown("")
