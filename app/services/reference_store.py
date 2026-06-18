from __future__ import annotations

import copy
from uuid import uuid4

import streamlit as st

from config.reference_data import (
    DEFAULT_APPROVER_ROWS,
    DEFAULT_COUNTERPARTIES,
    DEFAULT_DEPOSIT_ACCOUNTS,
    DEFAULT_DEPOSITS_HISTORY,
    DEFAULT_EXTRA_APPROVER_ROWS,
    DEFAULT_FUNDS,
    DEFAULT_LOAN_ACCOUNTS,
    DEFAULT_LOANS_HISTORY,
    EXTRA_APPROVER_COUNT,
    DEFAULT_ZPIF,
    DEFAULT_ZPIF_SHAREHOLDERS,
    MAIN_APPROVER_COUNT,
)
from models.document import DocumentType

LOAN_STATUS_LABELS: dict[str, str] = {
    "draft": "новый",
    "on_approval": "на согласовании",
    "approved": "согласован",
    "issued": "выдан",
}

DEPOSIT_STATUS_LABELS: dict[str, str] = {
    "draft": "новый",
    "on_approval": "на согласовании",
    "approved": "согласован",
    "issued": "выдан",
}


def _default_approvers() -> list[dict[str, str]]:
    zpif_names = [item["name"] for item in DEFAULT_ZPIF]
    doc_labels = [doc_type.label for doc_type in DocumentType]
    fallback_pif = zpif_names[0] if zpif_names else ""
    fallback_doc = doc_labels[0] if doc_labels else ""
    return [
        {
            "name": row["name"],
            "role": row["role"],
            "pif": row.get("pif") or fallback_pif,
            "document": row.get("document") or fallback_doc,
        }
        for row in DEFAULT_APPROVER_ROWS
    ]


def _migrate_counterparties(records: list[dict]) -> list[dict[str, str]]:
    migrated: list[dict[str, str]] = []
    for row in records:
        if not isinstance(row, dict):
            continue
        migrated.append(
            {
                "name": str(row.get("name", "")).strip(),
                "inn": str(row.get("inn", "")).strip(),
                "comment": str(row.get("comment", "")).strip(),
                "lawyer_comment": str(row.get("lawyer_comment", "")).strip(),
            }
        )
    return migrated


def _migrate_approvers(records: list[dict]) -> list[dict[str, str]]:
    zpif_names = [item["name"] for item in st.session_state.get("ref_zpif", DEFAULT_ZPIF)]
    doc_labels = [
        item["label"]
        for item in st.session_state.get(
            "ref_doc_types",
            [{"code": t.value, "label": t.label} for t in DocumentType],
        )
    ]
    fallback_pif = zpif_names[0] if zpif_names else ""
    fallback_doc = doc_labels[0] if doc_labels else ""
    migrated: list[dict[str, str]] = []
    for row in records:
        if isinstance(row, dict):
            migrated.append(
                {
                    "name": str(row.get("name", "")).strip(),
                    "role": str(row.get("role", "")).strip(),
                    "pif": str(row.get("pif") or fallback_pif).strip(),
                    "document": str(row.get("document") or fallback_doc).strip(),
                }
            )
        else:
            name, role = row
            migrated.append(
                {
                    "name": name,
                    "role": role,
                    "pif": fallback_pif,
                    "document": fallback_doc,
                }
            )
    return migrated


def init_references() -> None:
    if "ref_funds" not in st.session_state:
        st.session_state.ref_funds = copy.deepcopy(DEFAULT_FUNDS)
    if "ref_zpif" not in st.session_state:
        st.session_state.ref_zpif = copy.deepcopy(DEFAULT_ZPIF)
    if "ref_zpif_shareholders" not in st.session_state:
        st.session_state.ref_zpif_shareholders = copy.deepcopy(DEFAULT_ZPIF_SHAREHOLDERS)
    elif len(st.session_state.ref_zpif_shareholders) < len(DEFAULT_ZPIF_SHAREHOLDERS):
        st.session_state.ref_zpif_shareholders = copy.deepcopy(DEFAULT_ZPIF_SHAREHOLDERS)
    if "ref_counterparties" not in st.session_state:
        st.session_state.ref_counterparties = copy.deepcopy(DEFAULT_COUNTERPARTIES)
    else:
        st.session_state.ref_counterparties = _migrate_counterparties(
            st.session_state.ref_counterparties
        )
    if "ref_loan_accounts" not in st.session_state:
        st.session_state.ref_loan_accounts = copy.deepcopy(DEFAULT_LOAN_ACCOUNTS)
    if "ref_approvers" not in st.session_state:
        st.session_state.ref_approvers = _default_approvers()
    else:
        st.session_state.ref_approvers = _migrate_approvers(st.session_state.ref_approvers)
        if len(st.session_state.ref_approvers) < len(DEFAULT_APPROVER_ROWS):
            st.session_state.ref_approvers = _default_approvers()
    if "ref_doc_types" not in st.session_state:
        st.session_state.ref_doc_types = [
            {"code": doc_type.value, "label": doc_type.label} for doc_type in DocumentType
        ]
    if "loan_request" not in st.session_state:
        st.session_state.loan_request = _empty_loan_request()
    if "ref_loans_history" not in st.session_state:
        st.session_state.ref_loans_history = copy.deepcopy(DEFAULT_LOANS_HISTORY)
    if "ref_deposit_accounts" not in st.session_state:
        st.session_state.ref_deposit_accounts = copy.deepcopy(DEFAULT_DEPOSIT_ACCOUNTS)
    if "deposit_request" not in st.session_state:
        st.session_state.deposit_request = _empty_deposit_request()
    if "ref_deposits_history" not in st.session_state:
        st.session_state.ref_deposits_history = copy.deepcopy(DEFAULT_DEPOSITS_HISTORY)
    if "income_request" not in st.session_state:
        st.session_state.income_request = _empty_income_request()


