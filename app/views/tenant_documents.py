from __future__ import annotations

from datetime import date
from uuid import uuid4

import pandas as pd
import streamlit as st

from app.services.reference_store import (
    TENANT_OUTBOUND_STATUS_LABELS,
    add_tenant_outbound_doc,
    get_tenant_outbound_docs,
    get_tenants,
    init_references,
    mark_tenant_outbound_sent,
    save_tenants,
)
from config.settings import settings
from integrations.diadoc import is_diadoc_configured
from models.document import normalize_inn

_TENANT_COLUMNS = [
    "name",
    "inn",
    "kpp",
    "ogrn",
    "legal_address",
    "bank_account",
    "bank_name",
    "bic",
    "rent_amount",
    "variable_electricity",
    "variable_water",
    "repair_conditions",
    "repair_note",
]

_TENANT_DOCUMENT_TEMPLATES = [
    "Счёт на оплату аренды",
    "Акт об оказании услуг",
    "Акт по коммунальным услугам",
    "Дополнительное соглашение",
    "Договор аренды",
    "УОН к договору аренды",
    "УОН для ДС к договору аренды",
    "Претензия (задолженность)",
    "Исковое заявление",
]

_OUTBOUND_DOCUMENT_TYPES = _TENANT_DOCUMENT_TEMPLATES


def _tenants_to_dataframe(tenants: list[dict]) -> pd.DataFrame:
    rows = [
        {column: tenant.get(column, "" if column != "rent_amount" else 0.0) for column in _TENANT_COLUMNS}
        for tenant in tenants
    ]
    df = pd.DataFrame(rows)
    for column in ("variable_electricity", "variable_water", "repair_conditions"):
        df[column] = df[column].fillna(False).astype(bool)
    df["rent_amount"] = pd.to_numeric(df["rent_amount"], errors="coerce").fillna(0.0)
    return df


def _parse_tenants_from_editor(edited: pd.DataFrame, existing: list[dict]) -> list[dict] | None:
    existing_by_name = {tenant["name"]: tenant for tenant in existing if tenant.get("name")}
    records: list[dict] = []

    for _, row in edited.fillna("").iterrows():
        name = str(row["name"]).strip()
        inn = str(row["inn"]).strip()
        if not name and not inn:
            continue
        if not name or not inn:
            st.error("У каждого арендатора должны быть заполнены название и ИНН.")
            return None

        normalized_inn = normalize_inn(inn)
        if not normalized_inn:
            st.error(f"Некорректный ИНН у арендатора «{name}»: укажите 10 или 12 цифр.")
            return None

        previous = existing_by_name.get(name)
        records.append(
            {
                "id": previous["id"] if previous else str(uuid4()),
                "name": name,
                "inn": normalized_inn,
                "kpp": str(row["kpp"]).strip(),
                "ogrn": str(row["ogrn"]).strip(),
                "legal_address": str(row["legal_address"]).strip(),
                "bank_account": str(row["bank_account"]).strip(),
                "bank_name": str(row["bank_name"]).strip(),
                "bic": str(row["bic"]).strip(),
                "rent_amount": float(row["rent_amount"] or 0),
                "variable_electricity": bool(row["variable_electricity"]),
                "variable_water": bool(row["variable_water"]),
                "repair_conditions": bool(row["repair_conditions"]),
                "repair_note": str(row["repair_note"]).strip(),
            }
        )

    if not records:
        st.error("Добавьте хотя бы одного арендатора.")
        return None

    return records


def _render_tenants_table() -> None:
    tenants = get_tenants()
    df = _tenants_to_dataframe(tenants)

    edited = st.data_editor(
        df,
        column_config={
            "name": st.column_config.TextColumn("Арендатор", required=True, width="medium"),
            "inn": st.column_config.TextColumn("ИНН", required=True, width="small"),
            "kpp": st.column_config.TextColumn("КПП", width="small"),
            "ogrn": st.column_config.TextColumn("ОГРН", width="small"),
            "legal_address": st.column_config.TextColumn("Юр. адрес", width="large"),
            "bank_account": st.column_config.TextColumn("Р/с", width="medium"),
            "bank_name": st.column_config.TextColumn("Банк", width="medium"),
            "bic": st.column_config.TextColumn("БИК", width="small"),
            "rent_amount": st.column_config.NumberColumn(
                "Аренда, ₽",
                min_value=0.0,
                step=1000.0,
                format="%.2f",
                width="small",
            ),
            "variable_electricity": st.column_config.CheckboxColumn(
                "Электричество",
                help="Переменная часть: электричество",
                width="small",
            ),
            "variable_water": st.column_config.CheckboxColumn(
                "Вода",
                help="Переменная часть: вода",
                width="small",
            ),
            "repair_conditions": st.column_config.CheckboxColumn(
                "Ремонт",
                help="В договоре есть условия про ремонт",
                width="small",
            ),
            "repair_note": st.column_config.TextColumn(
                "Условия ремонта",
                width="large",
            ),
        },
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        key="tenant_documents_editor",
    )

    save_col, info_col = st.columns([1, 3])
    with save_col:
        if st.button("Сохранить арендаторов", type="primary", use_container_width=True):
            records = _parse_tenants_from_editor(edited, tenants)
            if records is not None:
                save_tenants(records)
                st.success("Сохранено")
                st.rerun()
    with info_col:
        st.caption(
            "Добавляйте строки в таблице, заполняйте реквизиты и параметры договора. "
            "Данные сохраняются в текущей сессии."
        )


