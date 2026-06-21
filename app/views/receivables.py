from datetime import date

import streamlit as st

from app.components.receivables_report import render_receivables_table
from app.services.reference_store import (
    all_receivables_approvers_approved,
    build_receivables_export_csv,
    get_approvers,
    get_receivables_report,
    get_zpif_names,
    init_references,
    reset_receivables_approvals,
)


def _render_status(report: dict) -> None:
    status = report["status"]
    if status == "draft":
        label = "Черновик"
        background = "#f3f4f6"
        border = "#d1d5db"
        color = "#6b7280"
    elif status == "on_approval":
        label = "На проверке у главного бухгалтера"
        background = "#fef9c3"
        border = "#ca8a04"
        color = "#854d0e"
    elif status == "approved":
        label = "Согласовано"
        background = "#dcfce7"
        border = "#16a34a"
        color = "#166534"
    else:
        label = "Экспортировано для СЧА"
        background = "#dbeafe"
        border = "#1e40af"
        color = "#1e40af"

    st.markdown(
        f"""
        <div class="receivables-status-badge" style="
        background:{background};border:1px solid {border};color:{color};">
        {label}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_approvers(report: dict) -> None:
    approvers = get_approvers()
    if not approvers:
        st.info("Справочник согласующих пуст. Добавьте записи на странице «Справочники».")
        return

    approvals: dict[str, bool] = report.setdefault("approver_approvals", {})
    locked = report["status"] in {"approved", "exported"}

    for name, role in approvers:
        approvals.setdefault(name, False)
        icon_col, text_col = st.columns([0.5, 5.5], vertical_alignment="center")
        with icon_col:
            if report["status"] == "exported" or approvals.get(name):
                st.button(
                    " ",
                    key=f"recv_done_{report['id']}_{name}",
                    disabled=True,
                    type="tertiary",
                    help="Согласовано",
                )
            elif locked or report["status"] != "on_approval":
                st.button(
                    " ",
                    key=f"recv_idle_{report['id']}_{name}",
                    disabled=True,
                    type="tertiary",
                )
            elif st.button(
                " ",
                key=f"recv_pending_{report['id']}_{name}",
                help="Согласовать",
                type="tertiary",
            ):
                approvals[name] = True
                if all_receivables_approvers_approved(report):
                    report["status"] = "approved"
                st.rerun()
        with text_col:
            st.markdown(f"**{name}** — _{role}_")


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .receivables-status-badge {
            display: inline-block;
            padding: 0.3rem 0.55rem;
            border-radius: 0.4rem;
            font-weight: 600;
            font-size: 0.75rem;
            margin-bottom: 0.35rem;
        }
        div[class*="st-key-recv_send_approval_"] button {
            font-size: 0.75rem !important;
            min-height: 1.75rem !important;
            padding: 0.2rem 0.55rem !important;
            width: auto !important;
        }
        div[class*="st-key-recv_done_"],
        div[class*="st-key-recv_pending_"],
        div[class*="st-key-recv_idle_"] {
            width: 100% !important;
            height: 32px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        div[class*="st-key-recv_done_"] button,
        div[class*="st-key-recv_pending_"] button,
        div[class*="st-key-recv_idle_"] button {
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
        div[class*="st-key-recv_done_"] button {
            background: #16a34a !important;
        }
        div[class*="st-key-recv_pending_"] button {
            background: #9ca3af !important;
        }
        div[class*="st-key-recv_pending_"] button:hover {
            background: #6b7280 !important;
        }
        div[class*="st-key-recv_idle_"] button {
            background: #9ca3af !important;
        }
        div[class*="st-key-recv_done_"] button p,
        div[class*="st-key-recv_pending_"] button p,
        div[class*="st-key-recv_idle_"] button p {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    init_references()
    _inject_styles()

    st.subheader("Отчёт по дебиторской задолженности")
    st.caption(
        "Расчёт текущей стоимости ДЗ арендаторов для целей СЧА: "
        "номинал из Аванкора → ОКВЭД, PD, правила СЧА, обеспечительный депозит."
    )

    report = get_receivables_report()
    zpif_names = get_zpif_names()
    form_locked = report["status"] in {"on_approval", "approved", "exported"}

    if not zpif_names:
        st.warning("Справочник ЗПИФ пуст. Добавьте фонды на странице «Справочники».")
        return

    current_zpif = report["zpif"] if report["zpif"] in zpif_names else zpif_names[0]
    filter_col1, filter_col2, filter_col3 = st.columns([2, 1.2, 1.2])
    with filter_col1:
        selected_zpif = st.selectbox(
            "ЗПИФ",
            options=zpif_names,
            index=zpif_names.index(current_zpif),
            disabled=form_locked,
            key="receivables_zpif_select",
        )
    with filter_col2:
        report_date = st.date_input(
            "Дата расчёта",
            value=date.fromisoformat(report["report_date"]),
            disabled=form_locked,
            key="receivables_report_date",
        )
    with filter_col3:
        st.markdown("")
        st.markdown("")
        if st.button(
            "Обновить из Аванкора",
            disabled=form_locked,
            use_container_width=True,
            key="receivables_reload_avankor",
        ):
            report["loaded_from_avankor"] = True
            st.success("Остатки ДЗ загружены из Аванкора (демо).")
            st.rerun()

    if selected_zpif != report["zpif"] and report["status"] == "draft":
        report["zpif"] = selected_zpif
    if report_date.isoformat() != report["report_date"] and report["status"] == "draft":
        report["report_date"] = report_date.isoformat()

    st.markdown("**Расчётный лист**")
    rows = render_receivables_table(selected_zpif)

    st.markdown("---")
    st.markdown("**Согласование**")

    actions_col, _ = st.columns([2.2, 3.8])
    with actions_col:
        _render_status(report)
        if report["status"] == "draft":
            if st.button(
                "Отправить на проверку",
                type="primary",
                key="recv_send_approval_btn",
            ):
                if not rows:
                    st.error("Нет данных для расчёта по выбранному ЗПИФ.")
                    return
                if not get_approvers():
                    st.error("Справочник согласующих пуст.")
                    return
                report["zpif"] = selected_zpif
                report["report_date"] = report_date.isoformat()
                report["status"] = "on_approval"
                reset_receivables_approvals()
                st.success("Расчёт отправлен на проверку главному бухгалтеру.")
                st.rerun()

    st.markdown("")
    _render_approvers(report)

    st.markdown("---")
    st.markdown("**Экспорт для СЧА / XBRL**")

    export_ready = report["status"] in {"approved", "exported"} and bool(rows)
    export_col, _ = st.columns([2.2, 3.8])
    with export_col:
        csv_data = build_receivables_export_csv(selected_zpif, report_date.isoformat())
        st.download_button(
            "Скачать файл расчёта (CSV)",
            data=csv_data,
            file_name=f"dz_{selected_zpif.replace(' ', '_')}_{report_date.isoformat()}.csv",
            mime="text/csv",
            disabled=not export_ready,
            use_container_width=True,
            key="receivables_export_csv",
        )
        if st.button(
            "Отметить как переданный в контур СЧА",
            disabled=not export_ready or report["status"] == "exported",
            use_container_width=True,
            key="receivables_mark_exported",
        ):
            report["status"] = "exported"
            st.success("Файл расчёта передан в контур СЧА (демо).")
            st.rerun()

    if report["status"] == "exported":
        st.caption("Расчёт уже передан в контур СЧА / XBRL.")

    with st.expander("Методика расчёта (демо)"):
        st.markdown(
            """
            1. **Номинальная ДЗ** — остаток задолженности арендатора в Аванкоре.
            2. **PD** — вероятность дефолта по префиксу ОКВЭД (справочник отраслевых ставок).
            3. **Дисконт СЧА** — базовый процент по ОПФ контрагента (ЮЛ / ИП).
            4. **Обеспечительный депозит** уменьшает сумму, к которой применяется дисконт.
            5. **Текущая стоимость** = номинал − (номинал − депозит) × (дисконт СЧА + PD) / 100.
            """
        )