def _empty_loan_request() -> dict:
    return {
        "id": str(uuid4()),
        "zpif": "",
        "account": "",
        "recipient": "",
        "amount": 0.0,
        "status": "draft",
        "shareholder_approvals": {},
    }


def _migrate_loan_request(loan: dict) -> dict:
    loan.setdefault("account", "")
    loan.setdefault("recipient", "")
    return loan


def get_funds() -> list[dict[str, str]]:
    init_references()
    return st.session_state.ref_funds


def get_zpif() -> list[dict[str, str]]:
    init_references()
    return st.session_state.ref_zpif


def get_zpif_names() -> list[str]:
    return [item["name"] for item in get_zpif()]


def get_zpif_shareholders() -> list[dict[str, str]]:
    init_references()
    return st.session_state.ref_zpif_shareholders


def get_shareholders_for_zpif(zpif_name: str) -> list[dict[str, str]]:
    return [item for item in get_zpif_shareholders() if item["zpif"] == zpif_name]


def get_counterparties() -> list[dict[str, str]]:
    init_references()
    return st.session_state.ref_counterparties


def get_counterparty_names() -> list[str]:
    return [item["name"] for item in get_counterparties()]


def get_counterparty(name: str) -> dict[str, str] | None:
    if not name:
        return None
    for item in get_counterparties():
        if item["name"] == name:
            return item
    return None


def get_loan_accounts() -> list[dict[str, str]]:
    init_references()
    return st.session_state.ref_loan_accounts


def get_accounts_for_zpif(zpif_name: str) -> list[str]:
    return [
        item["account"]
        for item in get_loan_accounts()
        if item["zpif"] == zpif_name
    ]


def get_approvers() -> list[tuple[str, str]]:
    init_references()
    return [(item["name"], item["role"]) for item in st.session_state.ref_approvers]


def get_primary_approvers() -> list[tuple[str, str]]:
    return get_approvers()[:MAIN_APPROVER_COUNT]


def get_additional_approvers() -> list[tuple[str, str]]:
    return get_approvers()[MAIN_APPROVER_COUNT:]


def get_extra_approvers() -> list[tuple[str, str]]:
    rows = [(row["name"], row["role"]) for row in DEFAULT_EXTRA_APPROVER_ROWS]
    return rows[:EXTRA_APPROVER_COUNT]


def get_approver_records() -> list[dict[str, str]]:
    init_references()
    return st.session_state.ref_approvers


def get_document_types() -> list[dict[str, str]]:
    init_references()
    return st.session_state.ref_doc_types


def get_document_type_labels() -> list[str]:
    return [item["label"] for item in get_document_types()]


def resolve_document_type(code: str) -> DocumentType | None:
    try:
        return DocumentType(code)
    except ValueError:
        return None


def get_loan_status_label(status: str) -> str:
    return LOAN_STATUS_LABELS.get(status, status)


def _loan_summary(loan: dict) -> dict:
    return {
        "id": loan["id"],
        "zpif": loan.get("zpif", ""),
        "account": loan.get("account", ""),
        "recipient": loan.get("recipient", ""),
        "amount": float(loan.get("amount") or 0.0),
        "status": loan.get("status", "draft"),
    }


def get_loans_history() -> list[dict]:
    init_references()
    return st.session_state.ref_loans_history


def sync_current_loan_to_history() -> None:
    loan = get_loan_request()
    if loan["status"] == "draft" and not loan.get("zpif") and loan.get("amount", 0) <= 0:
        return

    summary = _loan_summary(loan)
    history = st.session_state.ref_loans_history
    for index, item in enumerate(history):
        if item["id"] == summary["id"]:
            history[index] = summary
            return
    history.insert(0, summary)


def get_loans_for_display() -> list[dict]:
    sync_current_loan_to_history()
    return st.session_state.ref_loans_history


def archive_current_loan(*, status: str = "issued") -> None:
    loan = get_loan_request()
    if loan.get("amount", 0) > 0:
        summary = _loan_summary(loan)
        summary["status"] = status
        history = st.session_state.ref_loans_history
        for index, item in enumerate(history):
            if item["id"] == summary["id"]:
                history[index] = summary
                break
        else:
            history.insert(0, summary)
    reset_loan_request()


def get_loan_request() -> dict:
    init_references()
    loan = st.session_state.loan_request
    return _migrate_loan_request(loan)


