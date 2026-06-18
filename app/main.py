import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app.auth import logout_button, require_auth
from app.branding import configure_app_branding
from app.services.reference_store import init_references
from app.views import deposits, directories, document, inbox, income, loans, payment_calendar
from app.views import settings as settings_page
from config.settings import settings
from db import init_db

st.set_page_config(
    page_title=settings.app_title,
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    st.set_option("client.toolbarMode", "minimal")
except Exception:
    pass

configure_app_branding()

try:
    init_db()
except Exception as exc:
    st.error(f"Не удалось подключиться к PostgreSQL: {exc}")
    st.stop()

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        width: 22% !important;
    }
    [data-testid="stSidebarNav"] a span {
        font-size: 0.875rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if not require_auth():
    st.stop()

init_references()

logout_button()

document_page = st.Page(
    document.render,
    title="Обработка",
    icon="📝",
    url_path="document",
)
st.session_state["nav_document_page"] = document_page

pg = st.navigation(
    [
        st.Page(inbox.render, title="Документы", icon="📄", default=True, url_path="inbox"),
        document_page,
        st.Page(
            payment_calendar.render,
            title="Платежный календарь",
            icon="📅",
            url_path="payment-calendar",
        ),
        st.Page(directories.render, title="Справочники", icon="📚", url_path="directories"),
        st.Page(loans.render, title="Займы", icon="💰", url_path="loans"),
        st.Page(deposits.render, title="Депозиты", icon="🏦", url_path="deposits"),
        st.Page(income.render, title="Доход", icon="📈", url_path="income"),
        st.Page(settings_page.render, title="Настройки", icon="⚙️", url_path="settings"),
    ]
)
pg.run()
