#!/usr/bin/env python3
"""Merge 3 accountant post-invoice branches into a single path."""

import xml.etree.ElementTree as ET
from pathlib import Path

BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI = "http://www.omg.org/spec/BPMN/20100524/DI"
DC = "http://www.omg.org/spec/DD/20100524/DC"
DI = "http://www.omg.org/spec/DD/20100524/DI"
XSI = "http://www.w3.org/2001/XMLSchema-instance"

PATH = Path(__file__).resolve().parent.parent / "diagrams" / "2.1-invoice-payment.bpmn"

REMOVE_IDS = {
    "Task_CheckBalances2", "Task_CheckBalances3",
    "Task_DecidePayments2", "Task_DecidePayments3",
    "Task_Prepare2", "Task_Prepare3",
    "Task_SendApproval2", "Task_SendApproval3",
    "Flow_Check2_Decide2", "Flow_Decide2_Prepare2", "Flow_Prepare2_Send2", "Flow_Send2_Merge",
    "Flow_Check3_Decide3", "Flow_Decide3_Prepare3", "Flow_Prepare3_Send3", "Flow_Send3_Merge",
    "Task_CheckBalances2_di", "Task_CheckBalances3_di",
    "Task_DecidePayments2_di", "Task_DecidePayments3_di",
    "Task_Prepare2_di", "Task_Prepare3_di",
    "Task_SendApproval2_di", "Task_SendApproval3_di",
    "Flow_Check2_Decide2_di", "Flow_Decide2_Prepare2_di", "Flow_Prepare2_Send2_di", "Flow_Send2_Merge_di",
    "Flow_Check3_Decide3_di", "Flow_Decide3_Prepare3_di", "Flow_Prepare3_Send3_di", "Flow_Send3_Merge_di",
    "Flow_Invoice2_Yes_di", "Flow_Invoice3_Yes_di",
}


def q(local: str) -> str:
    return f"{{{BPMN}}}{local}"


def find_by_id(root, eid):
    for el in root.iter():
        if el.get("id") == eid:
            return el
    return None


def remove_by_id(root, eid):
    for parent in root.iter():
        for child in list(parent):
            if child.get("id") == eid:
                parent.remove(child)
                return


