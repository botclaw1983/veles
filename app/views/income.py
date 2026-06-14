import streamlit as st

from app.components.income_distribution import render_unitholders_table
from app.services.reference_store import (
    all_income_approvers_approved,
    get_approvers,
    get_income_request,
    get_shareholders_for_zpif,
    get_zpif_names,
    init_references,
    reset_income_approvals,
)


def _render_approval_status(income: dict) -> None:
    if income["status"] == "draft":
        label = "Не отправлено"
        background = "#f3f4f6"
        border = "#d1d5db"
        color = "#6b7280"
    elif income["status"] == "on_approval":
        label = "Ожидается согласование"
        background = "#fef9c3"
        border = "#ca8a04"
        color = "#854d0e"
    elif income["status"] == "approved":
        label = "Согласовано"
        background = "#dcfce7"
        border = "#16a34a"
        color = "#166534"
    else:
        label = "Отправлено в Аванкор"
        background = "#dbeafe"
        border = "#1e40af"
        color = "#1e40af"

    st.markdown(
        f"""
        <div class="income-status-badge" style="
        background:{background};border:1px solid {border};color:{color};">
        {label}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_approvers(income: dict) -> None:
    approvers = get_approvers()
    if not approvers:
        st.info("Справочник согласующих пуст. Добавьте записи на странице «Справочники».")
        return

    approvals: dict[str, bool] = income.setdefault("approver_approvals", {})
    locked = income["status"] in {"approved", "sent_to_avankor"}

    for name, role in approvers:
        approvals.setdefault(name, False)

        icon_col, text_col = st.columns([0.5, 5.5], vertical_alignment="center")
        with icon_col:
            if income["status"] == "sent_to_avankor" or approvals.get(name):
                st.button(
                    " ",
                    key=f"income_done_{income['id']}_{name}",
                    disabled=True,
                    type="tertiary",
                    help="Согласовано",
                )
            elif locked or income["status"] != "on_approval":
                st.button(
                    " ",
                    key=f"income_idle_{income['id']}_{name}",
                    disabled=True,
                    type="tertiary",
                )
            elif st.button(
                " ",
                key=f"income_pending_{income['id']}_{name}",
                help="Согласовать",
                type="tertiary",
            ):
                approvals[name] = True
                if all_income_approvers_approved(income):
                    income["status"] = "approved"
                st.rerun()
        with text_col:
            st.markdown(f"**{name}** — _{role}_")


def _inject_income_styles() -> None:
    st.markdown(
        """
        <style>
        .income-status-badge {
            display: inline-block;
            padding: 0.3rem 0.55rem;
            border-radius: 0.4rem;
            font-weight: 600;
            font-size: 0.75rem;
            margin-bottom: 0.35rem;
        }
        div[class*="st-key-income_send_approval_"] button {
            font-size: 0.75rem !important;
            min-height: 1.75rem !important;
            padding: 0.2rem 0.55rem !important;
            width: auto !important;
        }
        div[class*="st-key-income_done_"],
        div[class*="st-key-income_pending_"],
        div[class*="st-key-income_idle_"] {
            width: 100% !important;
            height: 32px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        div[class*="st-key-income_done_"] button,
        div[class*="st-key-income_pending_"] button,
        div[class*="st-key-income_idle_"] button {
            width: 20px !important;
            height: 20px !important;
            min-width: 20px !important;
            min-height: 20px !important;
            border-radius: 50% !important;
            padding: 0 !important;
            margin: 0 !important;
            border: none !important;
            color: transparent !important;
            font-size: 0 !important;
            opacity: 1 !important;
        }
        div[class*="st-key-income_done_"] button {
            background: #16a34a !important;
        }
        div[class*="st-key-income_pending_"] button {
            background: #9ca3af !important;
        }
        div[class*="st-key-income_pending_"] button:hover {
            background: #6b7280 !important;
        }
        div[class*="st-key-income_idle_"] button {
            background: #9ca3af !important;
        }
        div[class*="st-key-income_done_"] button p,
        div[class*="st-key-income_pending_"] button p,
        div[class*="st-key-income_idle_"] button p {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    init_references()
    _inject_income_styles()

    st.subheader("Доход")
    st.markdown("**Распределение дохода**")

    income = get_income_request()
    zpif_names = get_zpif_names()
    form_locked = income["status"] in {"on_approval", "approved", "sent_to_avankor"}

    if not zpif_names:
        st.warning("Справочник ЗПИФ пуст. Добавьте фонды на странице «Справочники».")
        return

    current_zpif = income["zpif"] if income["zpif"] in zpif_names else zpif_names[0]
    selected_zpif = st.selectbox(
        "ЗПИФ",
        options=zpif_names,
        index=zpif_names.index(current_zpif),
        disabled=form_locked,
        key="income_zpif_select",
    )

    if selected_zpif != income["zpif"] and income["status"] == "draft":
        income["zpif"] = selected_zpif

    income["amount"] = st.number_input(
        "Сумма дохода",
        min_value=0.0,
        value=float(income["amount"] or 0.0),
        step=0.01,
        disabled=form_locked,
        key="income_amount_input",
    )

    st.markdown("**Пайщики**")
    render_unitholders_table(selected_zpif, float(income["amount"] or 0.0))

    st.markdown("---")
    st.markdown("**Согласование**")

    actions_col, _ = st.columns([2.2, 3.8])
    with actions_col:
        _render_approval_status(income)
        if income["status"] == "draft":
            if st.button(
                "Отправить на согласование",
                type="primary",
                key="income_send_approval_btn",
            ):
                if income["amount"] <= 0:
                    st.error("Укажите сумму дохода больше нуля.")
                    return
                if not get_approvers():
                    st.error("Справочник согласующих пуст.")
                    return
                if not get_shareholders_for_zpif(selected_zpif):
                    st.error("Для выбранного ЗПИФ нет пайщиков в справочнике.")
                    return
                income["zpif"] = selected_zpif
                income["status"] = "on_approval"
                reset_income_approvals()
                st.success("Распределение дохода отправлено на согласование.")
                st.rerun()

    st.markdown("")
    _render_approvers(income)

    st.markdown("---")
    st.markdown("**Отправить в Аванкор**")

    avankor_sent = income["status"] == "sent_to_avankor"
    all_approved = income["status"] == "approved" or avankor_sent

    if st.button(
        "Отправить в Аванкор",
        type="primary" if all_approved and not avankor_sent else "secondary",
        disabled=not all_approved or avankor_sent,
        use_container_width=True,
        key="income_send_avankor_btn",
    ):
        income["status"] = "sent_to_avankor"
        st.success("Распределение дохода отправлено в Аванкор (демо).")
        st.rerun()

    if avankor_sent:
        st.caption("Данные уже отправлены в Аванкор.")
