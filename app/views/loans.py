import streamlit as st

from app.components.loans_history import render_loans_history_table
from app.components.payment_registry import render_payment_registry
from app.services.reference_store import (
    all_shareholders_approved,
    archive_current_loan,
    get_accounts_for_zpif,
    get_counterparty_names,
    get_loan_request,
    get_shareholders_for_zpif,
    get_zpif_names,
    init_references,
    reset_loan_shareholder_approvals,
)


def _render_shareholder_approvals(loan: dict, zpif_name: str) -> None:
    shareholders = get_shareholders_for_zpif(zpif_name)
    if not shareholders:
        st.info("Для выбранного ЗПИФ нет акционеров. Добавьте их в справочник «Акционеры ЗПИФ».")
        return

    approvals: dict[str, bool] = loan.setdefault("shareholder_approvals", {})
    for shareholder in shareholders:
        name = shareholder["name"]
        approvals.setdefault(name, False)

        icon_col, text_col = st.columns([0.5, 5.5], vertical_alignment="center")
        with icon_col:
            if loan["status"] == "approved" or approvals.get(name):
                st.button(
                    " ",
                    key=f"loan_done_{loan['id']}_{name}",
                    disabled=True,
                    type="tertiary",
                    help="Согласовано",
                )
            elif loan["status"] != "on_approval":
                st.button(
                    " ",
                    key=f"loan_idle_{loan['id']}_{name}",
                    disabled=True,
                    type="tertiary",
                )
            elif st.button(
                " ",
                key=f"loan_pending_{loan['id']}_{name}",
                help="Согласовать",
                type="tertiary",
            ):
                approvals[name] = True
                if all_shareholders_approved(loan):
                    loan["status"] = "approved"
                st.rerun()
        with text_col:
            st.markdown(f"**{name}** — _{shareholder['inn']}_")


def _render_loan_status(loan: dict) -> None:
    if loan["status"] == "draft":
        label = "Не отправлено"
        background = "#f3f4f6"
        border = "#d1d5db"
        color = "#6b7280"
    elif loan["status"] == "on_approval":
        label = "Ожидается согласование акционеров"
        background = "#fef9c3"
        border = "#ca8a04"
        color = "#854d0e"
    else:
        label = "Согласовано акционерами"
        background = "#dcfce7"
        border = "#16a34a"
        color = "#166534"

    st.markdown(
        f"""
        <div class="loan-status-badge" style="
        background:{background};border:1px solid {border};color:{color};">
        {label}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _inject_loan_styles() -> None:
    st.markdown(
        """
        <style>
        .loan-status-badge {
            display: inline-block;
            padding: 0.3rem 0.55rem;
            border-radius: 0.4rem;
            font-weight: 600;
            font-size: 0.75rem;
            margin-bottom: 0.35rem;
        }
        div[class*="st-key-loan_send_approval_"] button {
            font-size: 0.75rem !important;
            min-height: 1.75rem !important;
            padding: 0.2rem 0.55rem !important;
            width: auto !important;
        }
        div[class*="st-key-loan_send_approval_"] button p {
            font-size: 0.75rem !important;
        }
        div[class*="st-key-loan_done_"],
        div[class*="st-key-loan_pending_"],
        div[class*="st-key-loan_idle_"] {
            width: 100% !important;
            height: 32px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        div[class*="st-key-loan_done_"] button,
        div[class*="st-key-loan_pending_"] button,
        div[class*="st-key-loan_idle_"] button {
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
        div[class*="st-key-loan_done_"] button {
            background: #16a34a !important;
        }
        div[class*="st-key-loan_pending_"] button {
            background: #9ca3af !important;
        }
        div[class*="st-key-loan_pending_"] button:hover {
            background: #6b7280 !important;
        }
        div[class*="st-key-loan_idle_"] button {
            background: #9ca3af !important;
        }
        div[class*="st-key-loan_done_"] button p,
        div[class*="st-key-loan_pending_"] button p,
        div[class*="st-key-loan_idle_"] button p {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    init_references()
    _inject_loan_styles()

    st.subheader("Займы")
    render_loans_history_table()
    st.markdown("**Выдать новый займ**")

    loan = get_loan_request()
    zpif_names = get_zpif_names()
    form_locked = loan["status"] == "on_approval"

    if not zpif_names:
        st.warning("Справочник ЗПИФ пуст. Добавьте фонды на странице «Справочники».")
        return

    current_zpif = loan["zpif"] if loan["zpif"] in zpif_names else zpif_names[0]
    selected_zpif = st.selectbox(
        "ЗПИФ",
        options=zpif_names,
        index=zpif_names.index(current_zpif),
        disabled=form_locked,
    )

    if selected_zpif != loan["zpif"] and loan["status"] == "draft":
        loan["zpif"] = selected_zpif
        loan["account"] = ""
        reset_loan_shareholder_approvals(selected_zpif)

    account_options = get_accounts_for_zpif(selected_zpif)
    if account_options:
        current_account = loan["account"] if loan["account"] in account_options else account_options[0]
        loan["account"] = st.selectbox(
            "Счёт",
            options=account_options,
            index=account_options.index(current_account),
            disabled=form_locked,
        )
    else:
        st.selectbox("Счёт", options=["—"], disabled=True)
        st.caption("Для выбранного ЗПИФ счета не заданы.")

    recipient_options = get_counterparty_names()
    if recipient_options:
        current_recipient = (
            loan["recipient"] if loan["recipient"] in recipient_options else recipient_options[0]
        )
        loan["recipient"] = st.selectbox(
            "Получатель займа",
            options=recipient_options,
            index=recipient_options.index(current_recipient),
            disabled=form_locked,
        )
    else:
        loan["recipient"] = st.text_input(
            "Получатель займа",
            value=loan["recipient"],
            disabled=form_locked,
        )

    loan["amount"] = st.number_input(
        "Сумма займа",
        min_value=0.0,
        value=float(loan["amount"] or 0.0),
        step=0.01,
        disabled=form_locked,
    )

    render_payment_registry()

    st.markdown("---")
    st.markdown("**Согласование акционерами**")

    actions_col, _ = st.columns([2.2, 3.8])
    with actions_col:
        _render_loan_status(loan)
        if loan["status"] == "draft":
            if st.button(
                "Отправить на согласование акционерам",
                type="primary",
                key="loan_send_approval_btn",
            ):
                if loan["amount"] <= 0:
                    st.error("Укажите сумму займа больше нуля.")
                    return
                if not loan.get("account"):
                    st.error("Выберите счёт.")
                    return
                if not loan.get("recipient"):
                    st.error("Укажите получателя займа.")
                    return
                shareholders = get_shareholders_for_zpif(selected_zpif)
                if not shareholders:
                    st.error("Для выбранного ЗПИФ нет акционеров в справочнике.")
                    return
                loan["zpif"] = selected_zpif
                loan["status"] = "on_approval"
                reset_loan_shareholder_approvals(selected_zpif)
                st.success("Заявка отправлена акционерам на согласование.")
                st.rerun()

    st.markdown("")
    _render_shareholder_approvals(loan, selected_zpif)

    if loan["status"] == "approved":
        st.markdown("---")
        st.success("Все акционеры согласовали займ.")
        issue_col, new_col = st.columns(2)
        with issue_col:
            if st.button("Выдать займ", type="primary"):
                archive_current_loan(status="issued")
                st.success("Займ выдан.")
                st.rerun()
        with new_col:
            if st.button("Создать новую заявку"):
                archive_current_loan(status="approved")
                st.rerun()
