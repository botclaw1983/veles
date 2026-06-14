from __future__ import annotations

import copy

import pandas as pd
import streamlit as st

from config.reference_data import DEFAULT_PAYMENT_REGISTRY


def _format_rub(value: float) -> str:
    formatted = f"{value:,.2f}".replace(",", " ").replace(".", ",")
    return f"{formatted} ₽"


def get_payment_registry(registry_key: str = "ref_payment_registry") -> dict:
    if registry_key not in st.session_state:
        st.session_state[registry_key] = copy.deepcopy(DEFAULT_PAYMENT_REGISTRY)
    return st.session_state[registry_key]


def render_payment_registry(registry_key: str = "ref_payment_registry") -> None:
    registry = get_payment_registry(registry_key)
    payments = registry["payments"]
    total = sum(item["amount"] for item in payments)

    st.markdown("**Согласование реестра платежей**")
    st.caption(f"Плательщик: {registry['payer']}")

    meta_col1, meta_col2, meta_col3 = st.columns(3)
    meta_col1.markdown(f"**Платёжная дата:** {registry['payment_date']}")
    meta_col2.markdown(f"**Остаток денежных средств:** {_format_rub(registry['cash_balance'])}")
    meta_col3.markdown(
        f"**Плановый остаток после платежей:** {_format_rub(registry['planned_balance'])}"
    )

    df = pd.DataFrame(
        [
            {
                "№": item["num"],
                "Получатель платежа": item["recipient"],
                "Назначение платежа": item["purpose"],
                "Сумма платежа": _format_rub(item["amount"]),
                "Срок оплаты": item["due_date"],
                "комментарий": item["comment"],
            }
            for item in payments
        ]
    )

    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        height=min(420, 38 + len(payments) * 36),
    )

    total_col1, total_col2 = st.columns([4, 2])
    total_col1.markdown("**ИТОГО**")
    total_col2.markdown(f"**{_format_rub(total)}**")
