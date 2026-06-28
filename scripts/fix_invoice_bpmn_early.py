#!/usr/bin/env python3
"""Restore pre-invoice BPMN flow (Diadoc sign → EDO folders) and add missing lanes/tasks."""

import xml.etree.ElementTree as ET
from pathlib import Path

BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI = "http://www.omg.org/spec/BPMN/20100524/DI"
DC = "http://www.omg.org/spec/DD/20100524/DC"
DI = "http://www.omg.org/spec/DD/20100524/DI"
XSI = "http://www.w3.org/2001/XMLSchema-instance"

PATH = Path(__file__).resolve().parent.parent / "diagrams" / "2.1-invoice-payment.bpmn"

REMOVE_IDS = {
    "Task_SaveFolder", "Gateway_ChooseAccountant",
    "Task_SendEmail1", "Task_SendEmail2", "Task_SendEmail3",
    "Task_Receive1", "Task_Receive2", "Task_Receive3",
    "Flow_Save_Choose", "Flow_Choose_Acc1", "Flow_Choose_Acc2", "Flow_Choose_Acc3",
    "Flow_Email1_Receive1", "Flow_Email2_Receive2", "Flow_Email3_Receive3",
    "Flow_Receive1_Prepare1", "Flow_Receive2_Prepare2", "Flow_Receive3_Prepare3",
    "Task_SaveFolder_di", "Gateway_ChooseAccountant_di",
    "Task_SendEmail1_di", "Task_SendEmail2_di", "Task_SendEmail3_di",
    "Task_Receive1_di", "Task_Receive2_di", "Task_Receive3_di",
    "Flow_Save_Choose_di", "Flow_Choose_Acc1_di", "Flow_Choose_Acc2_di", "Flow_Choose_Acc3_di",
    "Flow_Email1_Receive1_di", "Flow_Email2_Receive2_di", "Flow_Email3_Receive3_di",
    "Flow_Receive1_Prepare1_di", "Flow_Receive2_Prepare2_di", "Flow_Receive3_Prepare3_di",
}


def q(local: str) -> str:
    return f"{{{BPMN}}}{local}"


def find_by_id(root, elem_id: str):
    for el in root.iter():
        if el.get("id") == elem_id:
            return el
    return None


def remove_by_id(root, elem_id: str):
    for parent in root.iter():
        for child in list(parent):
            if child.get("id") == elem_id:
                parent.remove(child)
                return True
    return False


def doc(parent, doc_id: str):
    d = ET.SubElement(parent, q("documentation"))
    d.set("id", doc_id)
    return d


def user_task(process, eid: str, name: str, doc_id: str):
    el = find_by_id(process, eid)
    if el is None:
        el = ET.SubElement(process, q("userTask"))
        el.set("id", eid)
        doc(el, doc_id)
    el.set("name", name)
    return el


def end_event(process, eid: str, name: str, doc_id: str):
    el = find_by_id(process, eid)
    if el is None:
        el = ET.SubElement(process, q("endEvent"))
        el.set("id", eid)
        doc(el, doc_id)
    el.set("name", name)
    return el


def ex_gw(process, eid: str, name: str, doc_id: str, default: str | None = None):
    el = find_by_id(process, eid)
    if el is None:
        el = ET.SubElement(process, q("exclusiveGateway"))
        el.set("id", eid)
        doc(el, doc_id)
    el.set("name", name)
    if default:
        el.set("default", default)
    return el


def par_gw(process, eid: str, doc_id: str):
    el = find_by_id(process, eid)
    if el is None:
        el = ET.SubElement(process, q("parallelGateway"))
        el.set("id", eid)
        doc(el, doc_id)
    return el


def flow(process, fid: str, src: str, tgt: str, doc_id: str, name: str | None = None, cond: str | None = None):
    el = find_by_id(process, fid)
    if el is None:
        el = ET.SubElement(process, q("sequenceFlow"))
        el.set("id", fid)
        doc(el, doc_id)
    el.set("sourceRef", src)
    el.set("targetRef", tgt)
    if name:
        el.set("name", name)
    elif "name" in el.attrib:
        del el.attrib["name"]
    for ce in list(el):
        if ce.tag == f"{{{XSI}}}conditionExpression":
            el.remove(ce)
    if cond:
        ce = ET.SubElement(el, f"{{{XSI}}}conditionExpression")
        ce.set(f"{{{XSI}}}type", "tFormalExpression")
        ce.text = cond
    return el


