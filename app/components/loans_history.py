import pandas as pd
import streamlit as st

from app.services.reference_store import get_loan_status_label, get_loans_for_display


def _format_rub(value: float) -> str:
    formatted = f"{value:,.2f}".replace(",", " ").replace(".", ",")
    return f"{formatted} ₽"


def _style_status_cell(value: str) -> str:
    styles = {
        "новый": "background-color: #f3f4f6; color: #4b5563; font-weight: 600",
        "на согласовании": "background-color: #fef9c3; color: #854d0e; font-weight: 600",
        "согласован": "background-color: #dcfce7; color: #166534; font-weight: 600",
        "выдан": "background-color: #dbeafe; color: #1e40af; font-weight: 600",
    }
    return styles.get(value, "")


def render_loans_history_table() -> None:
    loans = get_loans_for_display()
    if not loans:
        st.info("Ранее выданных займов пока нет.")
        return

    df = pd.DataFrame(
        [
            {
                "ЗПИФ": loan["zpif"],
                "Счёт": loan["account"],
                "Получатель займа": loan["recipient"],
                "Сумма займа": _format_rub(loan["amount"]),
                "Статус": get_loan_status_label(loan["status"]),
            }
            for loan in loans
        ]
    )

    styled_df = df.style.map(_style_status_cell, subset=["Статус"])

    st.dataframe(
        styled_df,
        hide_index=True,
        use_container_width=True,
        height=min(260, 38 + len(loans) * 36),
    )
