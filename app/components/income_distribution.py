import pandas as pd
import streamlit as st

from app.services.reference_store import calculate_income_distribution


def _format_rub(value: float) -> str:
    formatted = f"{value:,.2f}".replace(",", " ").replace(".", ",")
    return f"{formatted} ₽"


def _format_pct(value: float) -> str:
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return f"{text.replace('.', ',')} %"


def render_unitholders_table(zpif_name: str, total_amount: float) -> None:
    rows = calculate_income_distribution(zpif_name, total_amount)
    if not rows:
        st.info("Для выбранного ЗПИФ нет пайщиков или сумма дохода не задана.")
        return

    df = pd.DataFrame(
        [
            {
                "Пайщик": row["name"],
                "ИНН": row["inn"],
                "Доля": _format_pct(row["share_pct"]),
                "Сумма дохода": _format_rub(row["amount"]),
            }
            for row in rows
        ]
    )

    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        height=min(420, 38 + len(rows) * 36),
    )

    total_col1, total_col2 = st.columns([4, 2])
    total_col1.markdown("**ИТОГО**")
    total_col2.markdown(f"**{_format_rub(total_amount)}**")
