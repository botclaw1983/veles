from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.services.reference_store import get_source_contract_pdf
from integrations.ollama_recognition import (
    DEFAULT_CONTRACT_ANALYSIS_PROMPT,
    analyze_contract_against_invoice,
    check_ollama_available,
)
from models.document import Document


def _prompt_session_key(doc_id: str) -> str:
    return f"contract_analysis_prompt_{doc_id}"


def _result_session_key(doc_id: str) -> str:
    return f"contract_analysis_result_{doc_id}"


def _get_analysis_prompt(doc_id: str) -> str:
    key = _prompt_session_key(doc_id)
    if key not in st.session_state:
        st.session_state[key] = DEFAULT_CONTRACT_ANALYSIS_PROMPT
    return st.session_state[key]


def render_contract_analysis(doc: Document) -> None:
    """Блок сверки счёта с договором: промпт (свёрнут) и результат анализа."""
    if not doc.pdf_filename or not Path(doc.pdf_filename).is_file():
        return

    contract_pdf = get_source_contract_pdf()
    if contract_pdf is None:
        st.markdown("**Сверка с договором**")
        st.caption("PDF не найден в папке «Договор».")
        return

    st.markdown("**Сверка с договором**")
    st.caption(contract_pdf.name)

    ok, error = check_ollama_available()
    if not ok:
        st.caption(f"Анализ недоступен: {error}")
        return

    with st.expander("Промпт для модели", expanded=False):
        prompt_key = _prompt_session_key(doc.id)
        st.text_area(
            "Промпт",
            value=_get_analysis_prompt(doc.id),
            height=220,
            label_visibility="collapsed",
            key=prompt_key,
        )
        if st.button("Сбросить промпт", key=f"reset_contract_prompt_{doc.id}"):
            st.session_state[prompt_key] = DEFAULT_CONTRACT_ANALYSIS_PROMPT
            st.rerun()

    if st.button(
        "Сверить с договором",
        use_container_width=True,
        key=f"analyze_contract_{doc.id}",
    ):
        with st.spinner("Анализ счёта и договора..."):
            try:
                result = analyze_contract_against_invoice(
                    doc.pdf_filename,
                    contract_pdf,
                    prompt=st.session_state.get(
                        _prompt_session_key(doc.id),
                        DEFAULT_CONTRACT_ANALYSIS_PROMPT,
                    ),
                    counterparty_name=doc.fields.counterparty_name,
                    counterparty_inn=doc.fields.counterparty_inn,
                    amount=doc.fields.amount,
                    contract_title=contract_pdf.stem,
                )
                st.session_state[_result_session_key(doc.id)] = result
            except Exception as exc:  # noqa: BLE001 — показываем ошибку в UI
                st.error(f"Ошибка анализа: {exc}")

    result = st.session_state.get(_result_session_key(doc.id))
    if result:
        st.markdown("**Анализ**")
        st.markdown(result)
