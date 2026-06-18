import streamlit as st

from app.services.document_store import save_document
from models.document import ApprovalPhase, Document, DocumentStatus


def send_document_to_approval(doc: Document) -> None:
    doc.status = DocumentStatus.ON_APPROVAL
    doc.reset_approvals()
    save_document(doc)


def render_approval_status(doc: Document, *, show_send_button: bool = True) -> None:
    phase = doc.approval_phase

    if phase == ApprovalPhase.NOT_APPROVED:
        if show_send_button and st.button(
            "Отправить на согласование",
            key=f"send_approval_{doc.id}",
            type="primary",
            use_container_width=True,
        ):
            send_document_to_approval(doc)
            st.rerun()
        return

    if phase == ApprovalPhase.PENDING:
        label = "На согласовании"
        background = "#6b7280"
        border = "#4b5563"
        color = "#ffffff"
    else:
        label = "Согласован"
        background = "#dcfce7"
        border = "#16a34a"
        color = "#166534"

    st.markdown(
        f"""
        <div class="approval-status-badge" style="
        background:{background};border:1px solid {border};color:{color};">
        {label}
        </div>
        """,
        unsafe_allow_html=True,
    )
