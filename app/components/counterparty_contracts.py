from __future__ import annotations

from pathlib import Path

import fitz
import streamlit as st

from app.components.pdf_viewer import render_pdf
from app.services.reference_store import get_contract_pdf_path, get_contracts_for_counterparty
from models.document import Document


def _inject_contract_styles() -> None:
    st.markdown(
        """
        <style>
        div[class*="st-key-contract_pick_"] button {
            font-size: 0.82rem !important;
            padding: 0.15rem 0.45rem !important;
            min-height: 0 !important;
            height: auto !important;
            color: #2563eb !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            text-decoration: underline !important;
        }
        div[class*="st-key-contract_pick_"] button:hover {
            color: #1d4ed8 !important;
            background: #eff6ff !important;
        }
        div[class*="st-key-contract_pick_"] button p {
            font-size: 0.82rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _ensure_contract_pdfs(contracts: list[dict[str, str]]) -> None:
    for contract in contracts:
        path = get_contract_pdf_path(contract)
        if path.is_file():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        pdf = fitz.open()
        page = pdf.new_page(width=595, height=842)
        lines = [
            contract.get("title") or "Договор",
            "",
            f"№ {contract.get('number', '—')}",
            f"Дата: {contract.get('date', '—')}",
            "",
            f"Контрагент: {contract.get('counterparty_name', '—')}",
            f"ИНН: {contract.get('counterparty_inn', '—')}",
            "",
            "Демонстрационный текст договора для прототипа Veles.",
        ]
        page.insert_text((56, 72), "\n".join(lines), fontsize=12)
        pdf.save(path)
        pdf.close()


def render_counterparty_contracts(doc: Document) -> None:
    counterparty_name = doc.fields.counterparty_name.strip()
    if not counterparty_name:
        return

    contracts = get_contracts_for_counterparty(
        counterparty_name,
        doc.fields.counterparty_inn,
    )
    if not contracts:
        return

    _ensure_contract_pdfs(contracts)
    _inject_contract_styles()

    st.markdown("---")
    st.markdown("**Договоры контрагента**")
    st.caption(counterparty_name)

    selected_key = f"selected_contract_{doc.id}"
    button_cols = st.columns(min(len(contracts), 4) or 1)
    for index, contract in enumerate(contracts):
        label = contract["number"]
        with button_cols[index % len(button_cols)]:
            if st.button(
                label,
                key=f"contract_pick_{doc.id}_{contract['id']}",
                type="tertiary",
            ):
                st.session_state[selected_key] = contract["id"]
                st.rerun()

    selected_id = st.session_state.get(selected_key)
    if not selected_id:
        return

    selected = next((item for item in contracts if item["id"] == selected_id), None)
    if selected is None:
        return

    pdf_path = get_contract_pdf_path(selected)
    st.markdown(
        f"**{selected.get('title') or 'Договор'}** · № {selected['number']} от {selected['date']}"
    )
    if pdf_path.is_file():
        render_pdf(pdf_path, height=640)
    else:
        st.warning(f"Файл договора не найден: {pdf_path}")
