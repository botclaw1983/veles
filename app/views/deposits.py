import streamlit as st

from app.components.deposits_history import render_deposits_history_table
from app.components.payment_registry import render_payment_registry
from app.services.reference_store import (
    all_shareholders_approved,
    archive_current_deposit,
    get_accounts_for_deposit_zpif,
    get_counterparty_names,
    get_deposit_request,
    get_shareholders_for_zpif,
    get_zpif_names,
    init_references,
    reset_deposit_shareholder_approvals,
)


def _render_shareholder_approvals(deposit: dict, zpif_name: str) -> None:
    shareholders = get_shareholders_for_zpif(zpif_name)
    if not shareholders:
        st.info("Для выбранного ЗПИФ нет акционеров. Добавьте их в справочник «Акционеры ЗПИФ».")
        return

    approvals: dict[str, bool] = deposit.setdefault("shareholder_approvals", {})
    for shareholder in shareholders:
        name = shareholder["name"]
        approvals.setdefault(name, False)

        icon_col, text_col = st.columns([0.5, 5.5], vertical_alignment="center")
        with icon_col:
            if deposit["status"] == "approved" or approvals.get(name):
                st.button(
                    " ",
                    key=f"deposit_done_{deposit['id']}_{name}",
                    disabled=True,
                    type="tertiary",
                    help="Согласовано",
                )
            elif deposit["status"] != "on_approval":
                st.button(
                    " ",
                    key=f"deposit_idle_{deposit['id']}_{name}",
                    disabled=True,
                    type="tertiary",
                )
            elif st.button(
                " ",
                key=f"deposit_pending_{deposit['id']}_{name}",
                help="Согласовать",
                type="tertiary",
            ):
                approvals[name] = True
                if all_shareholders_approved(deposit):
                    deposit["status"] = "approved"
                st.rerun()
        with text_col:
            st.markdown(f"**{name}** — _{shareholder['inn']}_")


