#!/usr/bin/env python3
"""Normalize BPMN XML for bpmn.io / Camunda Modeler import.

- Reorder process children: flow elements before sequence flows
- Serialize with explicit bpmn: prefix (not default namespace)
- Set targetNamespace to http://bpmn.io/schema/bpmn
"""

from __future__ import annotations

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

NS = {
    "bpmn": BPMN,
    "bpmndi": BPMNDI,
    "dc": DC,
    "di": DI,
    "xsi": XSI,
    "bioc": BIOC,
    "color": COLOR,
}


def reorder_process(process: ET.Element) -> None:
    children = list(process)
    lane_sets = [c for c in children if c.tag == f"{{{BPMN}}}laneSet"]
    flow_nodes = [c for c in children if c.tag not in (f"{{{BPMN}}}laneSet", f"{{{BPMN}}}sequenceFlow")]
    flows = [c for c in children if c.tag == f"{{{BPMN}}}sequenceFlow"]
    for child in children:
        process.remove(child)
    for group in (lane_sets, flow_nodes, flows):
        for child in group:
            process.append(child)


def normalize(path: Path) -> None:
    for prefix, uri in NS.items():
        ET.register_namespace(prefix, uri)

    tree = ET.parse(path)
    root = tree.getroot()

    if root.tag != f"{{{BPMN}}}definitions":
        raise ValueError(f"expected bpmn definitions root, got {root.tag}")

    root.set("targetNamespace", "http://bpmn.io/schema/bpmn")
    root.set("exporter", "bpmn-js (https://demo.bpmn.io)")
    root.set("exporterVersion", "18.19.0")
    if "processType" in root.attrib:
        del root.attrib["processType"]

    for process in root.findall(f".//{{{BPMN}}}process"):
        if process.get("processType") == "Private":
            del process.attrib["processType"]
        reorder_process(process)

    tree.write(path, encoding="UTF-8", xml_declaration=True)

    # ElementTree uses single quotes in the prolog; bpmn.io accepts both.
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "<?xml version='1.0' encoding='UTF-8'?>",
        '<?xml version="1.0" encoding="UTF-8"?>',
        1,
    )
    path.write_text(text, encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <file.bpmn>", file=sys.stderr)
        return 1
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        return 1
    normalize(path)
    print(f"Normalized: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
