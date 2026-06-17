import streamlit as st

from config.settings import settings


def render() -> None:
    st.title("Настройки")

    st.subheader("Diadoc")
    st.write(f"API URL: `{settings.diadoc_api_url}`")
    st.write(f"Client ID: `{'настроен' if settings.diadoc_client_id else 'не задан'}`")
    st.write(f"Access token: `{'настроен' if settings.diadoc_access_token else 'не задан'}`")
    if settings.diadoc_box_ids:
        st.write(f"Ящики: `{', '.join(settings.diadoc_box_ids)}`")
    else:
        st.write("Ящики: `авто (GetMyOrganizations)`")

    st.subheader("Аванкор")
    st.write(f"Base URL: `{settings.avankor_base_url or 'не задан'}`")

    st.subheader("Хранилище")
    st.write(f"PDF: `{settings.data_dir}`")

    st.subheader("PostgreSQL")
    st.write(f"DATABASE_URL: `{settings.database_url}`")

    st.caption("Секреты задаются через файл `.env` в корне проекта.")