def _render_deposit_status(deposit: dict) -> None:
    if deposit["status"] == "draft":
        label = "Не отправлено"
        background = "#f3f4f6"
        border = "#d1d5db"
        color = "#6b7280"
    elif deposit["status"] == "on_approval":
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
        <div class="deposit-status-badge" style="
        background:{background};border:1px solid {border};color:{color};">
        {label}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _inject_deposit_styles() -> None:
    st.markdown(
        """
        <style>
        .deposit-status-badge {
            display: inline-block;
            padding: 0.3rem 0.55rem;
            border-radius: 0.4rem;
            font-weight: 600;
            font-size: 0.75rem;
            margin-bottom: 0.35rem;
        }
        div[class*="st-key-deposit_send_approval_"] button {
            font-size: 0.75rem !important;
            min-height: 1.75rem !important;
            padding: 0.2rem 0.55rem !important;
            width: auto !important;
        }
        div[class*="st-key-deposit_send_approval_"] button p {
            font-size: 0.75rem !important;
        }
        div[class*="st-key-deposit_done_"],
        div[class*="st-key-deposit_pending_"],
        div[class*="st-key-deposit_idle_"] {
            width: 100% !important;
            height: 32px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        div[class*="st-key-deposit_done_"] button,
        div[class*="st-key-deposit_pending_"] button,
        div[class*="st-key-deposit_idle_"] button {
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
        div[class*="st-key-deposit_done_"] button {
            background: #16a34a !important;
        }
        div[class*="st-key-deposit_pending_"] button {
            background: #9ca3af !important;
        }
        div[class*="st-key-deposit_pending_"] button:hover {
            background: #6b7280 !important;
        }
        div[class*="st-key-deposit_idle_"] button {
            background: #9ca3af !important;
        }
        div[class*="st-key-deposit_done_"] button p,
        div[class*="st-key-deposit_pending_"] button p,
        div[class*="st-key-deposit_idle_"] button p {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    init_references()
    _inject_deposit_styles()

    st.subheader("Депозиты")
    render_deposits_history_table()
    st.markdown("**Выдать новый депозит**")

    deposit = get_deposit_request()
    zpif_names = get_zpif_names()
    form_locked = deposit["status"] == "on_approval"

    if not zpif_names:
        st.warning("Справочник ЗПИФ пуст. Добавьте фонды на странице «Справочники».")
        return

    current_zpif = deposit["zpif"] if deposit["zpif"] in zpif_names else zpif_names[0]
    selected_zpif = st.selectbox(
        "ЗПИФ",
        options=zpif_names,
        index=zpif_names.index(current_zpif),
        disabled=form_locked,
        key="deposit_zpif_select",
    )

    if selected_zpif != deposit["zpif"] and deposit["status"] == "draft":
        deposit["zpif"] = selected_zpif
        deposit["account"] = ""
        reset_deposit_shareholder_approvals(selected_zpif)

    account_options = get_accounts_for_deposit_zpif(selected_zpif)
    if account_options:
        current_account = (
            deposit["account"] if deposit["account"] in account_options else account_options[0]
        )
        deposit["account"] = st.selectbox(
            "Счёт",
            options=account_options,
            index=account_options.index(current_account),
            disabled=form_locked,
            key="deposit_account_select",
        )
    else:
        st.selectbox("Счёт", options=["—"], disabled=True, key="deposit_account_empty")
        st.caption("Для выбранного ЗПИФ счета не заданы.")

    recipient_options = get_counterparty_names()
    if recipient_options:
        current_recipient = (
            deposit["recipient"]
            if deposit["recipient"] in recipient_options
            else recipient_options[0]
        )
        deposit["recipient"] = st.selectbox(
            "Получатель депозита",
            options=recipient_options,
            index=recipient_options.index(current_recipient),
            disabled=form_locked,
            key="deposit_recipient_select",
        )
    else:
        deposit["recipient"] = st.text_input(
            "Получатель депозита",
            value=deposit["recipient"],
            disabled=form_locked,
            key="deposit_recipient_input",
        )

    deposit["amount"] = st.number_input(
        "Сумма депозита",
        min_value=0.0,
        value=float(deposit["amount"] or 0.0),
        step=0.01,
        disabled=form_locked,
        key="deposit_amount_input",
    )

    render_payment_registry(registry_key="ref_deposit_payment_registry")

    st.markdown("---")
    st.markdown("**Согласование акционерами**")

    actions_col, _ = st.columns([2.2, 3.8])
    with actions_col:
        _render_deposit_status(deposit)
        if deposit["status"] == "draft":
            if st.button(
                "Отправить на согласование акционерам",
                type="primary",
                key="deposit_send_approval_btn",
            ):
                if deposit["amount"] <= 0:
                    st.error("Укажите сумму депозита больше нуля.")
                    return
                if not deposit.get("account"):
                    st.error("Выберите счёт.")
                    return
                if not deposit.get("recipient"):
                    st.error("Укажите получателя депозита.")
                    return
                shareholders = get_shareholders_for_zpif(selected_zpif)
                if not shareholders:
                    st.error("Для выбранного ЗПИФ нет акционеров в справочнике.")
                    return
                deposit["zpif"] = selected_zpif
                deposit["status"] = "on_approval"
                reset_deposit_shareholder_approvals(selected_zpif)
                st.success("Заявка отправлена акционерам на согласование.")
                st.rerun()

    st.markdown("")
    _render_shareholder_approvals(deposit, selected_zpif)

    if deposit["status"] == "approved":
        st.markdown("---")
        st.success("Все акционеры согласовали депозит.")
        issue_col, new_col = st.columns(2)
        with issue_col:
            if st.button("Выдать депозит", type="primary", key="deposit_issue_btn"):
                archive_current_deposit(status="issued")
                st.success("Депозит выдан.")
                st.rerun()
        with new_col:
            if st.button("Создать новую заявку", key="deposit_new_request_btn"):
                archive_current_deposit(status="approved")
                st.rerun()
