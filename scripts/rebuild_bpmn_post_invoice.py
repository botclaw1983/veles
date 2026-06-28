#!/usr/bin/env python3
"""Rebuild post-invoice section of 2.1-invoice-payment.bpmn."""

import copy
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI = "http://www.omg.org/spec/BPMN/20100524/DI"
DC = "http://www.omg.org/spec/DD/20100524/DC"
DI = "http://www.omg.org/spec/DD/20100524/DI"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
BIOC = "http://bpmn.io/schema/bpmn/biocolor/1.0"
COLOR = "http://www.omg.org/spec/BPMN/non-normative/color/1.0"

NS = {"bpmn": BPMN, "bpmndi": BPMNDI, "dc": DC, "di": DI, "xsi": XSI, "bioc": BIOC, "color": COLOR}

BPMN_PATH = Path(__file__).resolve().parent.parent / "diagrams" / "2.1-invoice-payment.bpmn"

# Elements to remove entirely
REMOVE_IDS = {
    "Gateway_Electricity", "Task_SendToTC", "Task_SendToApprovers",
    "Gateway_AllSix", "Task_SendToFinDirector", "Task_SignSpecDep",
    "Flow_Prepare1_Merge", "Flow_Prepare2_Merge", "Flow_Prepare3_Merge",
    "Flow_NoInvoice1_Merge", "Flow_NoInvoice2_Merge", "Flow_NoInvoice3_Merge",
    "Flow_Merge_Elec", "Flow_Elec_Yes", "Flow_Elec_No", "Flow_TC_Send",
    "Flow_TCReply_Approvers", "Flow_Send_ApproverReceive", "Flow_Send_Wait",
    "Flow_Wait_AllSix", "Flow_AllSix_No", "Flow_AllSix_Yes",
    "Flow_SendFinDirector_Receive", "Flow_FinApprove_Upload",
    "Flow_Approve_SignSpecDep", "Flow_SignSpecDep_End", "Flow_Correct_Elec",
    # BPMNDI
    "Gateway_Electricity_di", "Task_SendToTC_di", "Task_SendToApprovers_di",
    "Gateway_AllSix_di", "Task_SendToFinDirector_di", "Task_SignSpecDep_di",
    "Flow_Prepare1_Merge_di", "Flow_Prepare2_Merge_di", "Flow_Prepare3_Merge_di",
    "Flow_NoInvoice1_Merge_di", "Flow_NoInvoice2_Merge_di", "Flow_NoInvoice3_Merge_di",
    "Flow_Merge_Elec_di", "Flow_Elec_Yes_di", "Flow_Elec_No_di", "Flow_TC_Send_di",
    "Flow_TCReply_Approvers_di", "Flow_Send_ApproverReceive_di", "Flow_Send_Wait_di",
    "Flow_Wait_AllSix_di", "Flow_AllSix_No_di", "Flow_AllSix_Yes_di",
    "Flow_SendFinDirector_Receive_di", "Flow_FinApprove_Upload_di",
    "Flow_Approve_SignSpecDep_di", "Flow_SignSpecDep_End_di", "Flow_Correct_Elec_di",
}

# Flows that must survive (pre-invoice boundary)
KEEP_FLOW_PREFIX = (
    "Flow_Start_", "Flow_Diadoc_", "Flow_Open_", "Flow_ZPIF_", "Flow_SendBO_",
    "Flow_Split_", "Flow_BOReview", "Flow_Join_", "Flow_BOApproved_",
    "Flow_Sign_", "Flow_Download_", "Flow_SaveEDO_", "Flow_SendSpecdep_",
    "Flow_AccSplit_", "Flow_Check", "Flow_Invoice",
)


def tag(ns_prefix: str, local: str) -> str:
    return f"{{{NS[ns_prefix]}}}{local}"


def q(tag_str: str) -> str:
    """Qualified tag for bpmn namespace."""
    if ":" in tag_str:
        prefix, local = tag_str.split(":", 1)
        return f"{{{NS[prefix]}}}{local}"
    return f"{{{BPMN}}}{tag_str}"


def find_by_id(root, elem_id: str):
    for el in root.iter():
        if el.get("id") == elem_id:
            return el
    return None


def remove_by_id(parent_root, elem_id: str):
    for el in list(parent_root.iter()):
        if el.get("id") == elem_id:
            parent = None
            # find parent
            for p in parent_root.iter():
                for child in list(p):
                    if child is el:
                        parent = p
                        break
            if parent is not None:
                parent.remove(el)
                return True
    return False


def make_doc(parent, tag_local: str, elem_id: str, text: str = ""):
    d = ET.SubElement(parent, q("documentation"))
    d.set("id", elem_id)
    if text:
        d.text = text
    return d


def user_task(process, elem_id: str, name: str, doc_id: str):
    existing = None
    for el in process:
        if el.get("id") == elem_id:
            existing = el
            break
    if existing is not None:
        existing.set("name", name)
        return existing
    t = ET.SubElement(process, q("userTask"))
    t.set("id", elem_id)
    t.set("name", name)
    make_doc(t, "documentation", doc_id)
    return t


def exclusive_gw(process, elem_id: str, name: str, doc_id: str, default: str | None = None):
    for el in process:
        if el.get("id") == elem_id:
            el.set("name", name)
            if default:
                el.set("default", default)
            return el
    g = ET.SubElement(process, q("exclusiveGateway"))
    g.set("id", elem_id)
    g.set("name", name)
    if default:
        g.set("default", default)
    make_doc(g, "documentation", doc_id)
    return g


def parallel_gw(process, elem_id: str, name: str, doc_id: str):
    for el in process:
        if el.get("id") == elem_id:
            if name:
                el.set("name", name)
            return el
    g = ET.SubElement(process, q("parallelGateway"))
    g.set("id", elem_id)
    if name:
        g.set("name", name)
    make_doc(g, "documentation", doc_id)
    return g


