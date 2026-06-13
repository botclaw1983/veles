import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app.auth import logout_button, require_auth
from app.views import document, inbox, settings
from config.settings import settings

st.set_page_config(
    page_title=settings.app_title,
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

if not require_auth():
    st.stop()

logout_button()

pg = st.navigation(
    [
        st.Page(inbox.render, title="Входящие", icon="📥", default=True),
        st.Page(document.render, title="Документ", icon="📝"),
        st.Page(settings.render, title="Настройки", icon="⚙️"),
    ]
)
pg.run()
