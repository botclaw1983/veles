from __future__ import annotations

from pathlib import Path

import streamlit as st

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
VELES_LOGO = ASSETS_DIR / "veles_capital_logo.svg"
VELES_LOGO_URL = "https://veles-capital.ru/"


def inject_brand_styles() -> None:
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] {
            min-width: 16rem !important;
            max-width: 20rem !important;
        }
        section[data-testid="stSidebar"] > div:first-child {
            min-width: 16rem !important;
            max-width: 20rem !important;
        }

        /* Логотип в открытом сайдбаре */
        [data-testid="stSidebarHeader"] {
            min-height: 4.25rem !important;
            padding: 0.75rem 0.75rem 0.35rem 0.75rem !important;
            align-items: flex-start !important;
        }
        [data-testid="stSidebarCollapseButton"] {
            display: none !important;
        }
        [data-testid="stSidebarHeader"] > div:first-child,
        [data-testid="stSidebarHeader"] a,
        [data-testid="stSidebarHeader"] span {
            flex: 1 1 auto !important;
            width: 100% !important;
            max-width: 100% !important;
            max-height: none !important;
        }
        [data-testid="stSidebarHeader"] img {
            display: block !important;
            visibility: visible !important;
            width: 100% !important;
            height: auto !important;
            max-width: 100% !important;
            max-height: none !important;
            min-height: 2.5rem !important;
            object-fit: contain !important;
            object-position: left center !important;
        }

        /* Логотип при свёрнутом сайдбаре — сдвиг вправо от полоски */
        [data-testid="stHeaderLogo"] {
            margin-left: 0.75rem !important;
            padding-right: 0.5rem !important;
        }
        [data-testid="stHeaderLogo"] img {
            display: block !important;
            visibility: visible !important;
            width: auto !important;
            height: auto !important;
            max-height: 2.25rem !important;
            max-width: min(15rem, 42vw) !important;
            object-fit: contain !important;
            object-position: left center !important;
        }

        /* Кнопка раскрытия сайдбара слева */
        [data-testid="stExpandSidebarButton"] {
            margin-left: 0.35rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def configure_app_branding() -> None:
    st.logo(str(VELES_LOGO), link=VELES_LOGO_URL, size="large")
    inject_brand_styles()