def seq_flow(process, flow_id: str, source: str, target: str, doc_id: str,
             name: str | None = None, condition: str | None = None):
    for el in process:
        if el.get("id") == flow_id:
            el.set("sourceRef", source)
            el.set("targetRef", target)
            if name:
                el.set("name", name)
            elif "name" in el.attrib:
                del el.attrib["name"]
            return el
    f = ET.SubElement(process, q("sequenceFlow"))
    f.set("id", flow_id)
    f.set("sourceRef", source)
    f.set("targetRef", target)
    make_doc(f, "documentation", doc_id)
    if name:
        f.set("name", name)
    if condition:
        ce = ET.SubElement(f, f"{{{XSI}}}conditionExpression")
        ce.set(f"{{{XSI}}}type", "tFormalExpression")
        ce.text = condition
    return f


def shape_bounds(root, plane, elem_id: str, x: float, y: float, w: float, h: float, **extra):
    sh = find_by_id(root, f"{elem_id}_di")
    if sh is None:
        sh = ET.SubElement(plane, f"{{{BPMNDI}}}BPMNShape")
        sh.set("bpmnElement", elem_id)
        sh.set("id", f"{elem_id}_di")
        b = ET.SubElement(sh, f"{{{DC}}}Bounds")
    else:
        b = sh.find(f"{{{DC}}}Bounds")
        if b is None:
            b = ET.SubElement(sh, f"{{{DC}}}Bounds")
    for k, v in extra.items():
        sh.set(k, v)
    b.set("x", str(x))
    b.set("y", str(y))
    b.set("width", str(w))
    b.set("height", str(h))
    return sh


def gw_shape(root, plane, elem_id: str, x: float, y: float, w: float = 50, h: float = 50, horizontal: bool = True):
    kw = {"isMarkerVisible": "true"}
    if horizontal:
        kw["isHorizontal"] = "true"
    return shape_bounds(root, plane, elem_id, x, y, w, h, **kw)


def edge_waypoints(plane, flow_id: str, points: list[tuple[float, float]]):
    e = ET.SubElement(plane, f"{{{BPMNDI}}}BPMNEdge")
    e.set("bpmnElement", flow_id)
    e.set("id", f"{flow_id}_di")
    for x, y in points:
        wp = ET.SubElement(e, f"{{{DI}}}waypoint")
        wp.set("x", str(x))
        wp.set("y", str(y))
    return e


def center_right(x, y, w, h):
    return x + w, y + h / 2


def center_left(x, y, w, h):
    return x, y + h / 2


def center_bottom(x, y, w, h):
    return x + w / 2, y + h


def center_top(x, y, w, h):
    return x + w / 2, y


def gw_center(x, y, w=50, h=50):
    return x + w / 2, y + h / 2


# Layout constants
TW, TH = 130, 80
GW = 50
# Branch Y centers (task center y)
BY = {1: 325, 2: 395, 3: 465}
# Post-invoice X positions per branch step
X = {"check": 2345, "decide": 2495, "prepare": 2645, "send": 2795, "merge": 2960,
     "apar": 3040, "wait": 3140, "all5": 3580,
     "pay1": 3680, "pay2": 3810, "pay3": 3940, "verify": 3920, "approve": 4020, "end": 4180}

# Approver X positions
AX = 3180
# Lane Y centers for approver tasks
LY = {
    "re": 325, "tc": 505, "ctrl": 625, "fin": 755, "chief": 1085, "gen": 870,
    "assistant": 970, "correct": 194,
}


