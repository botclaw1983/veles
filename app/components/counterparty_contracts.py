from __future__ import annotations

import streamlit as st

from app.components.pdf_viewer import render_pdf
from app.services.reference_store import get_source_contract_pdf
from models.document import Document


def render_counterparty_contracts(doc: Document) -> None:
    pdf_path = get_source_contract_pdf()
    if pdf_path is None:
        return

    st.markdown("**Договор**")
    render_pdf(pdf_path, height=640)