def shape(plane, eid: str, x: float, y: float, w: float, h: float, **kw):
    sid = f"{eid}_di"
    sh = find_by_id(plane, sid)
    if sh is None:
        sh = ET.SubElement(plane, f"{{{BPMNDI}}}BPMNShape")
        sh.set("id", sid)
        sh.set("bpmnElement", eid)
        b = ET.SubElement(sh, f"{{{DC}}}Bounds")
    else:
        b = sh.find(f"{{{DC}}}Bounds")
    for k, v in kw.items():
        sh.set(k, v)
    b.set("x", str(x))
    b.set("y", str(y))
    b.set("width", str(w))
    b.set("height", str(h))
    return sh


def gw_shape(plane, eid: str, x: float, y: float, **kw):
    kw.setdefault("isMarkerVisible", "true")
    return shape(plane, eid, x, y, 50, 50, **kw)


def edge(plane, fid: str, pts: list[tuple[float, float]]):
    for e in list(plane.findall(f"{{{BPMNDI}}}BPMNEdge")):
        if e.get("bpmnElement") == fid:
            plane.remove(e)
    e = ET.SubElement(plane, f"{{{BPMNDI}}}BPMNEdge")
    e.set("id", f"{fid}_di")
    e.set("bpmnElement", fid)
    for x, y in pts:
        wp = ET.SubElement(e, f"{{{DI}}}waypoint")
        wp.set("x", str(x))
        wp.set("y", str(y))