def rebuild():
    tree = ET.parse(BPMN_PATH)
    root = tree.getroot()
    process = root.find(".//bpmn:process[@id='Process_2_1']", NS)
    lane_set = process.find("bpmn:laneSet", NS)
    plane = root.find(".//bpmndi:BPMNPlane", NS)

    # --- Remove obsolete elements ---
    for eid in REMOVE_IDS:
        remove_by_id(root, eid)

    # --- Update Flow_Invoice*_Yes targets ---
    for n in (1, 2, 3):
        flow = find_by_id(root, f"Flow_Invoice{n}_Yes")
        if flow is not None:
            flow.set("targetRef", f"Task_CheckBalances{n}")

    # --- Rename / update existing tasks ---
    updates = {
        "Task_Prepare1": "Составить&#10;лист согласования",
        "Task_Prepare2": "Составить&#10;лист согласования",
        "Task_Prepare3": "Составить&#10;лист согласования",
        "Task_UploadBank": "Загрузить платежи&#10;в банк-клиент",
        "Task_VerifyOutlook": "Сверить платежи&#10;с письмами в почте",
        "Task_ApproveBank": "Подписать счёт&#10;на оплату",
    }
    for eid, name in updates.items():
        el = find_by_id(root, eid)
        if el is not None:
            el.set("name", name)

    # --- Add accountant branch tasks (N=1,2,3) ---
    for n in (1, 2, 3):
        user_task(process, f"Task_CheckBalances{n}",
                  "Проверить остатки&#10;на счету", f"documentation_cb{n}")
        user_task(process, f"Task_DecidePayments{n}",
                  "Принять решение:&#10;какие счета оплатить", f"documentation_dp{n}")
        user_task(process, f"Task_SendApproval{n}",
                  "Отправить лист согласования&#10;по email (5 адресатов)&#10;с документами",
                  f"documentation_sa{n}")

    # --- Real Estate approver (Lane_Accountants) ---
    user_task(process, "Task_RealEstateReceive",
              "Получить лист&#10;согласования по email", "documentation_re_r")
    exclusive_gw(process, "Gateway_RealEstateElec", "Счёт за&#10;электричество?",
                 "documentation_re_e", "Flow_RE_Elec_No")
    user_task(process, "Task_RealEstateSendTC",
              "Запрос сотрудникам ТЦ&#10;проверить счётчики&#10;электричества", "documentation_re_tc")
    user_task(process, "Task_RealEstateReview",
              "Рассмотреть&#10;лист согласования", "documentation_re_rev")
    exclusive_gw(process, "Gateway_RealEstateApproved", "Согласовано?",
                 "documentation_re_ap", "Flow_RE_Approved_No")
    user_task(process, "Task_RealEstateApprove",
              "Ответное письмо&#10;с согласованием", "documentation_re_ok")
    user_task(process, "Task_RealEstateReject",
              "Ответное письмо&#10;с отказом или правками", "documentation_re_no")

    # --- Chief approver (Lane_Chief) ---
    user_task(process, "Task_ChiefReceive",
              "Получить лист&#10;согласования по email", "documentation_ch_r")
    user_task(process, "Task_ChiefReview",
              "Рассмотреть&#10;лист согласования", "documentation_ch_rev")
    exclusive_gw(process, "Gateway_ChiefApproved", "Согласовано?",
                 "documentation_ch_ap", "Flow_ChiefApproved_No")
    user_task(process, "Task_ChiefApprove",
              "Ответное письмо&#10;с согласованием", "documentation_ch_ok")
    user_task(process, "Task_ChiefReject",
              "Ответное письмо&#10;с отказом или правками", "documentation_ch_no")

    # --- Gen Director lane + tasks ---
    lane_gd = find_by_id(root, "Lane_GenDirector")
    if lane_gd is None:
        lane_gd = ET.SubElement(lane_set, q("lane"))
        lane_gd.set("id", "Lane_GenDirector")
        lane_gd.set("name", "Генеральный&#10;директор")
        make_doc(lane_gd, "documentation", "documentation_gd_lane")

    user_task(process, "Task_GenDirectorReceive",
              "Получить лист&#10;согласования по email", "documentation_gd_r")
    user_task(process, "Task_GenDirectorReview",
              "Рассмотреть&#10;лист согласования", "documentation_gd_rev")
    exclusive_gw(process, "Gateway_GenDirectorApproved", "Согласовано?",
                 "documentation_gd_ap", "Flow_GenDirectorApproved_No")
    user_task(process, "Task_GenDirectorApprove",
              "Ответное письмо&#10;с согласованием", "documentation_gd_ok")
    user_task(process, "Task_GenDirectorReject",
              "Ответное письмо&#10;с отказом или правками", "documentation_gd_no")

    # --- Parallel approval gateway + AllFive ---
    parallel_gw(process, "Gateway_ApprovalParallel", "", "documentation_apar")
    exclusive_gw(process, "Gateway_AllFive", "Все 5&#10;согласовали?",
                 "documentation_all5", "Flow_AllFive_No")

    # --- Payment tasks ---
    user_task(process, "Task_CreateAvancor",
              "Создать платежи&#10;в Аванкор", "documentation_av1")
    user_task(process, "Task_ExportAvancor",
              "Выгрузить платежи&#10;из Аванкор", "documentation_av2")

    # --- Sequence flows: accountant branches ---
    for n in (1, 2, 3):
        seq_flow(process, f"Flow_Check{n}_Decide{n}", f"Task_CheckBalances{n}",
                 f"Task_DecidePayments{n}", f"documentation_fcd{n}")
        seq_flow(process, f"Flow_Decide{n}_Prepare{n}", f"Task_DecidePayments{n}",
                 f"Task_Prepare{n}", f"documentation_fdp{n}")
        seq_flow(process, f"Flow_Prepare{n}_Send{n}", f"Task_Prepare{n}",
                 f"Task_SendApproval{n}", f"documentation_fps{n}")
        seq_flow(process, f"Flow_Send{n}_Merge", f"Task_SendApproval{n}",
                 "Gateway_AccMerge", f"documentation_fsm{n}")

    seq_flow(process, "Flow_Merge_Apar", "Gateway_AccMerge", "Gateway_ApprovalParallel",
             "documentation_fma")
    seq_flow(process, "Flow_Apar_Wait", "Gateway_ApprovalParallel", "Task_WaitResponses",
             "documentation_faw")
    seq_flow(process, "Flow_Apar_RE", "Gateway_ApprovalParallel", "Task_RealEstateReceive",
             "documentation_fre")
    seq_flow(process, "Flow_Apar_Approver", "Gateway_ApprovalParallel", "Task_ApproverReceive",
             "documentation_fap")
    seq_flow(process, "Flow_Apar_Fin", "Gateway_ApprovalParallel", "Task_FinDirectorReceive",
             "documentation_fff")
    seq_flow(process, "Flow_Apar_Chief", "Gateway_ApprovalParallel", "Task_ChiefReceive",
             "documentation_fch")
    seq_flow(process, "Flow_Apar_Gen", "Gateway_ApprovalParallel", "Task_GenDirectorReceive",
             "documentation_fgd")

    # Real Estate approver flows
    seq_flow(process, "Flow_RE_Receive_Elec", "Task_RealEstateReceive", "Gateway_RealEstateElec",
             "documentation_fre1")
    seq_flow(process, "Flow_RE_Elec_Yes", "Gateway_RealEstateElec", "Task_RealEstateSendTC",
             "documentation_frey", "Да", "${electricity == true}")
    seq_flow(process, "Flow_RE_Elec_No", "Gateway_RealEstateElec", "Task_RealEstateReview",
             "documentation_fren", "Нет")
    seq_flow(process, "Flow_RE_SendTC", "Task_RealEstateSendTC", "Task_TCReceive",
             "documentation_fretc")
    seq_flow(process, "Flow_TCReply_REReview", "Task_TCReply", "Task_RealEstateReview",
             "documentation_ftrr")
    seq_flow(process, "Flow_RE_Review_GW", "Task_RealEstateReview", "Gateway_RealEstateApproved",
             "documentation_frg")
    seq_flow(process, "Flow_RE_Approved_Yes", "Gateway_RealEstateApproved", "Task_RealEstateApprove",
             "documentation_fry", "Да", "${approved == true}")
    seq_flow(process, "Flow_RE_Approved_No", "Gateway_RealEstateApproved", "Task_RealEstateReject",
             "documentation_frn", "Нет")
    seq_flow(process, "Flow_RE_Approve_Wait", "Task_RealEstateApprove", "Task_WaitResponses",
             "documentation_fraw")
    seq_flow(process, "Flow_RE_Reject_Correct", "Task_RealEstateReject", "Task_CorrectApproval",
             "documentation_frrc")

    # Controller flows (keep existing receive-review-gateway-approve/reject, update approve→wait)
    # Flow_ApproverReceive_Review, Flow_Review_Gateway, Flow_Approved_Yes/No, Flow_Approve_Wait, Flow_Reject_Correct exist
    # Update Flow_CorrectApproval target
    fc = find_by_id(root, "Flow_Reject_Correct")
    # Flow_Reject_Correct stays → Task_CorrectApproval

    seq_flow(process, "Flow_Correct_Merge", "Task_CorrectApproval", "Gateway_AccMerge",
             "documentation_fcm")

    # Fin Director reject already exists; update FinApprove → WaitResponses
    # Remove old Flow_FinApprove_Upload, add new
    seq_flow(process, "Flow_FinApprove_Wait", "Task_FinDirectorApprove", "Task_WaitResponses",
             "documentation_ffw")

    # Chief flows
    seq_flow(process, "Flow_ChiefReceive_Review", "Task_ChiefReceive", "Task_ChiefReview",
             "documentation_fcr")
    seq_flow(process, "Flow_ChiefReview_GW", "Task_ChiefReview", "Gateway_ChiefApproved",
             "documentation_fcg")
    seq_flow(process, "Flow_ChiefApproved_Yes", "Gateway_ChiefApproved", "Task_ChiefApprove",
             "documentation_fcy", "Да", "${approved == true}")
    seq_flow(process, "Flow_ChiefApproved_No", "Gateway_ChiefApproved", "Task_ChiefReject",
             "documentation_fcn", "Нет")
    seq_flow(process, "Flow_ChiefApprove_Wait", "Task_ChiefApprove", "Task_WaitResponses",
             "documentation_fcaw")
    seq_flow(process, "Flow_ChiefReject_Correct", "Task_ChiefReject", "Task_CorrectApproval",
             "documentation_fcrc")

    # Gen Director flows
    seq_flow(process, "Flow_GenReceive_Review", "Task_GenDirectorReceive", "Task_GenDirectorReview",
             "documentation_gcr")
    seq_flow(process, "Flow_GenReview_GW", "Task_GenDirectorReview", "Gateway_GenDirectorApproved",
             "documentation_gcg")
    seq_flow(process, "Flow_GenDirectorApproved_Yes", "Gateway_GenDirectorApproved",
             "Task_GenDirectorApprove", "documentation_gcy", "Да", "${approved == true}")
    seq_flow(process, "Flow_GenDirectorApproved_No", "Gateway_GenDirectorApproved",
             "Task_GenDirectorReject", "documentation_gcn", "Нет")
    seq_flow(process, "Flow_GenApprove_Wait", "Task_GenDirectorApprove", "Task_WaitResponses",
             "documentation_gaw")
    seq_flow(process, "Flow_GenReject_Correct", "Task_GenDirectorReject", "Task_CorrectApproval",
             "documentation_grc")

    # Wait / AllFive / Payment
    seq_flow(process, "Flow_Wait_AllFive", "Task_WaitResponses", "Gateway_AllFive",
             "documentation_fwa5")
    seq_flow(process, "Flow_AllFive_No", "Gateway_AllFive", "Task_WaitResponses",
             "documentation_fa5n", "Нет")
    seq_flow(process, "Flow_AllFive_Yes", "Gateway_AllFive", "Task_CreateAvancor",
             "documentation_fa5y", "Да", "${allApproved == true}")
    seq_flow(process, "Flow_Avancor_Export", "Task_CreateAvancor", "Task_ExportAvancor",
             "documentation_fae")
    seq_flow(process, "Flow_Export_Upload", "Task_ExportAvancor", "Task_UploadBank",
             "documentation_feu")
    seq_flow(process, "Flow_Approve_End", "Task_ApproveBank", "EndEvent_1",
             "documentation_fae2")

    # Update existing payment flows in place (avoid duplicate IDs)
    for fid, src, tgt in [
        ("Flow_Upload_Verify", "Task_UploadBank", "Task_VerifyOutlook"),
        ("Flow_Verify_Approve", "Task_VerifyOutlook", "Task_ApproveBank"),
    ]:
        f = find_by_id(root, fid)
        if f is not None:
            f.set("sourceRef", src)
            f.set("targetRef", tgt)

    # --- Update lane flowNodeRefs ---
    lane_refs = {
        "Lane_Accountants": [
            "Task_BOReview1", "Gateway_AccSplit", "Task_CheckFolder1", "Task_CheckFolder2",
            "Task_CheckFolder3", "Gateway_Invoice1", "Gateway_Invoice2", "Gateway_Invoice3",
            "Task_CheckBalances1", "Task_CheckBalances2", "Task_CheckBalances3",
            "Task_DecidePayments1", "Task_DecidePayments2", "Task_DecidePayments3",
            "Task_Prepare1", "Task_Prepare2", "Task_Prepare3",
            "Task_SendApproval1", "Task_SendApproval2", "Task_SendApproval3",
            "Gateway_AccMerge", "Gateway_ApprovalParallel", "Task_WaitResponses",
            "Gateway_AllFive",
            "Task_RealEstateReceive", "Gateway_RealEstateElec", "Task_RealEstateSendTC",
            "Task_RealEstateReview", "Gateway_RealEstateApproved",
            "Task_RealEstateApprove", "Task_RealEstateReject",
            "EndEvent_NoInvoice1", "EndEvent_NoInvoice2",
        ],
        "Lane_TC": ["Task_TCReceive", "Task_TCReview", "Task_TCReply", "EndEvent_NoInvoice3"],
        "Lane_Approvers": [
            "Task_ApproverReceive", "Task_ApproverReview", "Gateway_Approved",
            "Task_ApproverApprove", "Task_ApproverReject",
        ],
        "Lane_FinDirector": [
            "Task_FinDirectorReceive", "Task_FinDirectorReview", "Gateway_FinApproved",
            "Task_FinDirectorApprove", "Task_FinDirectorReject",
        ],
        "Lane_Assistant": ["Task_BOReview2", "Task_CreateAvancor", "Task_ExportAvancor", "Task_UploadBank"],
        "Lane_Chief": [
            "Task_ChiefReceive", "Task_ChiefReview", "Gateway_ChiefApproved",
            "Task_ChiefApprove", "Task_ChiefReject",
            "Task_VerifyOutlook", "Task_ApproveBank", "EndEvent_1",
        ],
        "Lane_SpecDep": ["Task_SpecdepReceive"],
        "Lane_BackOffice": [
            "Task_OpenDiadoc", "Task_DetermineZPIF", "Task_SendBOReview",
            "Gateway_BOReviewSplit", "Gateway_BOReviewJoin", "Gateway_BOApproved",
            "Task_SignDiadoc", "Task_DownloadSigned", "Gateway_PostDownloadSplit",
            "Task_SaveEDO", "Task_SendSpecdep", "Task_CorrectApproval",
        ],
    }

    for lane_id, refs in lane_refs.items():
        lane = find_by_id(root, lane_id)
        if lane is None:
            continue
        for child in list(lane):
            if child.tag == q("flowNodeRef"):
                lane.remove(child)
        for ref in refs:
            ET.SubElement(lane, q("flowNodeRef")).text = ref

    # --- BPMNDI: pool + lanes ---
    pool = find_by_id(root, "Participant_Pool_di")
    if pool is not None:
        b = pool.find(f"{{{DC}}}Bounds")
        b.set("height", "1160")

    lane_layout = {
        "Lane_Diadoc": (60, 110),
        "Lane_BackOffice": (170, 100),
        "Lane_Accountants": (270, 190),
        "Lane_TC": (460, 100),
        "Lane_Approvers": (560, 130),
        "Lane_FinDirector": (690, 130),
        "Lane_GenDirector": (820, 100),
        "Lane_Assistant": (920, 100),
        "Lane_Chief": (1020, 130),
        "Lane_SpecDep": (1150, 70),
    }
    for lid, (y, h) in lane_layout.items():
        ls = find_by_id(root, f"{lid}_di")
        if ls is None and lid == "Lane_GenDirector":
            ls = ET.SubElement(plane, f"{{{BPMNDI}}}BPMNShape")
            ls.set("bpmnElement", lid)
            ls.set("id", f"{lid}_di")
            ls.set("isHorizontal", "true")
            b = ET.SubElement(ls, f"{{{DC}}}Bounds")
            b.set("x", "150")
            b.set("y", str(y))
            b.set("width", "4360")
            b.set("height", str(h))
        elif ls is not None:
            b = ls.find(f"{{{DC}}}Bounds")
            b.set("y", str(y))
            b.set("height", str(h))

    # Shift EndEvent_NoInvoice positions (terminal, no merge edges)
    for eid, x, y in [
        ("EndEvent_NoInvoice1", 2920, 416),
        ("EndEvent_NoInvoice2", 2920, 362),
        ("EndEvent_NoInvoice3", 2920, 478),
    ]:
        sh = find_by_id(root, f"{eid}_di")
        if sh is not None:
            b = sh.find(f"{{{DC}}}Bounds")
            b.set("x", str(x))
            b.set("y", str(y))

    # Accountant branch shapes
    for n in (1, 2, 3):
        cy = BY[n] - TH / 2
        shape_bounds(root, plane, f"Task_CheckBalances{n}", X["check"], cy, TW, TH)
        shape_bounds(root, plane, f"Task_DecidePayments{n}", X["decide"], cy, TW, TH)
        shape_bounds(root, plane, f"Task_Prepare{n}", X["prepare"], cy, TW, TH)
        shape_bounds(root, plane, f"Task_SendApproval{n}", X["send"], cy - 5, TW, TH + 10)

    # Move merge/apar/wait/all5
    gw_shape(root, plane, "Gateway_AccMerge", X["merge"], 315)
    gw_shape(root, plane, "Gateway_ApprovalParallel", X["apar"], 315, horizontal=False)
    shape_bounds(root, plane, "Task_WaitResponses", X["wait"], 294, TW, TH)
    gw_shape(root, plane, "Gateway_AllFive", X["all5"], 315)

    # Real Estate approver shapes
    shape_bounds(root, plane, "Task_RealEstateReceive", AX, LY["re"] - 40, 120, TH)
    gw_shape(root, plane, "Gateway_RealEstateElec", AX + 140, LY["re"] - 25)
    shape_bounds(root, plane, "Task_RealEstateSendTC", AX + 220, LY["re"] - 45, 130, 90)
    shape_bounds(root, plane, "Task_RealEstateReview", AX + 380, LY["re"] - 40, 120, TH)
    gw_shape(root, plane, "Gateway_RealEstateApproved", AX + 520, LY["re"] - 25)
    shape_bounds(root, plane, "Task_RealEstateApprove", AX + 600, LY["re"] - 75, 120, 70)
    shape_bounds(root, plane, "Task_RealEstateReject", AX + 600, LY["re"] + 5, 120, 70)

    # TC shapes reposition
    for eid, x in [("Task_TCReceive", AX + 220), ("Task_TCReview", AX + 360), ("Task_TCReply", AX + 500)]:
        sh = find_by_id(root, f"{eid}_di")
        if sh is not None:
            b = sh.find(f"{{{DC}}}Bounds")
            b.set("x", str(x))
            b.set("y", "465")

    # Controller shapes
    for eid, x in [("Task_ApproverReceive", AX), ("Task_ApproverReview", AX + 130),
                   ("Gateway_Approved", AX + 260), ("Task_ApproverApprove", AX + 340),
                   ("Task_ApproverReject", AX + 340)]:
        sh = find_by_id(root, f"{eid}_di")
        if sh is not None:
            b = sh.find(f"{{{DC}}}Bounds")
            b.set("x", str(x))
            if "Approve" in eid or "Reject" in eid:
                b.set("y", "560" if "Approve" in eid else "640")
            elif "Gateway" in eid:
                b.set("y", "600")
            else:
                b.set("y", "585")

    # Fin Director shapes
    for eid, x in [("Task_FinDirectorReceive", AX), ("Task_FinDirectorReview", AX + 140),
                   ("Gateway_FinApproved", AX + 280), ("Task_FinDirectorApprove", AX + 360),
                   ("Task_FinDirectorReject", AX + 360)]:
        sh = find_by_id(root, f"{eid}_di")
        if sh is not None:
            b = sh.find(f"{{{DC}}}Bounds")
            b.set("x", str(x))
            if "Approve" in eid:
                b.set("y", "690")
            elif "Reject" in eid:
                b.set("y", "770")
            elif "Gateway" in eid:
                b.set("y", "730")
            else:
                b.set("y", "715")

    # Chief approver shapes
    shape_bounds(root, plane, "Task_ChiefReceive", AX, 1045, 120, TH)
    shape_bounds(root, plane, "Task_ChiefReview", AX + 130, 1045, 120, TH)
    gw_shape(root, plane, "Gateway_ChiefApproved", AX + 270, 1060)
    shape_bounds(root, plane, "Task_ChiefApprove", AX + 350, 1025, 120, 70)
    shape_bounds(root, plane, "Task_ChiefReject", AX + 350, 1105, 120, 70)

    # Gen Director shapes
    shape_bounds(root, plane, "Task_GenDirectorReceive", AX, 830, 120, TH)
    shape_bounds(root, plane, "Task_GenDirectorReview", AX + 130, 830, 120, TH)
    gw_shape(root, plane, "Gateway_GenDirectorApproved", AX + 270, 845)
    shape_bounds(root, plane, "Task_GenDirectorApprove", AX + 350, 805, 120, 70)
    shape_bounds(root, plane, "Task_GenDirectorReject", AX + 350, 885, 120, 70)

    # Payment shapes
    shape_bounds(root, plane, "Task_CreateAvancor", X["pay1"], 294, 130, TH)
    shape_bounds(root, plane, "Task_ExportAvancor", X["pay2"], 940, 130, TH)
    shape_bounds(root, plane, "Task_UploadBank", X["pay3"], 940, 140, TH)
    sh_v = find_by_id(root, "Task_VerifyOutlook_di")
    if sh_v is not None:
        b = sh_v.find(f"{{{DC}}}Bounds")
        b.set("x", str(X["verify"]))
        b.set("y", "1045")
        b.set("width", "140")
    sh_a = find_by_id(root, "Task_ApproveBank_di")
    if sh_a is not None:
        b = sh_a.find(f"{{{DC}}}Bounds")
        b.set("x", str(X["approve"]))
        b.set("y", "1045")
    sh_e = find_by_id(root, "EndEvent_1_di")
    if sh_e is not None:
        b = sh_e.find(f"{{{DC}}}Bounds")
        b.set("x", str(X["end"]))
        b.set("y", "1067")

    # --- Build BPMNEdge for all sequence flows ---
    # Remove old post-invoice edges that we removed flows for; add/update edges

    def get_bounds(elem_id):
        sh = find_by_id(root, f"{elem_id}_di")
        if sh is None:
            return None
        b = sh.find(f"{{{DC}}}Bounds")
        return float(b.get("x")), float(b.get("y")), float(b.get("width")), float(b.get("height"))

    def edge_between(flow_id, src_id, tgt_id, via: list[tuple[float, float]] | None = None):
        # remove all existing edges for this flow (avoid duplicates)
        for e in list(plane.findall(f"{{{BPMNDI}}}BPMNEdge")):
            if e.get("bpmnElement") == flow_id:
                plane.remove(e)
        if via:
            edge_waypoints(plane, flow_id, via)
            return
        sb = get_bounds(src_id)
        tb = get_bounds(tgt_id)
        if sb is None or tb is None:
            edge_waypoints(plane, flow_id, [(0, 0), (100, 0)])
            return
        sx, sy, sw, sh = sb
        tx, ty, tw, th = tb
        p1 = center_right(sx, sy, sw, sh)
        p2 = center_left(tx, ty, tw, th)
        if abs(p1[1] - p2[1]) > 30:
            mid_x = (p1[0] + p2[0]) / 2
            edge_waypoints(plane, flow_id, [p1, (mid_x, p1[1]), (mid_x, p2[1]), p2])
        else:
            edge_waypoints(plane, flow_id, [p1, p2])

    # Pre-invoice edges: keep existing (already in file)
    # Update Invoice Yes edges
    for n in (1, 2, 3):
        fid = f"Flow_Invoice{n}_Yes"
        for e in list(plane.findall(f"{{{BPMNDI}}}BPMNEdge")):
            if e.get("bpmnElement") == fid:
                plane.remove(e)
        gw = get_bounds(f"Gateway_Invoice{n}")
        tk = get_bounds(f"Task_CheckBalances{n}")
        if gw and tk:
            edge_waypoints(plane, fid, [center_right(*gw), center_left(*tk)])

    # Branch internal flows
    for n in (1, 2, 3):
        for suffix, a, b in [
            (f"Check{n}_Decide{n}", f"Task_CheckBalances{n}", f"Task_DecidePayments{n}"),
            (f"Decide{n}_Prepare{n}", f"Task_DecidePayments{n}", f"Task_Prepare{n}"),
            (f"Prepare{n}_Send{n}", f"Task_Prepare{n}", f"Task_SendApproval{n}"),
            (f"Send{n}_Merge", f"Task_SendApproval{n}", "Gateway_AccMerge"),
        ]:
            edge_between(f"Flow_{suffix}", a, b)

    edge_between("Flow_Merge_Apar", "Gateway_AccMerge", "Gateway_ApprovalParallel")

    # Parallel split edges
    apar = get_bounds("Gateway_ApprovalParallel")
    if apar:
        ax, ay, aw, ah = apar
        ac = gw_center(ax, ay, aw, ah)
        for flow_id, tgt in [
            ("Flow_Apar_Wait", "Task_WaitResponses"),
            ("Flow_Apar_RE", "Task_RealEstateReceive"),
            ("Flow_Apar_Approver", "Task_ApproverReceive"),
            ("Flow_Apar_Fin", "Task_FinDirectorReceive"),
            ("Flow_Apar_Chief", "Task_ChiefReceive"),
            ("Flow_Apar_Gen", "Task_GenDirectorReceive"),
        ]:
            tb = get_bounds(tgt)
            if tb:
                tc = center_left(*tb)
                edge_waypoints(plane, flow_id, [ac, (ac[0] + 20, ac[1]), (ac[0] + 20, tc[1]), tc])

    # Real estate chain
    for fid, s, t in [
        ("Flow_RE_Receive_Elec", "Task_RealEstateReceive", "Gateway_RealEstateElec"),
        ("Flow_RE_Elec_Yes", "Gateway_RealEstateElec", "Task_RealEstateSendTC"),
        ("Flow_RE_Elec_No", "Gateway_RealEstateElec", "Task_RealEstateReview"),
        ("Flow_RE_SendTC", "Task_RealEstateSendTC", "Task_TCReceive"),
        ("Flow_TCReceive_Review", "Task_TCReceive", "Task_TCReview"),
        ("Flow_TCReview_Reply", "Task_TCReview", "Task_TCReply"),
        ("Flow_TCReply_REReview", "Task_TCReply", "Task_RealEstateReview"),
        ("Flow_RE_Review_GW", "Task_RealEstateReview", "Gateway_RealEstateApproved"),
        ("Flow_RE_Approved_Yes", "Gateway_RealEstateApproved", "Task_RealEstateApprove"),
        ("Flow_RE_Approved_No", "Gateway_RealEstateApproved", "Task_RealEstateReject"),
        ("Flow_RE_Approve_Wait", "Task_RealEstateApprove", "Task_WaitResponses"),
        ("Flow_RE_Reject_Correct", "Task_RealEstateReject", "Task_CorrectApproval"),
    ]:
        edge_between(fid, s, t)

    # Controller + fin (existing edges update)
    for fid, s, t in [
        ("Flow_ApproverReceive_Review", "Task_ApproverReceive", "Task_ApproverReview"),
        ("Flow_Review_Gateway", "Task_ApproverReview", "Gateway_Approved"),
        ("Flow_Approved_Yes", "Gateway_Approved", "Task_ApproverApprove"),
        ("Flow_Approved_No", "Gateway_Approved", "Task_ApproverReject"),
        ("Flow_Approve_Wait", "Task_ApproverApprove", "Task_WaitResponses"),
        ("Flow_Reject_Correct", "Task_ApproverReject", "Task_CorrectApproval"),
        ("Flow_FinReceive_Review", "Task_FinDirectorReceive", "Task_FinDirectorReview"),
        ("Flow_FinReview_Gateway", "Task_FinDirectorReview", "Gateway_FinApproved"),
        ("Flow_FinApproved_Yes", "Gateway_FinApproved", "Task_FinDirectorApprove"),
        ("Flow_FinApproved_No", "Gateway_FinApproved", "Task_FinDirectorReject"),
        ("Flow_FinApprove_Wait", "Task_FinDirectorApprove", "Task_WaitResponses"),
        ("Flow_FinReject_Correct", "Task_FinDirectorReject", "Task_CorrectApproval"),
    ]:
        edge_between(fid, s, t)

    edge_between("Flow_Correct_Merge", "Task_CorrectApproval", "Gateway_AccMerge")

    for fid, s, t in [
        ("Flow_ChiefReceive_Review", "Task_ChiefReceive", "Task_ChiefReview"),
        ("Flow_ChiefReview_GW", "Task_ChiefReview", "Gateway_ChiefApproved"),
        ("Flow_ChiefApproved_Yes", "Gateway_ChiefApproved", "Task_ChiefApprove"),
        ("Flow_ChiefApproved_No", "Gateway_ChiefApproved", "Task_ChiefReject"),
        ("Flow_ChiefApprove_Wait", "Task_ChiefApprove", "Task_WaitResponses"),
        ("Flow_ChiefReject_Correct", "Task_ChiefReject", "Task_CorrectApproval"),
        ("Flow_GenReceive_Review", "Task_GenDirectorReceive", "Task_GenDirectorReview"),
        ("Flow_GenReview_GW", "Task_GenDirectorReview", "Gateway_GenDirectorApproved"),
        ("Flow_GenDirectorApproved_Yes", "Gateway_GenDirectorApproved", "Task_GenDirectorApprove"),
        ("Flow_GenDirectorApproved_No", "Gateway_GenDirectorApproved", "Task_GenDirectorReject"),
        ("Flow_GenApprove_Wait", "Task_GenDirectorApprove", "Task_WaitResponses"),
        ("Flow_GenReject_Correct", "Task_GenDirectorReject", "Task_CorrectApproval"),
        ("Flow_Wait_AllFive", "Task_WaitResponses", "Gateway_AllFive"),
        ("Flow_Avancor_Export", "Task_CreateAvancor", "Task_ExportAvancor"),
        ("Flow_Export_Upload", "Task_ExportAvancor", "Task_UploadBank"),
        ("Flow_Upload_Verify", "Task_UploadBank", "Task_VerifyOutlook"),
        ("Flow_Verify_Approve", "Task_VerifyOutlook", "Task_ApproveBank"),
        ("Flow_Approve_End", "Task_ApproveBank", "EndEvent_1"),
    ]:
        edge_between(fid, s, t)

    # AllFive loop
    g5 = get_bounds("Gateway_AllFive")
    wt = get_bounds("Task_WaitResponses")
    if g5 and wt:
        gc = gw_center(*g5)
        wc = center_top(*wt)
        edge_waypoints(plane, "Flow_AllFive_No", [gc, (gc[0], wc[1] - 10), (wc[0], wc[1] - 10), wc])
        edge_waypoints(plane, "Flow_AllFive_Yes",
                       [center_right(*g5), center_left(*get_bounds("Task_CreateAvancor"))])
    edge_between("Flow_Wait_AllFive", "Task_WaitResponses", "Gateway_AllFive")

    # Invoice No edges (terminal, no merge)
    for n, eid in [(1, "EndEvent_NoInvoice1"), (2, "EndEvent_NoInvoice2"), (3, "EndEvent_NoInvoice3")]:
        fid = f"Flow_Invoice{n}_No"
        for e in list(plane.findall(f"{{{BPMNDI}}}BPMNEdge")):
            if e.get("bpmnElement") == fid:
                plane.remove(e)
        gw = get_bounds(f"Gateway_Invoice{n}")
        en = get_bounds(eid)
        if gw and en:
            edge_waypoints(plane, fid, [center_right(*gw), center_left(*en)])

    # Register namespaces for output
    ET.register_namespace("", BPMN)
    ET.register_namespace("bioc", BIOC)
    ET.register_namespace("bpmndi", BPMNDI)
    ET.register_namespace("color", COLOR)
    ET.register_namespace("dc", DC)
    ET.register_namespace("di", DI)
    ET.register_namespace("open-bpmn", "http://open-bpmn.org/XMLSchema")
    ET.register_namespace("xsi", XSI)

    # Deduplicate sequenceFlows (keep first)
    seen_flows: set[str] = set()
    for f in list(process.findall(q("sequenceFlow"))):
        fid = f.get("id")
        if fid in seen_flows:
            process.remove(f)
        else:
            seen_flows.add(fid)

    # Deduplicate BPMNEdges (keep last per bpmnElement)
    seen_edges: dict[str, ET.Element] = {}
    for e in list(plane.findall(f"{{{BPMNDI}}}BPMNEdge")):
        be = e.get("bpmnElement")
        if be in seen_edges:
            plane.remove(seen_edges[be])
        seen_edges[be] = e

    tree.write(BPMN_PATH, encoding="UTF-8", xml_declaration=True)
    return BPMN_PATH


