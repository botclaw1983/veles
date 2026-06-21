import pandas as pd
import streamlit as st

from app.services.reference_store import calculate_receivables_report


def _format_rub(value: float) -> str:
    formatted = f"{value:,.2f}".replace(",", " ").replace(".", ",")
    return f"{formatted} ₽"


def _format_pct(value: float) -> str:
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{text.replace('.', ',')} %"


def render_receivables_table(zpif_name: str) -> list[dict]:
    rows = calculate_receivables_report(zpif_name)
    if not rows:
        st.info("По выбранному ЗПИФ нет остатков дебиторской задолженности в Аванкоре (демо).")
        return []

    df = pd.DataFrame(
        [
            {
                "Арендатор": row["tenant_name"],
                "ИНН": row["tenant_inn"],
                "Договор": row["contract_number"],
                "Период": row["period"],
                "Просрочка, дн.": row["days_overdue"],
                "ОПФ": row["legal_form"],
                "ОКВЭД": row["okved"],
                "Номинал ДЗ": _format_rub(row["nominal"]),
                "Депозит": _format_rub(row["security_deposit"]),
                "PD": _format_pct(row["pd_pct"]),
                "Дисконт СЧА": _format_pct(row["scha_discount_pct"]),
                "Итого %": _format_pct(row["total_discount_pct"]),
                "Текущая стоимость": _format_rub(row["current_value"]),
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

    total_nominal = sum(row["nominal"] for row in rows)
    total_current = sum(row["current_value"] for row in rows)
    total_discount = sum(row["discount_amount"] for row in rows)

    col1, col2, col3, col4 = st.columns([2.5, 1.5, 1.5, 1.5])
    col1.markdown("**ИТОГО по фонду**")
    col2.markdown(f"**{_format_rub(total_nominal)}**")
    col3.markdown(f"**−{_format_rub(total_discount)}**")
    col4.markdown(f"**{_format_rub(total_current)}**")

    return rows