def reset_loan_shareholder_approvals(zpif_name: str) -> None:
    loan = get_loan_request()
    shareholders = get_shareholders_for_zpif(zpif_name)
    loan["shareholder_approvals"] = {item["name"]: False for item in shareholders}


def all_shareholders_approved(loan: dict) -> bool:
    approvals: dict = loan.get("shareholder_approvals", {})
    return bool(approvals) and all(approvals.values())


def reset_loan_request() -> None:
    st.session_state.loan_request = _empty_loan_request()


def _empty_deposit_request() -> dict:
    return {
        "id": str(uuid4()),
        "zpif": "",
        "account": "",
        "recipient": "",
        "amount": 0.0,
        "status": "draft",
        "shareholder_approvals": {},
    }


def _migrate_deposit_request(deposit: dict) -> dict:
    deposit.setdefault("account", "")
    deposit.setdefault("recipient", "")
    return deposit


def get_deposit_accounts() -> list[dict[str, str]]:
    init_references()
    return st.session_state.ref_deposit_accounts


def get_accounts_for_deposit_zpif(zpif_name: str) -> list[str]:
    return [
        item["account"]
        for item in get_deposit_accounts()
        if item["zpif"] == zpif_name
    ]


def get_deposit_status_label(status: str) -> str:
    return DEPOSIT_STATUS_LABELS.get(status, status)


def _deposit_summary(deposit: dict) -> dict:
    return {
        "id": deposit["id"],
        "zpif": deposit.get("zpif", ""),
        "account": deposit.get("account", ""),
        "recipient": deposit.get("recipient", ""),
        "amount": float(deposit.get("amount") or 0.0),
        "status": deposit.get("status", "draft"),
    }


def get_deposits_history() -> list[dict]:
    init_references()
    return st.session_state.ref_deposits_history


def sync_current_deposit_to_history() -> None:
    deposit = get_deposit_request()
    if deposit["status"] == "draft" and not deposit.get("zpif") and deposit.get("amount", 0) <= 0:
        return

    summary = _deposit_summary(deposit)
    history = st.session_state.ref_deposits_history
    for index, item in enumerate(history):
        if item["id"] == summary["id"]:
            history[index] = summary
            return
    history.insert(0, summary)


def get_deposits_for_display() -> list[dict]:
    sync_current_deposit_to_history()
    return st.session_state.ref_deposits_history


def archive_current_deposit(*, status: str = "issued") -> None:
    deposit = get_deposit_request()
    if deposit.get("amount", 0) > 0:
        summary = _deposit_summary(deposit)
        summary["status"] = status
        history = st.session_state.ref_deposits_history
        for index, item in enumerate(history):
            if item["id"] == summary["id"]:
                history[index] = summary
                break
        else:
            history.insert(0, summary)
    reset_deposit_request()


def get_deposit_request() -> dict:
    init_references()
    deposit = st.session_state.deposit_request
    return _migrate_deposit_request(deposit)


def reset_deposit_shareholder_approvals(zpif_name: str) -> None:
    deposit = get_deposit_request()
    shareholders = get_shareholders_for_zpif(zpif_name)
    deposit["shareholder_approvals"] = {item["name"]: False for item in shareholders}


def reset_deposit_request() -> None:
    st.session_state.deposit_request = _empty_deposit_request()


def _empty_income_request() -> dict:
    return {
        "id": str(uuid4()),
        "zpif": "",
        "amount": 0.0,
        "status": "draft",
        "approver_approvals": {},
    }


def get_income_request() -> dict:
    init_references()
    return st.session_state.income_request


def reset_income_approvals() -> None:
    income = get_income_request()
    income["approver_approvals"] = {
        name: False for name, _role in get_approvers()
    }


def all_income_approvers_approved(income: dict) -> bool:
    approvals: dict = income.get("approver_approvals", {})
    return bool(approvals) and all(approvals.values())


def _is_individual_inn(inn: str) -> bool:
    return len(inn.strip()) == 12


def _calculate_ndfl(amount: float, inn: str) -> float:
    if not _is_individual_inn(inn):
        return 0.0
    return round(amount * 0.13, 2)


def calculate_income_distribution(zpif_name: str, total_amount: float) -> list[dict]:
    shareholders = get_shareholders_for_zpif(zpif_name)
    if not shareholders or total_amount <= 0:
        return []

    count = len(shareholders)
    base_share = round(100.0 / count, 4)
    base_amount = round(total_amount / count, 2)
    distributed = 0.0
    rows: list[dict] = []

    for index, shareholder in enumerate(shareholders):
        is_last = index == count - 1
        if is_last:
            amount = round(total_amount - distributed, 2)
            share_pct = round(100.0 - base_share * (count - 1), 4)
        else:
            amount = base_amount
            share_pct = base_share
            distributed += amount

        ndfl = _calculate_ndfl(amount, shareholder["inn"])
        rows.append(
            {
                "name": shareholder["name"],
                "inn": shareholder["inn"],
                "share_pct": share_pct,
                "amount": amount,
                "ndfl": ndfl,
                "net_payable": round(amount - ndfl, 2),
            }
        )

    return rows