def validate(path: Path):
    tree = ET.parse(path)
    root = tree.getroot()
    process = root.find(".//{http://www.omg.org/spec/BPMN/20100524/MODEL}process[@id='Process_2_1']")

    ids = set()
    for el in root.iter():
        eid = el.get("id")
        if eid:
            ids.add(eid)

    flows = process.findall("{http://www.omg.org/spec/BPMN/20100524/MODEL}sequenceFlow")
    errors = []
    for f in flows:
        for attr in ("sourceRef", "targetRef"):
            ref = f.get(attr)
            if ref not in ids:
                errors.append(f"{f.get('id')}: missing {attr}={ref}")

    plane = root.find(".//{http://www.omg.org/spec/BPMN/20100524/DI}BPMNPlane")
    edges = plane.findall("{http://www.omg.org/spec/BPMN/20100524/DI}BPMNEdge") if plane is not None else []
    empty_edges = []
    for e in edges:
        wps = e.findall("{http://www.omg.org/spec/DD/20100524/DI}waypoint")
        if len(wps) < 2:
            empty_edges.append(e.get("bpmnElement"))

    removed_check = ["Gateway_AllSix", "Task_SendToApprovers", "Task_SignSpecDep"]
    still_present = [x for x in removed_check if x in ids]

    new_keys = [
        "Task_CheckBalances1", "Task_SendApproval1", "Gateway_ApprovalParallel",
        "Gateway_AllFive", "Task_RealEstateReceive", "Gateway_RealEstateElec",
        "Task_ChiefReceive", "Lane_GenDirector", "Task_GenDirectorReceive",
        "Task_CreateAvancor", "Task_ExportAvancor", "Flow_Approve_End",
    ]
    new_present = [x for x in new_keys if x in ids]

    line_count = len(path.read_text(encoding="utf-8").splitlines())

    return {
        "lines": line_count,
        "flows": len(flows),
        "edges": len(edges),
        "flows_eq_edges": len(flows) == len(edges),
        "errors": errors,
        "empty_edges": empty_edges,
        "removed_still_present": still_present,
        "new_present": new_present,
    }


if __name__ == "__main__":
    out = rebuild()
    result = validate(out)
    print(f"Lines: {result['lines']}")
    print(f"Flows: {result['flows']}, BPMNEdges: {result['edges']}, match: {result['flows_eq_edges']}")
    print(f"Removed absent: {not result['removed_still_present']} ({result['removed_still_present']})")
    print(f"New elements: {result['new_present']}")
    if result["errors"]:
        print("ERRORS:", result["errors"])
        sys.exit(1)
    if result["empty_edges"]:
        print("EMPTY EDGES:", result["empty_edges"])
        sys.exit(1)
    if result["removed_still_present"]:
        sys.exit(1)
    print("Validation OK")
