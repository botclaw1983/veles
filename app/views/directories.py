import pandas as pd
import streamlit as st

from app.services.reference_store import (
    get_document_type_labels,
    get_zpif_names,
    init_references,
)


def _save_records(
    *,
    edited: pd.DataFrame,
    state_key: str,
    required_fields: list[str],
    empty_message: str,
) -> bool:
    records: list[dict[str, str]] = []
    for _, row in edited.fillna("").iterrows():
        item = {field: str(row[field]).strip() for field in required_fields}
        if not any(item.values()):
            continue
        if not all(item.values()):
            st.error("Заполните все поля в каждой строке или удалите пустую строку.")
            return False
        records.append(item)

    if not records:
        st.error(empty_message)
        return False

    st.session_state[state_key] = records
    return True


def _render_name_inn_editor(
    *,
    caption: str,
    state_key: str,
    save_key: str,
    empty_message: str,
) -> None:
    st.caption(caption)
    df = pd.DataFrame(st.session_state[state_key])
    edited = st.data_editor(
        df,
        column_config={
            "name": st.column_config.TextColumn("Название", required=True),
            "inn": st.column_config.TextColumn("ИНН", required=True),
        },
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        key=f"editor_{save_key}",
    )

    if st.button("Сохранить", key=f"save_{save_key}", use_container_width=True):
        if _save_records(
            edited=edited,
            state_key=state_key,
            required_fields=["name", "inn"],
            empty_message=empty_message,
        ):
            st.success("Сохранено")
            st.rerun()


def _render_shareholders_editor() -> None:
    st.caption("Акционеры закрытых паевых инвестиционных фондов")
    zpif_options = get_zpif_names() or ["—"]
    df = pd.DataFrame(st.session_state.ref_zpif_shareholders)
    edited = st.data_editor(
        df,
        column_config={
            "name": st.column_config.TextColumn("Акционер", required=True),
            "zpif": st.column_config.SelectboxColumn("ЗПИФ", options=zpif_options, required=True),
            "inn": st.column_config.TextColumn("ИНН", required=True),
        },
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        key="editor_zpif_shareholders",
    )

    if st.button("Сохранить", key="save_zpif_shareholders", use_container_width=True):
        if _save_records(
            edited=edited,
            state_key="ref_zpif_shareholders",
            required_fields=["name", "zpif", "inn"],
            empty_message="Добавьте хотя бы одного акционера.",
        ):
            st.success("Сохранено")
            st.rerun()


def _render_approvers_editor() -> None:
    st.caption("Сотрудники, участвующие в согласовании")
    zpif_options = get_zpif_names() or ["—"]
    doc_options = get_document_type_labels() or ["—"]

    df = pd.DataFrame(st.session_state.ref_approvers)
    for column, default in (("pif", zpif_options[0]), ("document", doc_options[0])):
        if column not in df.columns:
            df[column] = default

    edited = st.data_editor(
        df,
        column_config={
            "name": st.column_config.TextColumn("ФИО", required=True),
            "role": st.column_config.TextColumn("Роль", required=True),
            "pif": st.column_config.SelectboxColumn("ПИФ", options=zpif_options, required=True),
            "document": st.column_config.SelectboxColumn(
                "Документ",
                options=doc_options,
                required=True,
            ),
        },
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        key="editor_approvers",
    )

    if st.button("Сохранить", key="save_approvers", use_container_width=True):
        if _save_records(
            edited=edited,
            state_key="ref_approvers",
            required_fields=["name", "role", "pif", "document"],
            empty_message="Добавьте хотя бы одного согласующего.",
        ):
            st.success("Сохранено")
            st.rerun()


def _render_doc_types_editor() -> None:
    st.caption("Классификация документов в системе")
    df = pd.DataFrame(st.session_state.ref_doc_types)
    edited = st.data_editor(
        df,
        column_config={
            "label": st.column_config.TextColumn("Тип", required=True),
            "code": st.column_config.TextColumn("Код", required=True),
        },
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        key="editor_doc_types",
    )

    if st.button("Сохранить", key="save_doc_types", use_container_width=True):
        if _save_records(
            edited=edited,
            state_key="ref_doc_types",
            required_fields=["label", "code"],
            empty_message="Добавьте хотя бы один тип документа.",
        ):
            codes = [item["code"] for item in st.session_state.ref_doc_types]
            if len(codes) != len(set(codes)):
                st.error("Коды типов документов должны быть уникальными.")
                return
            st.success("Сохранено")
            st.rerun()


def render() -> None:
    init_references()

    st.subheader("Справочники")

    (
        tab_funds,
        tab_zpif,
        tab_shareholders,
        tab_counterparties,
        tab_approvers,
        tab_doc_types,
    ) = st.tabs(
        [
            "Юр. лица",
            "ЗПИФ",
            "Акционеры ЗПИФ",
            "Контрагенты",
            "Согласующие",
            "Типы документов",
        ]
    )

    with tab_funds:
        _render_name_inn_editor(
            caption="Юридические лица управляющей компании",
            state_key="ref_funds",
            save_key="funds",
            empty_message="Добавьте хотя бы одно юр. лицо.",
        )

    with tab_zpif:
        _render_name_inn_editor(
            caption="Закрытые паевые инвестиционные фонды",
            state_key="ref_zpif",
            save_key="zpif",
            empty_message="Добавьте хотя бы один ЗПИФ.",
        )

    with tab_shareholders:
        _render_shareholders_editor()

    with tab_counterparties:
        _render_name_inn_editor(
            caption="Контрагенты из входящих документов",
            state_key="ref_counterparties",
            save_key="counterparties",
            empty_message="Добавьте хотя бы одного контрагента.",
        )

    with tab_approvers:
        _render_approvers_editor()

    with tab_doc_types:
        _render_doc_types_editor()

    st.markdown("---")
    st.caption("Изменения сохраняются в текущей сессии и используются в разделах «Обработка», «Займы», «Депозиты» и «Доход».")