def _render_templates_tab() -> None:
    st.info(
        "Здесь появится заполнение документов по шаблонам: счета, акты и другие формы "
        "для арендаторов на основе данных из вкладки «Арендаторы»."
    )

    with st.expander("Планируемые шаблоны", expanded=True):
        st.markdown("\n".join(f"- {item}" for item in _TENANT_DOCUMENT_TEMPLATES))


def _render_diadoc_status() -> None:
    if is_diadoc_configured():
        st.success("Diadoc подключён — можно формировать очередь на отправку.")
        if settings.diadoc_box_ids:
            st.caption(f"Ящики: {', '.join(settings.diadoc_box_ids)}")
    else:
        st.warning(
            "Diadoc не настроен. Задайте `DIADOC_ACCESS_TOKEN` в `.env`, "
            "чтобы отправлять документы арендаторам."
        )


def _render_diadoc_prepare_form(tenants: list[dict]) -> None:
    st.markdown("**Подготовить документ к отправке**")

    if not tenants:
        st.info("Сначала добавьте арендаторов на вкладке «Арендаторы».")
        return

    tenant_options = {tenant["name"]: tenant for tenant in tenants}
    col1, col2, col3 = st.columns([1.4, 1.2, 0.8])
    with col1:
        tenant_name = st.selectbox(
            "Арендатор",
            options=list(tenant_options),
            key="tenant_diadoc_tenant",
        )
    with col2:
        document_type = st.selectbox(
            "Тип документа",
            options=_OUTBOUND_DOCUMENT_TYPES,
            key="tenant_diadoc_doc_type",
        )
    with col3:
        period = st.text_input(
            "Период",
            value=date.today().strftime("%m.%Y"),
            key="tenant_diadoc_period",
            help="Например: 06.2026",
        )

    if st.button("Добавить в очередь", type="primary", key="tenant_diadoc_add"):
        tenant = tenant_options[tenant_name]
        add_tenant_outbound_doc(
            tenant_id=tenant["id"],
            tenant_name=tenant["name"],
            document_type=document_type,
            period=period.strip(),
        )
        st.success(f"«{document_type}» для {tenant_name} добавлен в очередь.")
        st.rerun()


def _render_diadoc_queue() -> None:
    st.markdown("**Очередь отправки**")
    outbound_docs = get_tenant_outbound_docs()

    if not outbound_docs:
        st.info("Очередь пуста. Подготовьте документы для отправки арендаторам.")
        return

    header = st.columns([1.4, 1.4, 0.8, 1.0, 0.9, 0.9])
    header[0].markdown("**Арендатор**")
    header[1].markdown("**Документ**")
    header[2].markdown("**Период**")
    header[3].markdown("**Статус**")
    header[4].markdown("**Отправлено**")
    header[5].markdown("**Действие**")

    for record in outbound_docs:
        cols = st.columns([1.4, 1.4, 0.8, 1.0, 0.9, 0.9])
        cols[0].write(record["tenant_name"])
        cols[1].write(record["document_type"])
        cols[2].write(record["period"] or "—")
        status_label = TENANT_OUTBOUND_STATUS_LABELS.get(record["status"], record["status"])
        cols[3].write(status_label)
        cols[4].write(record.get("sent_at") or "—")

        if record["status"] == "sent":
            cols[5].write("—")
        elif cols[5].button("Отправить", key=f"tenant_diadoc_send_{record['id']}"):
            if not is_diadoc_configured():
                st.error("Настройте Diadoc в `.env` перед отправкой.")
            else:
                mark_tenant_outbound_sent(record["id"])
                st.success(
                    f"Документ «{record['document_type']}» отправлен в Diadoc "
                    f"(демо: статус обновлён)."
                )
                st.rerun()


def _render_diadoc_tab() -> None:
    _render_diadoc_status()
    st.markdown("---")
    tenants = get_tenants()
    _render_diadoc_prepare_form(tenants)
    st.markdown("---")
    _render_diadoc_queue()
    st.caption(
        "На следующем этапе отправка будет выполняться через API Diadoc (`PostMessage`). "
        "Сейчас очередь и статусы работают в демо-режиме."
    )


def render() -> None:
    init_references()
    st.title("Документы арендаторов")
    st.caption(
        "Реестр арендаторов, подготовка документов по шаблонам и отправка в Diadoc."
    )

    tab_tenants, tab_templates, tab_diadoc = st.tabs(
        ["Арендаторы", "Документы для подписания", "Отправка в Diadoc"]
    )

    with tab_tenants:
        _render_tenants_table()

    with tab_templates:
        _render_templates_tab()

    with tab_diadoc:
        _render_diadoc_tab()
