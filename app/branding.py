from __future__ import annotations

from pathlib import Path

import streamlit as st

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
VELES_LOGO = ASSETS_DIR / "veles_capital_logo.svg"
VELES_LOGO_URL = "https://veles-capital.ru/"

# Ширина полоски сайдбара в свёрнутом состоянии (только кнопка «развернуть»)
SIDEBAR_RAIL = "7rem"
# Горизонтальный отступ основного контента Streamlit (wide layout)
MAIN_PADDING_X = "1rem"


def inject_brand_styles() -> None:
    rail = SIDEBAR_RAIL
    main_pad = MAIN_PADDING_X
    st.markdown(
        f"""
        <style>
        :root {{
            --veles-sidebar-rail: {rail};
        }}

        /* Убрать Deploy и меню «три точки» */
        [data-testid="stAppDeployButton"],
        [data-testid="stMainMenu"],
        [data-testid="stToolbarActions"],
        .stAppDeployButton {{
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
            overflow: hidden !important;
            pointer-events: none !important;
        }}

        section[data-testid="stSidebar"] {{
            min-width: 16rem !important;
            max-width: 20rem !important;
        }}
        section[data-testid="stSidebar"] > div:first-child {{
            min-width: 16rem !important;
            max-width: 20rem !important;
        }}

        /* --- Сайдбар открыт --- */
        section[data-testid="stSidebar"][aria-expanded="true"] {{
            transform: none !important;
        }}

        [data-testid="stSidebarHeader"],
        [data-testid="stSidebarLogo"] {{
            min-height: 4.25rem !important;
        }}
        [data-testid="stSidebarHeader"] {{
            padding: 0.75rem 0.75rem 0.35rem 0.75rem !important;
            align-items: flex-start !important;
        }}
        [data-testid="stSidebarHeader"] > div:first-child,
        [data-testid="stSidebarHeader"] a,
        [data-testid="stSidebarLogo"] a {{
            width: 100% !important;
            max-width: 100% !important;
        }}
        [data-testid="stSidebarHeader"] img,
        [data-testid="stSidebarLogo"] img {{
            display: block !important;
            width: 100% !important;
            height: auto !important;
            max-height: none !important;
            min-height: 2.25rem !important;
            object-fit: contain !important;
            object-position: left center !important;
        }}

        [data-testid="stSidebarHeader"] [data-testid="stSidebarCollapseButton"] {{
            display: none !important;
        }}

        section[data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarCollapseButton"] {{
            display: inline-flex !important;
            position: fixed !important;
            bottom: 4.75rem !important;
            left: 0.85rem !important;
            z-index: 1001 !important;
        }}

        body:has(section[data-testid="stSidebar"][aria-expanded="true"]) header[data-testid="stHeader"],
        body:has(section[data-testid="stSidebar"][aria-expanded="true"]) [data-testid="stHeaderLogo"],
        body:has(section[data-testid="stSidebar"][aria-expanded="true"]) [data-testid="stExpandSidebarButton"] {{
            display: none !important;
        }}

        /* --- Сайдбар свёрнут: узкая полоска слева --- */
        section[data-testid="stSidebar"][aria-expanded="false"] {{
            transform: none !important;
            width: {rail} !important;
            min-width: {rail} !important;
            max-width: {rail} !important;
            box-shadow: 1px 0 0 #e5e7eb !important;
            z-index: 998 !important;
            overflow: hidden !important;
        }}
        section[data-testid="stSidebar"][aria-expanded="false"] > div:first-child {{
            width: {rail} !important;
            min-width: {rail} !important;
            max-width: {rail} !important;
        }}

        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stSidebarNav"],
        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stSidebarUserContent"],
        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stSidebarCollapseButton"],
        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stSidebarHeader"],
        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stSidebarLogo"] {{
            display: none !important;
        }}

        /*
         * Свёрнутый сайдбар: стрелка в узкой полоске слева,
         * логотип — в зоне контента (как заголовок страницы по оси X).
         */
        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) header[data-testid="stHeader"] {{
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            width: 100% !important;
            min-width: 100% !important;
            max-width: 100% !important;
            height: 3.25rem !important;
            min-height: 3.25rem !important;
            background-color: transparent !important;
            border-right: none !important;
            z-index: 1001 !important;
            pointer-events: none !important;
            box-sizing: border-box !important;
        }}

        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) header[data-testid="stHeader"]::before {{
            content: "" !important;
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            width: {rail} !important;
            height: 100% !important;
            background-color: #f0f2f6 !important;
            border-right: 1px solid #e5e7eb !important;
            z-index: 0 !important;
            pointer-events: none !important;
        }}

        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stToolbar"] {{
            width: 100% !important;
            height: 100% !important;
            padding: 0 !important;
            background: transparent !important;
            pointer-events: auto !important;
        }}

        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stToolbar"] > div {{
            position: relative !important;
            width: 100% !important;
            height: 100% !important;
            justify-content: flex-start !important;
        }}

        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stToolbar"] > div > div:first-child {{
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: flex-start !important;
            width: 100% !important;
            height: 100% !important;
            margin: 0 !important;
        }}

        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stToolbar"] > div > div:first-child > div {{
            margin: 0 !important;
            flex-shrink: 0 !important;
        }}

        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stToolbar"] > div > *:not(:first-child) {{
            display: none !important;
        }}

        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stExpandSidebarButton"] {{
            position: absolute !important;
            left: 0.15rem !important;
            top: 50% !important;
            transform: translateY(-50%) !important;
            display: inline-flex !important;
            visibility: visible !important;
            pointer-events: auto !important;
            z-index: 2 !important;
        }}

        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stHeaderLogo"],
        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stLogo"] {{
            display: flex !important;
            visibility: visible !important;
            align-items: center !important;
            flex: 0 1 auto !important;
            min-width: 0 !important;
            margin: 0 0 0 calc({rail} + {main_pad}) !important;
            padding: 0 !important;
            pointer-events: auto !important;
        }}

        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stHeaderLogo"] img,
        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stLogo"] img {{
            display: block !important;
            visibility: visible !important;
            width: auto !important;
            max-width: min(18rem, calc(100vw - {rail} - 2 * {main_pad})) !important;
            height: auto !important;
            max-height: 2.25rem !important;
            object-fit: contain !important;
            object-position: left center !important;
        }}

        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stMain"],
        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stMainBlockContainer"] {{
            margin-left: {rail} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def configure_app_branding() -> None:
    st.logo(str(VELES_LOGO), link=VELES_LOGO_URL, size="large")
    inject_brand_styles()
