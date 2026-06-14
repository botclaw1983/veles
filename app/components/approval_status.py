import streamlit as st

from models.document import ApprovalPhase, Document, DocumentStatus


def render_approval_status(doc: Document) -> None:
    phase = doc.approval_phase

    if phase == ApprovalPhase.NOT_APPROVED:
        if st.button(
            "Отправить на согласование",
            key=f"send_approval_{doc.id}",
            type="primary",
            use_container_width=True,
        ):
            doc.status = DocumentStatus.ON_APPROVAL
            doc.reset_approvals()
            doc.touch()
            st.rerun()
        return

    if phase == ApprovalPhase.PENDING:
        label = "Ожидается согласование"
        background = "#fef9c3"
        border = "#ca8a04"
        color = "#854d0e"
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
