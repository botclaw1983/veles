import streamlit as st

from app.components.payment_calendar import render_payment_calendar


def render() -> None:
    st.title("Платежный календарь")
    render_payment_calendar()