def fix():
    tree = ET.parse(PATH)
    root = tree.getroot()
    process = root.find(f".//{{{BPMN}}}process[@id='Process_2_1']")
    plane = root.find(f".//{{{BPMNDI}}}BPMNPlane")
    lane_set = process.find(q("laneSet"))

    for eid in REMOVE_IDS:
        remove_by_id(root, eid)

    # Diadoc lane: EndEvent_BOReviewFailed
    end_event(process, "EndEvent_BOReviewFailed",
              "Уточнить возможные причины&#10;несогласования и действия", "documentation_BOFail")
    diadoc = find_by_id(root, "Lane_Diadoc")
    if diadoc is not None and find_by_id(root, "EndEvent_BOReviewFailed") is not None:
        refs = {c.text for c in diadoc.findall(q("flowNodeRef"))}
        if "EndEvent_BOReviewFailed" not in refs:
            ET.SubElement(diadoc, q("flowNodeRef")).text = "EndEvent_BOReviewFailed"

    # Update BO review tasks
    user_task(process, "Task_SendBOReview",
              "Отправить счёт на проверку&#10;недвижимости и бухгалтеру", "documentation_SendBO")
    user_task(process, "Task_BOReview1",
              "Сотрудник недвижимости:&#10;правомерность платежа,&#10;работы/услуги оказаны", "documentation_BO1")
    user_task(process, "Task_BOReview2",
              "Бухгалтер:&#10;заполнение счёта,&#10;условия по договору", "documentation_BO2")

    # Early post-approval flow
    user_task(process, "Task_SignDiadoc", "Заходит в Diadoc&#10;и подписывает", "documentation_Sign")
    user_task(process, "Task_DownloadSigned", "Скачивает&#10;подписанный файл", "documentation_Download")
    par_gw(process, "Gateway_PostDownloadSplit", "documentation_PostSplit")
    user_task(process, "Task_SaveEDO", "Сохраняет в соответствующую&#10;папку ЗПИФа на ЭДО", "documentation_SaveEDO")
    user_task(process, "Task_SendSpecdep", "Отправляет файл&#10;в Спецдеп", "documentation_SendSpec")
    user_task(process, "Task_SpecdepReceive", "Спецдепозитарий:&#10;получить файл", "documentation_SpecRec")
    par_gw(process, "Gateway_AccSplit", "documentation_AccSplit")
    for n in (1, 2, 3):
        user_task(process, f"Task_CheckFolder{n}",
                  f"Бухгалтер {n}:&#10;зайти в свои папки&#10;на ЭДО", f"documentation_CF{n}")
        ex_gw(process, f"Gateway_Invoice{n}", "В папке&#10;есть счёт?", f"documentation_Inv{n}",
              f"Flow_Invoice{n}_No")
        end_event(process, f"EndEvent_NoInvoice{n}", "Нет счёта&#10;в папке", f"documentation_NoInv{n}")

    # Fin Director lane + tasks
    lane_fd = find_by_id(root, "Lane_FinDirector")
    if lane_fd is None:
        lane_fd = ET.SubElement(lane_set, q("lane"))
        lane_fd.set("id", "Lane_FinDirector")
        lane_fd.set("name", "Финансовый&#10;директор")
        doc(lane_fd, "documentation_FinDir")
        ls = find_by_id(root, "Lane_FinDirector_di")
        if ls is None:
            shape(plane, "Lane_FinDirector", 150, 690, 4360, 130, isHorizontal="true")

    user_task(process, "Task_FinDirectorReceive", "Получить лист&#10;согласования по email", "documentation_FinR")
    user_task(process, "Task_FinDirectorReview", "Рассмотреть&#10;лист согласования", "documentation_FinRev")
    ex_gw(process, "Gateway_FinApproved", "Согласовано?", "documentation_FinAp", "Flow_FinApproved_No")
    user_task(process, "Task_FinDirectorApprove", "Ответное письмо&#10;с согласованием", "documentation_FinOk")
    user_task(process, "Task_FinDirectorReject", "Ответное письмо&#10;с отказом или правками", "documentation_FinNo")

    flow(process, "Flow_BOApproved_Yes", "Gateway_BOApproved", "Task_SignDiadoc", "documentation_BOYes", "Да",
         "${boReviewPassed == true}")
    flow(process, "Flow_BOApproved_No", "Gateway_BOApproved", "EndEvent_BOReviewFailed", "documentation_BONo", "Нет")
    flow(process, "Flow_Sign_Download", "Task_SignDiadoc", "Task_DownloadSigned", "documentation_SignDl")
    flow(process, "Flow_Download_Split", "Task_DownloadSigned", "Gateway_PostDownloadSplit", "documentation_DlSplit")
    flow(process, "Flow_Split_SaveEDO", "Gateway_PostDownloadSplit", "Task_SaveEDO", "documentation_SplitEDO")
    flow(process, "Flow_Split_SendSpecdep", "Gateway_PostDownloadSplit", "Task_SendSpecdep", "documentation_SplitSpec")
    flow(process, "Flow_SaveEDO_AccSplit", "Task_SaveEDO", "Gateway_AccSplit", "documentation_EDOAcc")
    flow(process, "Flow_SendSpecdep_Receive", "Task_SendSpecdep", "Task_SpecdepReceive", "documentation_SpecFlow")
    for n in (1, 2, 3):
        flow(process, f"Flow_AccSplit_Check{n}", "Gateway_AccSplit", f"Task_CheckFolder{n}", f"documentation_ASC{n}")
        flow(process, f"Flow_Check{n}_Invoice{n}", f"Task_CheckFolder{n}", f"Gateway_Invoice{n}", f"documentation_CI{n}")
        flow(process, f"Flow_Invoice{n}_Yes", f"Gateway_Invoice{n}", f"Task_CheckBalances{n}",
             f"documentation_IY{n}", "Да", "${invoiceInFolder == true}")
        flow(process, f"Flow_Invoice{n}_No", f"Gateway_Invoice{n}", f"EndEvent_NoInvoice{n}",
             f"documentation_IN{n}", "Нет")

    flow(process, "Flow_FinReceive_Review", "Task_FinDirectorReceive", "Task_FinDirectorReview", "documentation_FRR")
    flow(process, "Flow_FinReview_Gateway", "Task_FinDirectorReview", "Gateway_FinApproved", "documentation_FRG")
    flow(process, "Flow_FinApproved_Yes", "Gateway_FinApproved", "Task_FinDirectorApprove",
         "documentation_FAY", "Да", "${approved == true}")
    flow(process, "Flow_FinApproved_No", "Gateway_FinApproved", "Task_FinDirectorReject", "documentation_FAN", "Нет")
    flow(process, "Flow_FinReject_Correct", "Task_FinDirectorReject", "Task_CorrectApproval", "documentation_FRC")

    # Fix lane name
    approvers = find_by_id(root, "Lane_Approvers")
    if approvers is not None:
        approvers.set("name", "Контролёр")
    accountants = find_by_id(root, "Lane_Accountants")
    if accountants is not None:
        accountants.set("name", "Недвижимость / бухгалтеры")
    assistant = find_by_id(root, "Lane_Assistant")
    if assistant is not None:
        assistant.set("name", "Помощник бухгалтера / бухгалтер")

    # GenDirector lane refs
    lane_gd = find_by_id(root, "Lane_GenDirector")
    if lane_gd is not None:
        for c in list(lane_gd.findall(q("flowNodeRef"))):
            lane_gd.remove(c)
        for ref in ["Task_GenDirectorReceive", "Task_GenDirectorReview", "Gateway_GenDirectorApproved",
                    "Task_GenDirectorApprove", "Task_GenDirectorReject"]:
            ET.SubElement(lane_gd, q("flowNodeRef")).text = ref
        lane_gd.set("name", "Генеральный&#10;директор")

    # Move CreateAvancor to assistant lane (rebuild script puts it in accountants - fix here)
    if accountants is not None:
        refs = [c.text for c in accountants.findall(q("flowNodeRef"))]
        if "Task_CreateAvancor" in refs:
            accountants.remove([c for c in accountants.findall(q("flowNodeRef")) if c.text == "Task_CreateAvancor"][0])
    if assistant is not None:
        refs = {c.text for c in assistant.findall(q("flowNodeRef"))}
        if "Task_CreateAvancor" not in refs:
            ET.SubElement(assistant, q("flowNodeRef")).text = "Task_CreateAvancor"

    # --- BPMNDI early shapes ---
    shape(plane, "EndEvent_BOReviewFailed", 1340, 92, 36, 36)
    shape(plane, "Task_SignDiadoc", 1380, 175, 120, 80)
    shape(plane, "Task_DownloadSigned", 1515, 175, 120, 80)
    gw_shape(plane, "Gateway_PostDownloadSplit", 1650, 190, isHorizontal="true")
    shape(plane, "Task_SaveEDO", 1780, 175, 130, 80)
    shape(plane, "Task_SendSpecdep", 1780, 235, 130, 80)
    gw_shape(plane, "Gateway_AccSplit", 1960, 315)
    for n, y in [(1, 285), (2, 355), (3, 425)]:
        shape(plane, f"Task_CheckFolder{n}", 2065, y, 130, 80)
        gw_shape(plane, f"Gateway_Invoice{n}", 2235, y + 15, isHorizontal="true")
        shape(plane, f"EndEvent_NoInvoice{n}", 2920, y + 131 if n == 1 else (y + 7 if n == 2 else y + 35), 36, 36)
    shape(plane, "Task_SpecdepReceive", 1780, 1165, 130, 80)
    AX = 3180
    shape(plane, "Task_FinDirectorReceive", AX, 715, 130, 80)
    shape(plane, "Task_FinDirectorReview", AX + 150, 715, 130, 80)
    gw_shape(plane, "Gateway_FinApproved", AX + 300, 730, isHorizontal="true")
    shape(plane, "Task_FinDirectorApprove", AX + 380, 690, 130, 70)
    shape(plane, "Task_FinDirectorReject", AX + 380, 770, 130, 70)

    # Early edges
    edge(plane, "Flow_BOApproved_Yes", [(1340, 215), (1380, 215)])
    edge(plane, "Flow_BOApproved_No", [(1315, 190), (1315, 110), (1358, 110)])
    edge(plane, "Flow_Sign_Download", [(1500, 215), (1515, 215)])
    edge(plane, "Flow_Download_Split", [(1635, 215), (1650, 215)])
    edge(plane, "Flow_Split_SaveEDO", [(1700, 215), (1780, 215)])
    edge(plane, "Flow_Split_SendSpecdep", [(1700, 215), (1700, 275), (1780, 275)])
    edge(plane, "Flow_SaveEDO_AccSplit", [(1910, 215), (1910, 340), (1960, 340)])
    edge(plane, "Flow_SendSpecdep_Receive", [(1910, 275), (1910, 1205), (1780, 1205)])
    for n, cy in [(1, 325), (2, 395), (3, 465)]:
        edge(plane, f"Flow_AccSplit_Check{n}", [(2010, 340), (2010, cy), (2065, cy)])
        edge(plane, f"Flow_Check{n}_Invoice{n}", [(2195, cy), (2235, cy)])
        edge(plane, f"Flow_Invoice{n}_Yes", [(2285, cy), (2345, cy)])
        edge(plane, f"Flow_Invoice{n}_No", [(2285, cy), (2920, cy + 18)])

    ET.register_namespace("", BPMN)
    ET.register_namespace("bioc", "http://bpmn.io/schema/bpmn/biocolor/1.0")
    ET.register_namespace("bpmndi", BPMNDI)
    ET.register_namespace("color", "http://www.omg.org/spec/BPMN/non-normative/color/1.0")
    ET.register_namespace("dc", DC)
    ET.register_namespace("di", DI)
    ET.register_namespace("open-bpmn", "http://open-bpmn.org/XMLSchema")
    ET.register_namespace("xsi", XSI)

    tree.write(PATH, encoding="UTF-8", xml_declaration=True)
    print("Early flow restored")


if __name__ == "__main__":
    fix()