def main():
    tree = ET.parse(PATH)
    root = tree.getroot()
    proc = root.find(f".//{{{BPMN}}}process[@id='Process_2_1']")
    plane = root.find(f".//{{{BPMNDI}}}BPMNPlane")

    for eid in REMOVE_IDS:
        remove_by_id(root, eid)

    # Rename branch-1 tasks to generic (single accountant path)
    renames = {
        "Task_CheckBalances1": ("Task_CheckBalances", "Проверить остатки&#10;на счету"),
        "Task_DecidePayments1": ("Task_DecidePayments", "Принять решение:&#10;какие счета оплатить"),
        "Task_Prepare1": ("Task_Prepare", "Составить&#10;лист согласования"),
        "Task_SendApproval1": ("Task_SendApproval", "Отправить лист согласования&#10;по email (5 адресатов)&#10;с документами"),
    }
    id_map = {}
    for old_id, (new_id, name) in renames.items():
        el = find_by_id(root, old_id)
        if el is not None:
            el.set("id", new_id)
            el.set("name", name)
            id_map[old_id] = new_id

    # Update all references in sequenceFlows and lane refs
    for el in proc.iter():
        for attr in ("sourceRef", "targetRef"):
            v = el.get(attr)
            if v in id_map:
                el.set(attr, id_map[v])
        if el.tag == q("flowNodeRef") and el.text in id_map:
            el.text = id_map[el.text]

    for el in plane.iter():
        be = el.get("bpmnElement")
        if be in id_map:
            el.set("bpmnElement", id_map[be])
        eid = el.get("id")
        if eid and eid.endswith("_di"):
            base = eid[:-3]
            if base in id_map:
                el.set("id", id_map[base] + "_di")

    # Add merge gateway after folder checks
    if find_by_id(root, "Gateway_InvoiceFoundMerge") is None:
        gw = ET.SubElement(proc, q("exclusiveGateway"))
        gw.set("id", "Gateway_InvoiceFoundMerge")
        doc = ET.SubElement(gw, q("documentation"))
        doc.set("id", "documentation_ifm")

    # Redirect all Invoice Yes → merge → CheckBalances
    for n in (1, 2, 3):
        f = find_by_id(root, f"Flow_Invoice{n}_Yes")
        if f is not None:
            f.set("targetRef", "Gateway_InvoiceFoundMerge")

    # New flows: merge → single chain
    flows = [
        ("Flow_InvoiceFound_Check", "Gateway_InvoiceFoundMerge", "Task_CheckBalances", "documentation_ifc"),
        ("Flow_Check_Decide", "Task_CheckBalances", "Task_DecidePayments", "documentation_fcd"),
        ("Flow_Decide_Prepare", "Task_DecidePayments", "Task_Prepare", "documentation_fdp"),
        ("Flow_Prepare_Send", "Task_Prepare", "Task_SendApproval", "documentation_fps"),
        ("Flow_Send_Merge", "Task_SendApproval", "Gateway_AccMerge", "documentation_fsm"),
    ]
    old_flow_map = {
        "Flow_Check1_Decide1": "Flow_Check_Decide",
        "Flow_Decide1_Prepare1": "Flow_Decide_Prepare",
        "Flow_Prepare1_Send1": "Flow_Prepare_Send",
        "Flow_Send1_Merge": "Flow_Send_Merge",
    }
    for old, new in old_flow_map.items():
        remove_by_id(root, old)
        remove_by_id(root, old + "_di")

    for fid, src, tgt, doc_id in flows:
        remove_by_id(root, fid)  # avoid dup
        f = ET.SubElement(proc, q("sequenceFlow"))
        f.set("id", fid)
        f.set("sourceRef", src)
        f.set("targetRef", tgt)
        d = ET.SubElement(f, q("documentation"))
        d.set("id", doc_id)

    # Update lane refs
    lane = find_by_id(root, "Lane_Accountants")
    if lane is not None:
        new_refs = [
            "Task_BOReview1", "Gateway_AccSplit",
            "Task_CheckFolder1", "Task_CheckFolder2", "Task_CheckFolder3",
            "Gateway_Invoice1", "Gateway_Invoice2", "Gateway_Invoice3",
            "Gateway_InvoiceFoundMerge",
            "Task_CheckBalances", "Task_DecidePayments", "Task_Prepare", "Task_SendApproval",
            "Gateway_AccMerge", "Gateway_ApprovalParallel", "Task_WaitResponses", "Gateway_AllFive",
            "Task_RealEstateReceive", "Gateway_RealEstateElec", "Task_RealEstateSendTC",
            "Task_RealEstateReview", "Gateway_RealEstateApproved",
            "Task_RealEstateApprove", "Task_RealEstateReject",
            "EndEvent_NoInvoice1", "EndEvent_NoInvoice2",
        ]
        for c in list(lane.findall(q("flowNodeRef"))):
            lane.remove(c)
        for ref in new_refs:
            ET.SubElement(lane, q("flowNodeRef")).text = ref

    # BPMNDI: single row layout
    X = {"merge": 2345, "check": 2420, "decide": 2560, "prepare": 2700, "send": 2840, "accmerge": 2990}
    Y = 325

    def shape(eid, x, y, w=130, h=80, **kw):
        sid = f"{eid}_di"
        sh = find_by_id(root, sid)
        if sh is None:
            sh = ET.SubElement(plane, f"{{{BPMNDI}}}BPMNShape")
            sh.set("id", sid)
            sh.set("bpmnElement", eid)
            ET.SubElement(sh, f"{{{DC}}}Bounds")
        for k, v in kw.items():
            sh.set(k, v)
        b = sh.find(f"{{{DC}}}Bounds")
        b.set("x", str(x))
        b.set("y", str(y - h / 2 if h == 80 else y))
        b.set("width", str(w))
        b.set("height", str(h))

    gw_shape = find_by_id(root, "Gateway_InvoiceFoundMerge_di")
    if gw_shape is None:
        gw_shape = ET.SubElement(plane, f"{{{BPMNDI}}}BPMNShape")
        gw_shape.set("id", "Gateway_InvoiceFoundMerge_di")
        gw_shape.set("bpmnElement", "Gateway_InvoiceFoundMerge")
        gw_shape.set("isMarkerVisible", "true")
        gw_shape.set("isHorizontal", "true")
        ET.SubElement(gw_shape, f"{{{DC}}}Bounds")
    b = gw_shape.find(f"{{{DC}}}Bounds")
    b.set("x", str(X["merge"]))
    b.set("y", "300")
    b.set("width", "50")
    b.set("height", "50")

    shape("Task_CheckBalances", X["check"], Y)
    shape("Task_DecidePayments", X["decide"], Y)
    shape("Task_Prepare", X["prepare"], Y)
    shape("Task_SendApproval", X["send"], Y - 5, h=90)
    sh = find_by_id(root, "Gateway_AccMerge_di")
    if sh is not None:
        b = sh.find(f"{{{DC}}}Bounds")
        b.set("x", str(X["accmerge"]))
        b.set("y", "300")

    def edge(fid, pts):
        remove_by_id(root, fid + "_di")
        e = ET.SubElement(plane, f"{{{BPMNDI}}}BPMNEdge")
        e.set("id", fid + "_di")
        e.set("bpmnElement", fid)
        for x, y in pts:
            wp = ET.SubElement(e, f"{{{DI}}}waypoint")
            wp.set("x", str(x))
            wp.set("y", str(y))

    cy = Y
    edge("Flow_Invoice1_Yes", [(2285, cy), (2345, cy)])
    edge("Flow_Invoice2_Yes", [(2285, 395), (2345, 395), (2345, 325), (2370, 325)])
    edge("Flow_Invoice3_Yes", [(2285, 465), (2345, 465), (2345, 325), (2370, 325)])
    edge("Flow_InvoiceFound_Check", [(2395, 325), (2420, 325)])
    edge("Flow_Check_Decide", [(2550, 325), (2560, 325)])
    edge("Flow_Decide_Prepare", [(2690, 325), (2700, 325)])
    edge("Flow_Prepare_Send", [(2830, 325), (2840, 325)])
    edge("Flow_Send_Merge", [(2970, 325), (2990, 325)])

    # Deduplicate edges by bpmnElement
    seen = {}
    for e in list(plane.findall(f"{{{BPMNDI}}}BPMNEdge")):
        be = e.get("bpmnElement")
        if be in seen:
            plane.remove(seen[be])
        seen[be] = e

    ET.register_namespace("", BPMN)
    ET.register_namespace("bioc", "http://bpmn.io/schema/bpmn/biocolor/1.0")
    ET.register_namespace("bpmndi", BPMNDI)
    ET.register_namespace("color", "http://www.omg.org/spec/BPMN/non-normative/color/1.0")
    ET.register_namespace("dc", DC)
    ET.register_namespace("di", DI)
    ET.register_namespace("open-bpmn", "http://open-bpmn.org/XMLSchema")
    ET.register_namespace("xsi", XSI)
    tree.write(PATH, encoding="UTF-8", xml_declaration=True)

    # Validate
    tree2 = ET.parse(PATH)
    proc2 = tree2.getroot().find(f".//{{{BPMN}}}process[@id='Process_2_1']")
    ids = {el.get("id") for el in proc2.iter() if el.get("id")}
    assert "Task_CheckBalances2" not in ids
    assert "Task_CheckBalances" in ids
    assert "Gateway_InvoiceFoundMerge" in ids
    flows = proc2.findall(f"{{{BPMN}}}sequenceFlow")
    for f in flows:
        for a in ("sourceRef", "targetRef"):
            assert f.get(a) in ids, f"{f.get('id')} bad {a}={f.get(a)}"
    print(f"OK: {len(flows)} flows, single accountant path after invoice found")


if __name__ == "__main__":
    main()
