import streamlit as st

from config.settings import settings


def init_session() -> None:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "documents" not in st.session_state:
        st.session_state.documents = []
    if "selected_document_id" not in st.session_state:
        st.session_state.selected_document_id = None


def render_login() -> None:
    st.caption("Автоматизация документооборота УК ПИФ")

    with st.form("login"):
        username = st.text_input("Логин", value=settings.auth_username)
        password = st.text_input("Пароль", type="password", value=settings.auth_password)
        submitted = st.form_submit_button("Войти", type="primary")

    if submitted:
        if username == settings.auth_username and password == settings.auth_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Неверный логин или пароль")


def require_auth() -> bool:
    init_session()
    if not st.session_state.authenticated:
        render_login()
        return False
    return True


def logout_button() -> None:
    if st.sidebar.button("Выйти"):
        st.session_state.authenticated = False
        st.session_state.selected_document_id = None
        st.rerun()
